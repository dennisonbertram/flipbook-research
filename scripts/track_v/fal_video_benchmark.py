#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from time import perf_counter
from typing import Any

import fal_client
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "fixtures" / "track-a" / "text-heavy-page.png"
OUTPUT_ROOT = ROOT / "outputs" / "track-v"
RESULTS_TSV = ROOT / "docs" / "experiments" / "track-v" / "results.tsv"


MODELS = {
    "kling": "fal-ai/kling-video/v2.5-turbo/standard/image-to-video",
    "ltx": "fal-ai/ltx-video-13b-distilled/image-to-video",
}


def parse_resolution(value: str) -> tuple[int, int]:
    width, height = value.lower().split("x", 1)
    parsed = (int(width), int(height))
    if parsed[0] <= 0 or parsed[1] <= 0:
        raise argparse.ArgumentTypeError("resolution dimensions must be positive")
    return parsed


def git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return "nogit"
    return result.stdout.strip()


def utc_run_id(model_key: str, label: str, width: int, height: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "run"
    return f"{stamp}-fal-{model_key}-{slug}-{width}x{height}"


def fit_image(input_path: Path, output_path: Path, size: tuple[int, int]) -> None:
    width, height = size
    with Image.open(input_path) as source:
        img = source.convert("RGB")
        scale = min(width / img.width, height / img.height)
        resized = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "#fffdf8")
    x = (width - resized.width) // 2
    y = (height - resized.height) // 2
    canvas.paste(resized, (x, y))
    canvas.save(output_path, "PNG")


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def ocr(path: Path) -> str:
    result = subprocess.run(
        ["tesseract", str(path), "stdout", "--psm", "6", "--oem", "1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.strip()


def extract_frame(video: Path, frame_index: int, output: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"select=eq(n\\,{frame_index})",
            "-vframes",
            "1",
            str(output),
        ],
        check=True,
    )


def probe_video(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,nb_frames,r_frame_rate,duration",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return {"probe_error": result.stderr.strip()}
    data = json.loads(result.stdout or "{}")
    return data.get("streams", [{}])[0]


def image_similarity(a_path: Path, b_path: Path, size: tuple[int, int] = (192, 108)) -> float:
    with Image.open(a_path) as a_img, Image.open(b_path) as b_img:
        a = np.asarray(a_img.convert("L").resize(size, Image.Resampling.BILINEAR), dtype=np.float32)
        b = np.asarray(b_img.convert("L").resize(size, Image.Resampling.BILINEAR), dtype=np.float32)
    mse = float(np.mean((a - b) ** 2))
    return max(0.0, min(1.0, 1.0 - mse / (255.0**2)))


def frame_diff(a_path: Path, b_path: Path, size: tuple[int, int] = (192, 108)) -> float:
    with Image.open(a_path) as a_img, Image.open(b_path) as b_img:
        a = np.asarray(a_img.convert("L").resize(size, Image.Resampling.BILINEAR), dtype=np.float32)
        b = np.asarray(b_img.convert("L").resize(size, Image.Resampling.BILINEAR), dtype=np.float32)
    return float(np.mean(np.abs(a - b)) / 255.0)


def download(url: str, output: Path) -> float:
    start = perf_counter()
    with requests.get(url, timeout=300, stream=True) as response:
        response.raise_for_status()
        with output.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return (perf_counter() - start) * 1000


def fal_result_video_url(result: dict[str, Any]) -> str:
    for key in ("video", "output", "file"):
        value = result.get(key)
        if isinstance(value, dict) and isinstance(value.get("url"), str):
            return value["url"]
        if isinstance(value, str) and value.startswith("http"):
            return value
    videos = result.get("videos")
    if isinstance(videos, list):
        for value in videos:
            if isinstance(value, dict) and isinstance(value.get("url"), str):
                return value["url"]
    raise RuntimeError(f"Could not find video URL in fal result keys: {sorted(result)}")


def build_arguments(args: argparse.Namespace, image_url: str) -> dict[str, Any]:
    if args.model == "kling":
        return {
            "prompt": args.prompt,
            "negative_prompt": args.negative_prompt,
            "image_url": image_url,
            "duration": str(args.duration),
            "cfg_scale": args.cfg_scale,
        }

    return {
        "prompt": args.prompt,
        "negative_prompt": args.negative_prompt,
        "image_url": image_url,
        "resolution": args.ltx_resolution,
        "aspect_ratio": args.aspect_ratio,
        "seed": args.seed,
        "num_frames": args.frames,
        "frame_rate": args.fps,
        "first_pass_num_inference_steps": args.first_pass_steps,
        "second_pass_num_inference_steps": args.second_pass_steps,
        "second_pass_skip_initial_steps": args.second_pass_skip_steps,
        "expand_prompt": False,
        "reverse_video": False,
        "enable_detail_pass": args.enable_detail_pass,
        "enable_safety_checker": True,
        "constant_rate_factor": args.crf,
    }


def evaluate_video(input_path: Path, video_path: Path, run_dir: Path, probe: dict[str, Any]) -> dict[str, Any]:
    nb_frames = int(float(probe.get("nb_frames") or 0))
    if nb_frames <= 0:
        duration = float(probe.get("duration") or 0.0)
        nb_frames = max(1, round(duration * 24))
    indices = [0, max(0, nb_frames // 2), max(0, nb_frames - 1)]
    frame_paths = []
    for label, index in zip(["first", "mid", "last"], indices):
        frame_path = run_dir / f"frame-{label}.png"
        extract_frame(video_path, index, frame_path)
        frame_paths.append(frame_path)

    input_ocr = ocr(input_path)
    input_norm = normalize_text(input_ocr)
    frames = []
    text_scores = []
    layout_scores = []
    for label, index, frame_path in zip(["first", "mid", "last"], indices, frame_paths):
        frame_ocr = ocr(frame_path)
        frame_norm = normalize_text(frame_ocr)
        text_score = SequenceMatcher(None, input_norm, frame_norm).ratio() if input_norm else 0.0
        layout_score = image_similarity(input_path, frame_path)
        text_scores.append(text_score)
        layout_scores.append(layout_score)
        frames.append(
            {
                "label": label,
                "frame_index": index,
                "path": str(frame_path),
                "ocr": frame_ocr,
                "text_score": text_score,
                "layout_score": layout_score,
            }
        )

    quality = {
        "input_ocr": input_ocr,
        "text_score": float(np.mean(text_scores)),
        "layout_score": float(np.mean(layout_scores)),
        "motion_score": frame_diff(frame_paths[0], frame_paths[1]),
        "loop_error": frame_diff(frame_paths[0], frame_paths[-1]),
        "frames": frames,
        "note": "OCR/layout proxy for video-model text preservation; manual review is still required.",
    }
    (run_dir / "quality.json").write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
    create_contact_sheet(input_path, frame_paths, run_dir / "contact-sheet.jpg")
    return quality


def create_contact_sheet(input_path: Path, frame_paths: list[Path], output_path: Path) -> None:
    labels = ["input", "first", "mid", "last"]
    paths = [input_path, *frame_paths]
    thumbs = []
    for path in paths:
        with Image.open(path) as img:
            thumb = img.convert("RGB")
            thumb.thumbnail((480, 272), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (480, 272), "#f6f4ef")
            canvas.paste(thumb, ((480 - thumb.width) // 2, (272 - thumb.height) // 2))
            thumbs.append(canvas)
    sheet = Image.new("RGB", (960, 640), "#ece8de")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, thumb) in enumerate(zip(labels, thumbs)):
        x = 0 if index % 2 == 0 else 480
        y = 0 if index < 2 else 320
        sheet.paste(thumb, (x, y))
        draw.rectangle([x, y + 272, x + 480, y + 319], fill="#f6f4ef", outline="#d8d2c7")
        draw.text((x + 8, y + 287), label, fill="#111111", font=font)
    sheet.save(output_path, quality=90)


def ensure_results_header() -> None:
    RESULTS_TSV.parent.mkdir(parents=True, exist_ok=True)
    if RESULTS_TSV.exists():
        return
    RESULTS_TSV.write_text(
        "\t".join(
            [
                "run_id",
                "commit",
                "model",
                "endpoint",
                "input_resolution",
                "output_resolution",
                "requested_frames",
                "output_frames",
                "duration_s",
                "api_wall_ms",
                "download_ms",
                "text_score",
                "layout_score",
                "motion_score",
                "loop_error",
                "status",
                "description",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def append_results(metrics: dict[str, Any], quality: dict[str, Any]) -> None:
    ensure_results_header()
    probe = metrics.get("video_probe", {})
    output_resolution = "NA"
    if probe.get("width") and probe.get("height"):
        output_resolution = f'{probe["width"]}x{probe["height"]}'
    row = [
        metrics["run_id"],
        metrics["commit"],
        metrics["model"],
        metrics["endpoint"],
        metrics["input_resolution"],
        output_resolution,
        str(metrics["requested_frames"]),
        str(metrics.get("output_frames") or "NA"),
        str(metrics.get("duration_s") or "NA"),
        f'{metrics["api_wall_ms"]:.3f}',
        f'{metrics["download_ms"]:.3f}',
        f'{quality["text_score"]:.4f}',
        f'{quality["layout_score"]:.4f}',
        f'{quality["motion_score"]:.4f}',
        f'{quality["loop_error"]:.4f}',
        metrics["status"],
        metrics["description"].replace("\t", " "),
    ]
    with RESULTS_TSV.open("a", encoding="utf-8") as handle:
        handle.write("\t".join(row) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark fal-hosted video models for Flipbook page animation.")
    parser.add_argument("--model", choices=sorted(MODELS), required=True)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--label", default="page-i2v")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prep-resolution", type=parse_resolution, default=(960, 540))
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--append-results", action="store_true")
    parser.add_argument("--prompt", default="Subtle continuous camera motion and gentle parallax. Preserve every word, diagram line, page layout, and typography exactly.")
    parser.add_argument("--negative-prompt", default="warped text, changed letters, misspelled words, melting diagram, layout drift, low resolution, jitter")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--frames", type=int, default=33)
    parser.add_argument("--duration", type=int, default=5, choices=[5, 10], help="Kling duration in seconds.")
    parser.add_argument("--cfg-scale", type=float, default=0.3)
    parser.add_argument("--ltx-resolution", default="480p", choices=["480p", "720p"])
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--first-pass-steps", type=int, default=2)
    parser.add_argument("--second-pass-steps", type=int, default=2)
    parser.add_argument("--second-pass-skip-steps", type=int, default=1)
    parser.add_argument("--enable-detail-pass", action="store_true")
    parser.add_argument("--crf", type=int, default=29)
    parser.add_argument("--min-text-score", type=float, default=0.70)
    parser.add_argument("--min-layout-score", type=float, default=0.80)
    parser.add_argument("--skip-text-gate", action="store_true", help="Use only layout/motion proxies for illustration-heavy inputs.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not os.environ.get("FAL_KEY"):
        raise SystemExit("FAL_KEY is not set in the environment.")
    if not args.input.exists():
        raise SystemExit(f"Input image does not exist: {args.input}")

    width, height = args.prep_resolution
    run_id = utc_run_id(args.model, args.label, width, height)
    run_dir = args.output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    prepared_input = run_dir / "input.png"
    fit_image(args.input, prepared_input, (width, height))

    endpoint = args.endpoint or MODELS[args.model]
    print(f"[{run_id}] prepared input {prepared_input}", flush=True)
    upload_url = fal_client.upload_file(str(prepared_input))
    print(f"[{run_id}] uploaded input to fal storage", flush=True)
    fal_args = build_arguments(args, upload_url)
    updates: list[dict[str, Any]] = []

    def on_queue_update(update: Any) -> None:
        updates.append({"type": type(update).__name__, "repr": repr(update)[:1000]})
        print(f"[{run_id}] queue update: {type(update).__name__}", flush=True)

    start = perf_counter()
    print(f"[{run_id}] submitting {endpoint}", flush=True)
    result = fal_client.subscribe(endpoint, arguments=fal_args, with_logs=True, on_queue_update=on_queue_update)
    api_wall_ms = (perf_counter() - start) * 1000
    print(f"[{run_id}] fal result received in {api_wall_ms:.1f}ms", flush=True)

    video_url = fal_result_video_url(result)
    output_mp4 = run_dir / "output.mp4"
    download_ms = download(video_url, output_mp4)
    print(f"[{run_id}] downloaded video in {download_ms:.1f}ms", flush=True)
    probe = probe_video(output_mp4)
    quality = evaluate_video(prepared_input, output_mp4, run_dir, probe)
    duration_s = float(probe.get("duration") or 0.0) if "duration" in probe else None
    output_frames = int(float(probe.get("nb_frames") or 0)) if probe.get("nb_frames") else None

    text_ok = args.skip_text_gate or quality["text_score"] >= args.min_text_score
    layout_ok = quality["layout_score"] >= args.min_layout_score
    status = "pass" if text_ok and layout_ok else "quality_fail"
    metrics = {
        "run_id": run_id,
        "commit": git_commit(),
        "model": args.model,
        "endpoint": endpoint,
        "input_source": str(args.input),
        "input_resolution": f"{width}x{height}",
        "requested_frames": args.frames if args.model == "ltx" else f"{args.duration}s",
        "output_frames": output_frames,
        "duration_s": duration_s,
        "api_wall_ms": api_wall_ms,
        "download_ms": download_ms,
        "status": status,
        "description": f"fal {args.model} image-to-video benchmark",
        "gates": {
            "skip_text_gate": args.skip_text_gate,
            "min_text_score": args.min_text_score,
            "min_layout_score": args.min_layout_score,
            "text_ok": text_ok,
            "layout_ok": layout_ok,
        },
        "arguments": {key: value for key, value in fal_args.items() if key != "image_url"},
        "fal_result": result,
        "queue_updates": updates,
        "video_probe": probe,
        "artifacts": {
            "input": str(prepared_input),
            "output": str(output_mp4),
            "contact_sheet": str(run_dir / "contact-sheet.jpg"),
            "quality": str(run_dir / "quality.json"),
        },
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    if args.append_results:
        append_results(metrics, quality)
    print(json.dumps({"run_id": run_id, "status": status, "api_wall_ms": api_wall_ms, "output": str(output_mp4)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
