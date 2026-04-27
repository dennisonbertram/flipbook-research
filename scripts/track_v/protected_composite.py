#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.track_b.hybrid_animation import make_protected_mask  # noqa: E402
from scripts.track_v.fal_video_benchmark import evaluate_video, git_commit, probe_video  # noqa: E402


DEFAULT_SOURCE_RUN = ROOT / "outputs" / "track-v" / "20260426T234547Z-ltx-api-ltx-2-fast-official-ltx2-fast-text-preservation-1920x1080"
OUTPUT_ROOT = ROOT / "outputs" / "track-v"


def utc_run_id(label: str, width: int, height: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "protected-composite"
    return f"{stamp}-track-v-composite-{slug}-{width}x{height}"


def scaled_mask(mask: Image.Image, strength: float) -> Image.Image:
    if strength >= 0.999:
        return mask
    arr = np.asarray(mask, dtype=np.float32) * max(0.0, min(1.0, strength))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="L")


def ffmpeg_composite(
    video_path: Path,
    source_path: Path,
    mask_path: Path,
    output_path: Path,
    frames: int | None,
    crf: int,
    preset: str,
) -> float:
    filter_complex = (
        "[1:v]format=rgba[fgsrc];"
        "[2:v]format=gray[mask];"
        "[fgsrc][mask]alphamerge[fg];"
        "[0:v][fg]overlay=0:0:shortest=1,format=yuv420p[v]"
    )
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-loop",
        "1",
        "-i",
        str(source_path),
        "-loop",
        "1",
        "-i",
        str(mask_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
    ]
    if frames:
        cmd.extend(["-frames:v", str(frames)])
    cmd.append(str(output_path))
    start = perf_counter()
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    elapsed_ms = (perf_counter() - start) * 1000
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg composite failed: {result.stderr}")
    return elapsed_ms


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Composite protected source text/linework over a generated video run.")
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN)
    parser.add_argument("--label", default="ltx2-fast-text-protected-composite")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--dark-threshold", type=int, default=125)
    parser.add_argument("--edge-threshold", type=float, default=24.0)
    parser.add_argument("--mask-dilate", type=int, default=5)
    parser.add_argument("--mask-blur", type=float, default=1.25)
    parser.add_argument("--mask-strength", type=float, default=1.0)
    parser.add_argument("--crf", type=int, default=16)
    parser.add_argument("--preset", default="veryfast")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_input = args.source_run / "input.png"
    source_video = args.source_run / "output.mp4"
    if not source_input.exists() or not source_video.exists():
        raise SystemExit(f"source run must contain input.png and output.mp4: {args.source_run}")
    with Image.open(source_input) as image:
        source = image.convert("RGB")
    width, height = source.size
    run_id = utc_run_id(args.label, width, height)
    run_dir = args.output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    input_path = run_dir / "input.png"
    mask_path = run_dir / "protected-mask.png"
    output_path = run_dir / "output.mp4"
    shutil.copy2(source_input, input_path)

    mask_start = perf_counter()
    mask, mask_stats = make_protected_mask(
        source,
        dark_threshold=args.dark_threshold,
        edge_threshold=args.edge_threshold,
        dilate=args.mask_dilate,
        blur=args.mask_blur,
    )
    mask = scaled_mask(mask, args.mask_strength)
    mask.save(mask_path, "PNG")
    mask_ms = (perf_counter() - mask_start) * 1000

    source_probe = probe_video(source_video)
    frame_count = int(float(source_probe.get("nb_frames") or 0)) if source_probe.get("nb_frames") else None
    composite_ms = ffmpeg_composite(source_video, input_path, mask_path, output_path, frame_count, args.crf, args.preset)
    output_probe = probe_video(output_path)
    quality = evaluate_video(input_path, output_path, run_dir, output_probe)
    source_quality_path = args.source_run / "quality.json"
    source_quality: dict[str, Any] = json.loads(source_quality_path.read_text()) if source_quality_path.exists() else {}
    metrics = {
        "run_id": run_id,
        "commit": git_commit(),
        "model": "protected-composite",
        "source_run": str(args.source_run),
        "input_resolution": f"{width}x{height}",
        "output_frames": int(float(output_probe.get("nb_frames") or 0)) if output_probe.get("nb_frames") else None,
        "duration_s": float(output_probe.get("duration") or 0.0) if output_probe.get("duration") else None,
        "status": "pass" if quality["text_score"] >= 0.7 and quality["layout_score"] >= 0.8 else "quality_fail",
        "description": "Generated video with protected source text/linework composited back on top.",
        "mask_ms": mask_ms,
        "composite_ms": composite_ms,
        "mask_stats": mask_stats,
        "mask_params": {
            "dark_threshold": args.dark_threshold,
            "edge_threshold": args.edge_threshold,
            "mask_dilate": args.mask_dilate,
            "mask_blur": args.mask_blur,
            "mask_strength": args.mask_strength,
        },
        "source_quality": {
            "text_score": source_quality.get("text_score"),
            "layout_score": source_quality.get("layout_score"),
            "motion_score": source_quality.get("motion_score"),
            "loop_error": source_quality.get("loop_error"),
        },
        "quality": {
            "text_score": quality["text_score"],
            "layout_score": quality["layout_score"],
            "motion_score": quality["motion_score"],
            "loop_error": quality["loop_error"],
        },
        "video_probe": output_probe,
        "artifacts": {
            "input": str(input_path),
            "source_video": str(source_video),
            "mask": str(mask_path),
            "output": str(output_path),
            "contact_sheet": str(run_dir / "contact-sheet.jpg"),
            "quality": str(run_dir / "quality.json"),
            "metrics": str(run_dir / "metrics.json"),
        },
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": run_id, "status": metrics["status"], "composite_ms": composite_ms, "output": str(output_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
