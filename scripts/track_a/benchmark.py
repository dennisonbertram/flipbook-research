#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from PIL import Image

from fixtures import create_text_heavy_fixture


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = ROOT / "fixtures" / "track-a" / "text-heavy-page.png"
DEFAULT_RESULTS = ROOT / "docs" / "experiments" / "track-a" / "results.tsv"


def parse_resolution(value: str) -> tuple[int, int]:
    try:
        width_s, height_s = value.lower().split("x", 1)
        width = int(width_s)
        height = int(height_s)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("resolution must look like 960x544") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("resolution dimensions must be positive")
    return width, height


def utc_run_id(recipe: str, width: int, height: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{recipe}-{width}x{height}"


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


def load_and_prepare_input(input_path: Path, output_input: Path, width: int, height: int) -> tuple[Image.Image, float]:
    start = perf_counter()
    with Image.open(input_path) as img:
        rgb = img.convert("RGB")
        if rgb.size != (width, height):
            rgb = rgb.resize((width, height), Image.Resampling.LANCZOS)
        else:
            rgb = rgb.copy()
    rgb.save(output_input, "PNG")
    return rgb, (perf_counter() - start) * 1000


def encode_frames(frames: list[Image.Image], output_path: Path, width: int, height: int, fps: int, preset: str) -> float:
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
            if frame.size != (width, height):
                frame = frame.resize((width, height), Image.Resampling.LANCZOS)
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


def probe_video(path: Path) -> dict:
    cmd = [
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
    ]
    try:
        result = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = json.loads(result.stdout)
        return data.get("streams", [{}])[0]
    except Exception as exc:
        return {"probe_error": str(exc)}


def normalize_score(value) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def append_results(path: Path, metrics: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "run_id",
        "commit",
        "resolution",
        "wall_time_ms",
        "model_ms",
        "decode_ms",
        "encode_ms",
        "peak_vram_gb",
        "text_score",
        "layout_score",
        "motion_score",
        "loop_error",
        "status",
        "description",
    ]
    if not path.exists():
        path.write_text("\t".join(header) + "\n", encoding="utf-8")

    row = [
        metrics["run_id"],
        metrics["commit"],
        f'{metrics["width"]}x{metrics["height"]}',
        f'{metrics["wall_time_ms"]:.3f}',
        f'{metrics["model_ms"]:.3f}',
        f'{metrics["decode_ms"]:.3f}',
        f'{metrics["encode_ms"]:.3f}',
        normalize_score(metrics.get("peak_vram_gb")),
        normalize_score(metrics.get("text_score")),
        normalize_score(metrics.get("layout_score")),
        normalize_score(metrics.get("motion_score")),
        normalize_score(metrics.get("loop_error")),
        metrics["status"],
        metrics["description"].replace("\t", " "),
    ]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\t".join(row) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a Track A 33-frame segment benchmark.")
    parser.add_argument("--recipe", default="stub_freeze", help="Recipe module under scripts/track_a/recipes.")
    parser.add_argument("--input", type=Path, default=None, help="Input image. Defaults to a generated text-heavy fixture.")
    parser.add_argument("--resolution", type=parse_resolution, default=(960, 544), help="Output resolution, e.g. 960x544.")
    parser.add_argument("--frames", type=int, default=33)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--guidance-scale", type=float, default=1.0)
    parser.add_argument("--prompt", default="subtle continuous loop, gentle parallax, small ambient motion, preserve text and diagram layout")
    parser.add_argument("--negative-prompt", default="text distortion, warped letters, layout drift, jitter, melting, blurry")
    parser.add_argument("--model-id", default="Lightricks/LTX-Video")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", default="bfloat16", choices=["bfloat16", "float16", "float32"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--encode-preset", default="ultrafast")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "track-a")
    parser.add_argument("--append-results", action="store_true", help="Append a compact row to docs/experiments/track-a/results.tsv.")
    parser.add_argument("--results-tsv", type=Path, default=DEFAULT_RESULTS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    width, height = args.resolution
    args.width = width
    args.height = height

    input_path = args.input
    if input_path is None:
        if not DEFAULT_FIXTURE.exists():
            create_text_heavy_fixture(DEFAULT_FIXTURE)
        input_path = DEFAULT_FIXTURE
    input_path = input_path.resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    recipe_module = importlib.import_module(f"recipes.{args.recipe}")
    setup_start = perf_counter()
    state = recipe_module.setup(args) if hasattr(recipe_module, "setup") else None
    setup_ms = (perf_counter() - setup_start) * 1000
    if isinstance(state, dict) and "setup_ms" in state:
        setup_ms = state["setup_ms"]

    run_id = utc_run_id(args.recipe, width, height)
    output_dir = args.output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    output_input = output_dir / "input.png"
    output_video = output_dir / "output.mp4"
    output_preview = output_dir / "preview.jpg"
    output_metrics = output_dir / "metrics.json"

    wall_start = perf_counter()
    input_image, preprocess_ms = load_and_prepare_input(input_path, output_input, width, height)
    generated = recipe_module.generate(input_image, args, state)
    frames = generated["frames"]
    if len(frames) != args.frames:
        raise RuntimeError(f"Recipe returned {len(frames)} frames, expected {args.frames}")

    encode_ms = encode_frames(frames, output_video, width, height, args.fps, args.encode_preset)
    frames[min(len(frames) // 2, len(frames) - 1)].save(output_preview, "JPEG", quality=90)
    wall_time_ms = (perf_counter() - wall_start) * 1000

    timings = generated.get("timings", {})
    quality = generated.get("quality", {})
    effective_generated_fps = args.frames / (wall_time_ms / 1000)
    status = "pass" if wall_time_ms <= 1300 else "near_miss" if wall_time_ms <= 3000 else "fail"
    if args.recipe.startswith("stub_"):
        status = "stub"

    metrics = {
        "run_id": run_id,
        "commit": git_commit(),
        "track": "A",
        "recipe": args.recipe,
        "input_source": str(input_path),
        "width": width,
        "height": height,
        "frames": args.frames,
        "fps": args.fps,
        "steps": args.steps,
        "guidance_scale": args.guidance_scale,
        "prompt": args.prompt,
        "negative_prompt": args.negative_prompt,
        "model_id": args.model_id,
        "device": args.device,
        "dtype": args.dtype,
        "setup_ms_excluded": setup_ms,
        "wall_time_ms": wall_time_ms,
        "preprocess_ms": preprocess_ms,
        "model_ms": float(timings.get("model_ms", 0.0)),
        "denoise_ms": float(timings.get("denoise_ms", 0.0)),
        "decode_ms": float(timings.get("decode_ms", 0.0)),
        "decode_or_composite_ms": float(timings.get("decode_ms", 0.0)),
        "encode_ms": encode_ms,
        "effective_generated_fps": effective_generated_fps,
        "peak_vram_gb": quality.get("peak_vram_gb"),
        "text_score": quality.get("text_score"),
        "layout_score": quality.get("layout_score"),
        "motion_score": quality.get("motion_score"),
        "loop_error": quality.get("loop_error"),
        "status": status,
        "description": generated.get("description", args.recipe),
        "artifacts": {
            "input": str(output_input),
            "output": str(output_video),
            "preview": str(output_preview),
            "metrics": str(output_metrics),
        },
        "video_probe": probe_video(output_video),
    }
    output_metrics.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    if args.append_results:
        append_results(args.results_tsv, metrics)

    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
