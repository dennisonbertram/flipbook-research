#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN = ROOT / "outputs" / "track-v" / "20260426T234547Z-ltx-api-ltx-2-fast-official-ltx2-fast-text-preservation-1920x1080"
REPORT_DIR = ROOT / "docs" / "experiments" / "track-v"


def load_feature(path: Path, size: tuple[int, int]) -> np.ndarray:
    with Image.open(path) as source:
        image = source.convert("L").resize(size, Image.Resampling.BILINEAR)
        edges = image.filter(ImageFilter.FIND_EDGES)
    gray = np.asarray(image, dtype=np.float32) / 255.0
    edge = np.asarray(edges, dtype=np.float32) / 255.0
    feature = gray * 0.45 + edge * 0.55
    feature -= float(feature.mean())
    std = float(feature.std())
    if std > 1e-6:
        feature /= std
    return feature


def resize_array(array: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    image = Image.fromarray(np.clip((array - array.min()) / max(1e-6, array.max() - array.min()) * 255, 0, 255).astype(np.uint8))
    resized = image.resize(size, Image.Resampling.BILINEAR)
    out = np.asarray(resized, dtype=np.float32) / 255.0
    out -= float(out.mean())
    std = float(out.std())
    if std > 1e-6:
        out /= std
    return out


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(a * b))


def best_crop_match(
    input_path: Path,
    frame_path: Path,
    analysis_size: tuple[int, int],
    scales: list[float],
    grid_x: int,
    grid_y: int,
) -> dict[str, Any]:
    width, height = analysis_size
    source = load_feature(input_path, analysis_size)
    target = load_feature(frame_path, analysis_size)
    best: dict[str, Any] | None = None

    for scale in scales:
        crop_w = max(8, int(round(width / scale)))
        crop_h = max(8, int(round(height / scale)))
        max_x = width - crop_w
        max_y = height - crop_h
        xs = [0] if max_x <= 0 else [round(max_x * i / max(1, grid_x - 1)) for i in range(grid_x)]
        ys = [0] if max_y <= 0 else [round(max_y * i / max(1, grid_y - 1)) for i in range(grid_y)]
        for y in ys:
            for x in xs:
                crop = source[y : y + crop_h, x : x + crop_w]
                candidate = resize_array(crop, analysis_size)
                score = ncc(candidate, target)
                if best is None or score > best["score"]:
                    best = {
                        "score": score,
                        "scale": scale,
                        "crop_x": x / width,
                        "crop_y": y / height,
                        "crop_w": crop_w / width,
                        "crop_h": crop_h / height,
                    }

    assert best is not None
    best["unexplained"] = max(0.0, 1.0 - best["score"])
    return best


def classify_match(match: dict[str, Any]) -> str:
    score = float(match["score"])
    scale = float(match["scale"])
    if scale < 1.15 and score > 0.65:
        return "near-copy"
    if scale >= 1.35 and score > 0.42:
        return "camera-zoom-like"
    if score > 0.35:
        return "partially-crop-explainable"
    return "not-crop-explainable"


def analyze_run(run_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    input_path = run_dir / "input.png"
    if not input_path.exists():
        raise SystemExit(f"missing input image: {input_path}")
    frames = [
        ("first", run_dir / "frame-first.png"),
        ("mid", run_dir / "frame-mid.png"),
        ("last", run_dir / "frame-last.png"),
    ]
    missing = [str(path) for _, path in frames if not path.exists()]
    if missing:
        raise SystemExit(f"missing extracted frames: {missing}")

    scales = [1.0 + i * (args.max_scale - 1.0) / max(1, args.scale_steps - 1) for i in range(args.scale_steps)]
    results = []
    for label, frame_path in frames:
        match = best_crop_match(
            input_path=input_path,
            frame_path=frame_path,
            analysis_size=args.analysis_size,
            scales=scales,
            grid_x=args.grid_x,
            grid_y=args.grid_y,
        )
        match["label"] = label
        match["frame"] = str(frame_path)
        match["classification"] = classify_match(match)
        results.append(match)

    quality_path = run_dir / "quality.json"
    quality = json.loads(quality_path.read_text()) if quality_path.exists() else {}
    metrics_path = run_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
    return {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "model": metrics.get("model"),
        "status": metrics.get("status"),
        "api_wall_ms": metrics.get("api_wall_ms"),
        "duration_s": metrics.get("duration_s"),
        "output_frames": metrics.get("output_frames"),
        "quality": {
            "text_score": quality.get("text_score"),
            "layout_score": quality.get("layout_score"),
            "motion_score": quality.get("motion_score"),
            "loop_error": quality.get("loop_error"),
        },
        "crop_matches": results,
    }


def write_report(path: Path, analyses: list[dict[str, Any]]) -> None:
    lines = [
        "# Track V Camera Path Diagnostic",
        "",
        "This diagnostic asks whether generated frames are explainable as a crop/zoom of the input page. It is a proxy for camera-collapse versus actual page-preserving generation.",
        "",
        "| run | model | frame | class | crop score | scale | crop x,y,w,h | text | layout | motion |",
        "| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for analysis in analyses:
        quality = analysis["quality"]
        for match in analysis["crop_matches"]:
            lines.append(
                "| {run} | {model} | {frame} | {klass} | {score:.3f} | {scale:.2f} | {crop_x:.2f},{crop_y:.2f},{crop_w:.2f},{crop_h:.2f} | {text} | {layout} | {motion} |".format(
                    run=analysis["run_id"],
                    model=analysis.get("model") or "",
                    frame=match["label"],
                    klass=match["classification"],
                    score=match["score"],
                    scale=match["scale"],
                    crop_x=match["crop_x"],
                    crop_y=match["crop_y"],
                    crop_w=match["crop_w"],
                    crop_h=match["crop_h"],
                    text="" if quality.get("text_score") is None else f"{quality['text_score']:.3f}",
                    layout="" if quality.get("layout_score") is None else f"{quality['layout_score']:.3f}",
                    motion="" if quality.get("motion_score") is None else f"{quality['motion_score']:.3f}",
                )
            )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "- `near-copy`: frame is mostly the source plate.",
            "- `camera-zoom-like`: frame is largely explainable as a zoom/crop of the source.",
            "- `partially-crop-explainable`: model keeps some source geometry but also repaints or warps.",
            "- `not-crop-explainable`: frame no longer maps cleanly to the source image.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_size(value: str) -> tuple[int, int]:
    width, height = value.lower().split("x", 1)
    return int(width), int(height)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose whether video frames are best explained as source-page camera crops.")
    parser.add_argument("runs", nargs="*", type=Path, default=[DEFAULT_RUN])
    parser.add_argument("--analysis-size", type=parse_size, default=(240, 135))
    parser.add_argument("--max-scale", type=float, default=4.0)
    parser.add_argument("--scale-steps", type=int, default=31)
    parser.add_argument("--grid-x", type=int, default=25)
    parser.add_argument("--grid-y", type=int, default=15)
    parser.add_argument("--json-output", type=Path, default=REPORT_DIR / "track-v-camera-path-diagnostic-2026-04-27.json")
    parser.add_argument("--report-output", type=Path, default=REPORT_DIR / "track-v-camera-path-diagnostic-2026-04-27.md")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    analyses = [analyze_run(run, args) for run in args.runs]
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(analyses, indent=2) + "\n", encoding="utf-8")
    write_report(args.report_output, analyses)
    print(json.dumps({"runs": len(analyses), "json": str(args.json_output), "report": str(args.report_output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
