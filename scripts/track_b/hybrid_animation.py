#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "fixtures" / "track-a" / "text-heavy-page.png"
OUTPUT_ROOT = ROOT / "outputs" / "track-b"
RESULTS_TSV = ROOT / "docs" / "experiments" / "track-b" / "results.tsv"


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


def utc_run_id(label: str, width: int, height: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "hybrid"
    return f"{stamp}-track-b-hybrid-{slug}-{width}x{height}"


def fit_image(input_path: Path, output_path: Path, size: tuple[int, int]) -> Image.Image:
    width, height = size
    with Image.open(input_path) as source:
        img = source.convert("RGB")
        if img.size == size:
            shutil.copy2(input_path, output_path)
            return img
        scale = min(width / img.width, height / img.height)
        resized = img.resize(
            (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
            Image.Resampling.LANCZOS,
        )
    canvas = Image.new("RGB", (width, height), "#fffdf8")
    x = (width - resized.width) // 2
    y = (height - resized.height) // 2
    canvas.paste(resized, (x, y))
    canvas.save(output_path, "PNG")
    return canvas


def make_protected_mask(
    image: Image.Image,
    dark_threshold: int,
    edge_threshold: float,
    dilate: int,
    blur: float,
) -> tuple[Image.Image, dict[str, float]]:
    gray = np.asarray(image.convert("L"), dtype=np.float32)
    dark = gray < dark_threshold

    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:] = np.abs(gray[:, 1:] - gray[:, :-1])
    gy[1:, :] = np.abs(gray[1:, :] - gray[:-1, :])
    edges = np.maximum(gx, gy)
    edge_mask = (edges > edge_threshold) & (gray < 245)
    mask = dark | edge_mask

    raw = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    if dilate > 1:
        if dilate % 2 == 0:
            dilate += 1
        raw = raw.filter(ImageFilter.MaxFilter(dilate))
    soft = raw.filter(ImageFilter.GaussianBlur(blur)) if blur > 0 else raw
    stats = {
        "protected_ratio_raw": float(np.mean(mask)),
        "protected_ratio_dilated": float(np.mean(np.asarray(raw, dtype=np.float32) > 0)),
        "protected_ratio_soft_mean": float(np.mean(np.asarray(soft, dtype=np.float32)) / 255.0),
    }
    return soft, stats


def affine_motion(image: Image.Image, phase: float, args: argparse.Namespace) -> Image.Image:
    width, height = image.size
    cx = width / 2.0
    cy = height / 2.0
    pan_x = args.pan_x * math.sin(phase)
    pan_y = args.pan_y * math.sin(2.0 * phase)
    zoom = 1.0 + args.zoom * (0.5 - 0.5 * math.cos(phase))
    inv = 1.0 / zoom
    matrix = (
        inv,
        0.0,
        cx - cx * inv - pan_x,
        0.0,
        inv,
        cy - cy * inv - pan_y,
    )
    return image.transform(image.size, Image.Transform.AFFINE, matrix, resample=Image.Resampling.BICUBIC)


def add_lighting(moving: Image.Image, phase: float, protected_mask: Image.Image, args: argparse.Namespace) -> Image.Image:
    arr = np.asarray(moving, dtype=np.float32)
    height, width = arr.shape[:2]
    y = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
    x = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
    pattern = x * 2.2 + y * 1.4
    # Keep endpoints identical in closed-loop mode while still allowing
    # subtle mid-clip motion from lighting.
    wave = np.sin(phase + pattern) - np.sin(pattern)
    ambient = 1.0 + args.ambient * math.sin(phase)
    light = ambient + args.shimmer * wave
    mask = 1.0 - (np.asarray(protected_mask, dtype=np.float32) / 255.0)
    factor = 1.0 + (light - 1.0) * mask
    arr = np.clip(arr * factor[:, :, None], 0, 255)
    return Image.fromarray(arr.astype(np.uint8), mode="RGB")


def render_frames(source: Image.Image, protected_mask: Image.Image, args: argparse.Namespace) -> tuple[list[Image.Image], dict[str, float]]:
    start = perf_counter()
    source_arr = np.asarray(source, dtype=np.float32)
    mask = np.asarray(protected_mask, dtype=np.float32)[:, :, None] / 255.0
    frames: list[Image.Image] = []
    denominator = max(1, args.frames - 1) if args.closed_loop else max(1, args.frames)

    if args.motion_mode in {"lighting-only", "fast-drift"}:
        height, width = source_arr.shape[:2]
        y = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
        x = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
        pattern = x * 2.2 + y * 1.4
        unprotected = 1.0 - mask
        pad_x = max(2, math.ceil(abs(args.pan_x)) + 2)
        pad_y = max(2, math.ceil(abs(args.pan_y)) + 2)
        padded = np.pad(source_arr, ((pad_y, pad_y), (pad_x, pad_x), (0, 0)), mode="edge")
        for index in range(args.frames):
            if args.closed_loop and index in {0, args.frames - 1}:
                frames.append(source.copy())
                continue
            phase = 2.0 * math.pi * (index / denominator)
            if args.motion_mode == "fast-drift":
                dx = int(round(args.pan_x * math.sin(phase / 2.0)))
                dy = int(round(args.pan_y * math.sin(phase / 2.0)))
                y0 = pad_y - dy
                x0 = pad_x - dx
                moving_arr = padded[y0 : y0 + height, x0 : x0 + width]
            else:
                moving_arr = source_arr
            wave = np.sin(phase + pattern) - np.sin(pattern)
            ambient = args.ambient * math.sin(phase)
            delta = ambient + args.shimmer * wave
            lit = moving_arr * (1.0 + delta[:, :, None])
            if args.motion_mode == "fast-drift":
                frame = lit
            else:
                frame = source_arr * (1.0 + delta[:, :, None] * unprotected)
            frames.append(Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), mode="RGB"))
        return frames, {"render_ms": (perf_counter() - start) * 1000}

    for index in range(args.frames):
        if args.closed_loop and index in {0, args.frames - 1}:
            frames.append(source.copy())
            continue
        phase = 2.0 * math.pi * (index / denominator)
        moving = affine_motion(source, phase, args)
        moving = add_lighting(moving, phase, protected_mask, args)
        moving_arr = np.asarray(moving, dtype=np.float32)
        if args.motion_mode == "global-affine":
            frame = moving_arr
        else:
            frame = moving_arr * (1.0 - mask) + source_arr * mask
        frames.append(Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), mode="RGB"))
    return frames, {"render_ms": (perf_counter() - start) * 1000}


def encode_frames(frames: list[Image.Image], output_path: Path, fps: int, preset: str, crf: int) -> float:
    width, height = frames[0].size
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "pipe:0",
        "-frames:v",
        str(len(frames)),
        "-an",
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        preset,
        "-tune",
        "zerolatency",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    start = perf_counter()
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for frame in frames:
            proc.stdin.write(frame.convert("RGB").tobytes())
        proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        return_code = proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill()
    encode_ms = (perf_counter() - start) * 1000
    if return_code != 0:
        raise RuntimeError(f"ffmpeg failed with code {return_code}: {stderr}")
    return encode_ms


def encode_ffmpeg_drift(input_path: Path, output_path: Path, args: argparse.Namespace) -> float:
    width, height = args.resolution
    pad_x = max(2, math.ceil(abs(args.pan_x)))
    pad_y = max(2, math.ceil(abs(args.pan_y)))
    denominator = max(1, args.frames - 1) if args.closed_loop else max(1, args.frames)
    # Tiny global camera drift over an edge-padded still plate. This is the
    # fastest Track B path because ffmpeg handles synthesis and encode together.
    if args.drift_fill == "overscan":
        scale_factor = max((width + 2 * pad_x) / width, (height + 2 * pad_y) / height)
        scaled_width = max(width + 2 * pad_x, math.ceil(width * scale_factor))
        scaled_height = max(height + 2 * pad_y, math.ceil(height * scale_factor))
        if scaled_width % 2:
            scaled_width += 1
        if scaled_height % 2:
            scaled_height += 1
        base_x = (scaled_width - width) / 2.0
        base_y = (scaled_height - height) / 2.0
        crop_x = f"{base_x:g}-({args.pan_x:g})*sin(PI*n/{denominator:g})"
        crop_y = f"{base_y:g}-({args.pan_y:g})*sin(PI*n/{denominator:g})"
        vf = f"scale={scaled_width}:{scaled_height}:flags=bicubic,crop={width}:{height}:x='{crop_x}':y='{crop_y}'"
    else:
        crop_x = f"{pad_x:g}-({args.pan_x:g})*sin(PI*n/{denominator:g})"
        crop_y = f"{pad_y:g}-({args.pan_y:g})*sin(PI*n/{denominator:g})"
        vf = (
            f"pad=iw+{2 * pad_x}:ih+{2 * pad_y}:{pad_x}:{pad_y}:color=white,"
            f"crop={width}:{height}:x='{crop_x}':y='{crop_y}'"
        )
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-loop",
        "1",
        "-framerate",
        str(args.fps),
        "-i",
        str(input_path),
        "-vf",
        vf,
        "-frames:v",
        str(args.frames),
        "-an",
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.encode_preset,
        "-tune",
        "zerolatency",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    start = perf_counter()
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    encode_ms = (perf_counter() - start) * 1000
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg drift failed with code {result.returncode}: {result.stderr}")
    return encode_ms


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
    return json.loads(result.stdout or "{}").get("streams", [{}])[0]


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


def create_contact_sheet(input_path: Path, frame_paths: list[Path], mask_path: Path, output_path: Path) -> None:
    labels = ["input", "mask", "first", "mid", "last"]
    paths = [input_path, mask_path, *frame_paths]
    thumbs = []
    for path in paths:
        with Image.open(path) as img:
            thumb = img.convert("RGB")
            thumb.thumbnail((384, 216), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (384, 216), "#f6f4ef")
            canvas.paste(thumb, ((384 - thumb.width) // 2, (216 - thumb.height) // 2))
            thumbs.append(canvas)
    sheet = Image.new("RGB", (768, 648), "#ece8de")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, thumb) in enumerate(zip(labels, thumbs)):
        x = 0 if index % 2 == 0 else 384
        y = (index // 2) * 216
        sheet.paste(thumb, (x, y))
        draw.rectangle([x, y + 190, x + 384, y + 215], fill="#f6f4ef", outline="#d8d2c7")
        draw.text((x + 8, y + 198), label, fill="#111111", font=font)
    sheet.save(output_path, quality=90)


def evaluate_video(
    input_path: Path,
    video_path: Path,
    run_dir: Path,
    mask_path: Path,
    probe: dict[str, Any],
    skip_ocr: bool = False,
) -> dict[str, Any]:
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

    input_ocr = "" if skip_ocr else ocr(input_path)
    input_norm = normalize_text(input_ocr)
    frames = []
    text_scores = []
    layout_scores = []
    for label, index, frame_path in zip(["first", "mid", "last"], indices, frame_paths):
        frame_ocr = "" if skip_ocr else ocr(frame_path)
        frame_norm = normalize_text(frame_ocr)
        text_score = -1.0 if skip_ocr else SequenceMatcher(None, input_norm, frame_norm).ratio() if input_norm else 0.0
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
        "note": "OCR skipped for this run." if skip_ocr else "OCR/layout proxy for hybrid deterministic animation; manual review is still required.",
    }
    (run_dir / "quality.json").write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
    create_contact_sheet(input_path, frame_paths, mask_path, run_dir / "contact-sheet.jpg")
    return quality


def ensure_results_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    path.write_text(
        "\t".join(
            [
                "run_id",
                "commit",
                "input_resolution",
                "output_resolution",
                "frames",
                "fps",
                "wall_time_ms",
                "preprocess_ms",
                "mask_ms",
                "render_ms",
                "encode_ms",
                "text_score",
                "layout_score",
                "motion_score",
                "loop_error",
                "protected_ratio",
                "status",
                "description",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def append_results(path: Path, metrics: dict[str, Any], quality: dict[str, Any]) -> None:
    ensure_results_header(path)
    row = [
        metrics["run_id"],
        metrics["commit"],
        metrics["input_resolution"],
        metrics["output_resolution"],
        str(metrics["frames"]),
        str(metrics["fps"]),
        f'{metrics["wall_time_ms"]:.3f}',
        f'{metrics["preprocess_ms"]:.3f}',
        f'{metrics["mask_ms"]:.3f}',
        f'{metrics["render_ms"]:.3f}',
        f'{metrics["encode_ms"]:.3f}',
        f'{quality["text_score"]:.4f}',
        f'{quality["layout_score"]:.4f}',
        f'{quality["motion_score"]:.4f}',
        f'{quality["loop_error"]:.4f}',
        f'{metrics["mask_stats"]["protected_ratio_dilated"]:.4f}',
        metrics["status"],
        metrics["description"].replace("\t", " "),
    ]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\t".join(row) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track B deterministic hybrid page animation benchmark.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--label", default="page-hybrid")
    parser.add_argument("--resolution", type=parse_resolution, default=(960, 544))
    parser.add_argument("--frames", type=int, default=33)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--append-results", action="store_true")
    parser.add_argument("--results-tsv", type=Path, default=RESULTS_TSV)
    parser.add_argument(
        "--reuse-input",
        action="store_true",
        help="Use an already-prepared input at the requested resolution instead of copying it into the run directory.",
    )
    parser.add_argument(
        "--skip-mask",
        action="store_true",
        help="Use an empty mask artifact. Useful for global ffmpeg-drift timing where no protected mask is required.",
    )
    parser.add_argument("--encode-preset", default="ultrafast")
    parser.add_argument("--crf", type=int, default=16)
    parser.add_argument(
        "--motion-mode",
        choices=["masked-affine", "lighting-only", "global-affine", "fast-drift", "ffmpeg-drift"],
        default="masked-affine",
    )
    parser.add_argument("--dark-threshold", type=int, default=125)
    parser.add_argument("--edge-threshold", type=float, default=24.0)
    parser.add_argument("--mask-dilate", type=int, default=5)
    parser.add_argument("--mask-blur", type=float, default=1.25)
    parser.add_argument("--pan-x", type=float, default=3.5)
    parser.add_argument("--pan-y", type=float, default=2.0)
    parser.add_argument("--zoom", type=float, default=0.012)
    parser.add_argument("--ambient", type=float, default=0.006)
    parser.add_argument("--shimmer", type=float, default=0.012)
    parser.add_argument("--drift-fill", choices=["pad", "overscan"], default="pad")
    parser.add_argument("--closed-loop", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--min-text-score", type=float, default=0.85)
    parser.add_argument("--min-layout-score", type=float, default=0.94)
    parser.add_argument("--min-motion-score", type=float, default=0.004)
    parser.add_argument("--max-loop-error", type=float, default=0.030)
    parser.add_argument(
        "--latency-target-ms",
        type=float,
        default=None,
        help="Latency gate. Defaults to generated video duration in milliseconds.",
    )
    parser.add_argument("--skip-text-gate", action="store_true")
    parser.add_argument("--skip-ocr", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.input.exists():
        raise SystemExit(f"Input image does not exist: {args.input}")
    width, height = args.resolution
    run_id = utc_run_id(args.label, width, height)
    run_dir = args.output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    input_path = args.input if args.reuse_input else run_dir / "input.png"
    mask_path = run_dir / "protected-mask.png"
    output_video = run_dir / "output.mp4"
    metrics_path = run_dir / "metrics.json"

    wall_start = perf_counter()
    prep_start = perf_counter()
    source: Image.Image | None
    if args.reuse_input:
        with Image.open(args.input) as prepared:
            if prepared.size != (width, height):
                raise SystemExit(
                    f"--reuse-input requires an input matching --resolution: "
                    f"{prepared.size[0]}x{prepared.size[1]} != {width}x{height}"
                )
            source = None if args.skip_mask and args.motion_mode == "ffmpeg-drift" else prepared.convert("RGB")
    else:
        source = fit_image(args.input, input_path, (width, height))
    preprocess_ms = (perf_counter() - prep_start) * 1000

    mask_start = perf_counter()
    if args.skip_mask:
        protected_mask = Image.new("L", (width, height), 0)
        mask_stats = {
            "protected_ratio_raw": 0.0,
            "protected_ratio_dilated": 0.0,
            "protected_ratio_soft_mean": 0.0,
        }
    else:
        if source is None:
            with Image.open(input_path) as prepared:
                source = prepared.convert("RGB")
        protected_mask, mask_stats = make_protected_mask(
            source,
            dark_threshold=args.dark_threshold,
            edge_threshold=args.edge_threshold,
            dilate=args.mask_dilate,
            blur=args.mask_blur,
        )
    protected_mask.save(mask_path, "PNG")
    mask_ms = (perf_counter() - mask_start) * 1000

    if args.motion_mode == "ffmpeg-drift":
        render_timings = {"render_ms": 0.0}
        encode_ms = encode_ffmpeg_drift(input_path, output_video, args)
    else:
        if source is None:
            with Image.open(input_path) as prepared:
                source = prepared.convert("RGB")
        frames, render_timings = render_frames(source, protected_mask, args)
        frames[min(len(frames) // 2, len(frames) - 1)].save(run_dir / "preview.jpg", "JPEG", quality=90)
        encode_ms = encode_frames(frames, output_video, args.fps, args.encode_preset, args.crf)
    wall_time_ms = (perf_counter() - wall_start) * 1000

    probe = probe_video(output_video)
    quality = evaluate_video(input_path, output_video, run_dir, mask_path, probe, skip_ocr=args.skip_ocr)
    if args.motion_mode == "ffmpeg-drift":
        with Image.open(run_dir / "frame-mid.png") as preview:
            preview.convert("RGB").save(run_dir / "preview.jpg", "JPEG", quality=90)
    latency_target_ms = args.latency_target_ms
    if latency_target_ms is None:
        latency_target_ms = (args.frames / args.fps) * 1000.0
    latency_ok = wall_time_ms <= latency_target_ms
    text_ok = args.skip_text_gate or quality["text_score"] >= args.min_text_score
    layout_ok = quality["layout_score"] >= args.min_layout_score
    motion_ok = quality["motion_score"] >= args.min_motion_score
    loop_ok = quality["loop_error"] <= args.max_loop_error
    status = "pass" if latency_ok and text_ok and layout_ok and motion_ok and loop_ok else "quality_fail"
    if not latency_ok:
        status = "latency_fail"

    metrics = {
        "run_id": run_id,
        "commit": git_commit(),
        "track": "B",
        "recipe": "deterministic_masked_parallax",
        "input_source": str(args.input),
        "input_resolution": f"{width}x{height}",
        "output_resolution": f"{width}x{height}",
        "frames": args.frames,
        "fps": args.fps,
        "wall_time_ms": wall_time_ms,
        "preprocess_ms": preprocess_ms,
        "mask_ms": mask_ms,
        "render_ms": render_timings["render_ms"],
        "model_ms": 0.0,
        "decode_or_composite_ms": render_timings["render_ms"],
        "encode_ms": encode_ms,
        "effective_generated_fps": args.frames / (wall_time_ms / 1000),
        "status": status,
        "description": "Track B deterministic masked parallax hybrid animation",
        "motion_params": {
            "motion_mode": args.motion_mode,
            "pan_x": args.pan_x,
            "pan_y": args.pan_y,
            "zoom": args.zoom,
            "ambient": args.ambient,
            "shimmer": args.shimmer,
            "drift_fill": args.drift_fill,
            "closed_loop": args.closed_loop,
        },
        "mask_params": {
            "dark_threshold": args.dark_threshold,
            "edge_threshold": args.edge_threshold,
            "mask_dilate": args.mask_dilate,
            "mask_blur": args.mask_blur,
        },
        "mask_stats": mask_stats,
        "gates": {
            "latency_ok": latency_ok,
            "latency_target_ms": latency_target_ms,
            "text_ok": text_ok,
            "layout_ok": layout_ok,
            "motion_ok": motion_ok,
            "loop_ok": loop_ok,
            "skip_text_gate": args.skip_text_gate,
            "min_text_score": args.min_text_score,
            "min_layout_score": args.min_layout_score,
            "min_motion_score": args.min_motion_score,
            "max_loop_error": args.max_loop_error,
        },
        "quality": {
            "text_score": quality["text_score"],
            "layout_score": quality["layout_score"],
            "motion_score": quality["motion_score"],
            "loop_error": quality["loop_error"],
        },
        "video_probe": probe,
        "artifacts": {
            "input": str(input_path),
            "output": str(output_video),
            "preview": str(run_dir / "preview.jpg"),
            "mask": str(mask_path),
            "contact_sheet": str(run_dir / "contact-sheet.jpg"),
            "quality": str(run_dir / "quality.json"),
            "metrics": str(metrics_path),
        },
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    if args.append_results:
        append_results(args.results_tsv, metrics, quality)
    print(json.dumps({"run_id": run_id, "status": status, "wall_time_ms": wall_time_ms, "output": str(output_video)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
