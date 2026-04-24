#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
from zoneinfo import ZoneInfo
from difflib import SequenceMatcher

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "outputs" / "track-a"
QUALITY_TSV = ROOT / "docs" / "experiments" / "track-a" / "quality.tsv"


def next_local_deadline(hhmm: str) -> datetime:
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    hour, minute = [int(part) for part in hhmm.split(":", 1)]
    deadline = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if deadline <= now:
        deadline += timedelta(days=1)
    return deadline


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
    vf = f"select=eq(n\\,{frame_index})"
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
            vf,
            "-vframes",
            "1",
            str(output),
        ],
        check=True,
    )


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


def ensure_quality_header() -> None:
    QUALITY_TSV.parent.mkdir(parents=True, exist_ok=True)
    if QUALITY_TSV.exists():
        return
    QUALITY_TSV.write_text(
        "\t".join(
            [
                "run_id",
                "resolution",
                "steps",
                "status",
                "wall_time_ms",
                "text_score",
                "layout_score",
                "loop_error",
                "input_ocr_chars",
                "mid_ocr_chars",
                "mid_ocr_sample",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def append_quality_row(metrics: dict, quality: dict) -> None:
    ensure_quality_header()
    sample = quality["frames"][1]["ocr"].replace("\t", " ").replace("\n", " ")
    sample = re.sub(r"\s+", " ", sample).strip()[:220]
    row = [
        metrics["run_id"],
        f'{metrics["width"]}x{metrics["height"]}',
        str(metrics["steps"]),
        metrics["status"],
        f'{metrics["wall_time_ms"]:.3f}',
        f'{quality["text_score"]:.4f}',
        f'{quality["layout_score"]:.4f}',
        f'{quality["loop_error"]:.4f}',
        str(len(quality["input_ocr"])),
        str(len(quality["frames"][1]["ocr"])),
        sample,
    ]
    with QUALITY_TSV.open("a", encoding="utf-8") as handle:
        handle.write("\t".join(row) + "\n")


def evaluate_run(metrics_path: Path, force: bool = False) -> bool:
    run_dir = metrics_path.parent
    quality_path = run_dir / "quality.json"
    if quality_path.exists() and not force:
        return False

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if metrics.get("status") == "crash":
        return False

    input_path = Path(metrics["artifacts"]["input"])
    video_path = Path(metrics["artifacts"]["output"])
    if not input_path.exists() or not video_path.exists():
        return False

    frames_count = int(metrics.get("frames", 33))
    indices = [0, max(0, frames_count // 2), max(0, frames_count - 1)]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        frame_paths = []
        for i, idx in enumerate(indices):
            frame_path = tmp_path / f"frame_{i}_{idx}.png"
            extract_frame(video_path, idx, frame_path)
            frame_paths.append(frame_path)

        input_ocr = ocr(input_path)
        input_norm = normalize_text(input_ocr)
        frame_items = []
        text_scores = []
        layout_scores = []

        for idx, frame_path in zip(indices, frame_paths):
            frame_ocr = ocr(frame_path)
            frame_norm = normalize_text(frame_ocr)
            text_score = SequenceMatcher(None, input_norm, frame_norm).ratio() if input_norm else 0.0
            layout_score = image_similarity(input_path, frame_path)
            text_scores.append(text_score)
            layout_scores.append(layout_score)
            frame_items.append(
                {
                    "frame_index": idx,
                    "ocr": frame_ocr,
                    "text_score": text_score,
                    "layout_score": layout_score,
                }
            )

        loop_error = frame_diff(frame_paths[0], frame_paths[-1])

    quality = {
        "run_id": metrics["run_id"],
        "input_ocr": input_ocr,
        "text_score": float(np.mean(text_scores)),
        "layout_score": float(np.mean(layout_scores)),
        "loop_error": loop_error,
        "frames": frame_items,
        "note": "OCR similarity plus low-resolution image similarity proxy; manual review still required.",
    }

    metrics["text_score"] = quality["text_score"]
    metrics["layout_score"] = quality["layout_score"]
    metrics["loop_error"] = quality["loop_error"]
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    quality_path.write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
    append_quality_row(metrics, quality)
    return True


def iter_metrics() -> list[Path]:
    return sorted(OUTPUT_ROOT.glob("*/metrics.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Track A text preservation for completed runs.")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--until", default="08:00")
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-runs", type=int, default=0)
    args = parser.parse_args()

    deadline = next_local_deadline(args.until)
    processed = 0

    while True:
        batch_count = 0
        for metrics_path in iter_metrics():
            if args.max_runs and processed >= args.max_runs:
                return 0
            try:
                did_process = evaluate_run(metrics_path, force=args.force)
            except Exception as exc:
                print(f"quality error {metrics_path}: {exc}", flush=True)
                did_process = False
            if did_process:
                processed += 1
                batch_count += 1
                print(f"quality processed {metrics_path.parent.name}", flush=True)

        if not args.watch:
            break
        print(f"quality idle processed_total={processed} batch={batch_count}", flush=True)
        if datetime.now(deadline.tzinfo) >= deadline:
            break
        sleep(args.interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
