#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "outputs" / "track-b"
SWEEP_ROOT = ROOT / "docs" / "experiments" / "track-b" / "sweeps"
TRACK_B_RUNNER = ROOT / "scripts" / "track_b" / "hybrid_animation.py"

sys.path.insert(0, str(ROOT))
from scripts.track_b.hybrid_animation import fit_image  # noqa: E402


@dataclass(frozen=True)
class Case:
    label: str
    source: Path


CASES = [
    Case("naturalist", ROOT / "outputs" / "track-v" / "20260425T144658Z-fal-kling-fal-kling-naturalist-etching-960x540-960x540" / "input.png"),
    Case("canal", ROOT / "outputs" / "track-v" / "20260425T135104Z-fal-kling-canal-city-illustration-960x540" / "input.png"),
    Case("dense-text", ROOT / "outputs" / "track-v" / "20260425T134237Z-fal-kling-text-fixture-smoke-960x540" / "input.png"),
    Case("article", ROOT / "fixtures" / "track-d" / "pages" / "trackd-0000-article.png"),
    Case("dashboard", ROOT / "fixtures" / "track-d" / "pages" / "trackd-0001-dashboard.png"),
    Case("diagram", ROOT / "fixtures" / "track-d" / "pages" / "trackd-0002-diagram.png"),
    Case("product-grid", ROOT / "fixtures" / "track-d" / "pages" / "trackd-0003-product_grid.png"),
    Case("map-labels", ROOT / "fixtures" / "track-d" / "pages" / "trackd-0004-map_labels.png"),
    Case("illustration", ROOT / "fixtures" / "track-d" / "pages" / "trackd-0005-illustration.png"),
    Case("microtext", ROOT / "fixtures" / "track-d" / "pages" / "trackd-0006-microtext.png"),
]


FIELDS = [
    "sweep_id",
    "case",
    "source",
    "resolution",
    "frames",
    "fps",
    "pan_x",
    "pan_y",
    "drift_fill",
    "crf",
    "repeat",
    "run_id",
    "status",
    "wall_time_ms",
    "preprocess_ms",
    "mask_ms",
    "render_ms",
    "encode_ms",
    "effective_generated_fps",
    "layout_score",
    "motion_score",
    "loop_error",
    "text_score",
    "output",
    "contact_sheet",
]


def parse_resolution(value: str) -> tuple[int, int]:
    width, height = value.lower().split("x", 1)
    return int(width), int(height)


def profile_grid(profile: str) -> tuple[list[Case], list[int], list[tuple[float, float]], list[int], int]:
    if profile == "quick":
        return CASES[:3], [33, 121], [(1.0, 0.5), (2.0, 1.0), (3.0, 1.5)], [23], 1
    if profile == "focused":
        return CASES, [33, 65, 121], [(1.0, 0.5), (2.0, 1.0), (3.0, 1.5)], [18, 23, 28], 2
    return CASES, [33, 65, 121, 241], [(0.75, 0.375), (1.0, 0.5), (2.0, 1.0), (3.0, 1.5), (4.0, 2.0)], [18, 23, 28, 32], 3


def prepare_case(case: Case, prepared_dir: Path, resolution: tuple[int, int]) -> Path:
    width, height = resolution
    output = prepared_dir / f"{case.label}-{width}x{height}.png"
    if output.exists():
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    fit_image(case.source, output, resolution)
    return output


def run_one(
    case: Case,
    prepared_input: Path,
    resolution: tuple[int, int],
    frames: int,
    fps: int,
    pan_x: float,
    pan_y: float,
    drift_fill: str,
    crf: int,
    repeat: int,
) -> dict[str, Any]:
    width, height = resolution
    label = f"sweep-{case.label}-f{frames}-p{pan_x:g}x{pan_y:g}-crf{crf}-r{repeat}"
    cmd = [
        "python3",
        str(TRACK_B_RUNNER),
        "--input",
        str(prepared_input),
        "--label",
        label,
        "--resolution",
        f"{width}x{height}",
        "--motion-mode",
        "ffmpeg-drift",
        "--frames",
        str(frames),
        "--fps",
        str(fps),
        "--pan-x",
        str(pan_x),
        "--pan-y",
        str(pan_y),
        "--drift-fill",
        drift_fill,
        "--crf",
        str(crf),
        "--reuse-input",
        "--skip-mask",
        "--skip-ocr",
        "--skip-text-gate",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        return {
            "case": case.label,
            "source": str(case.source),
            "resolution": f"{width}x{height}",
            "frames": frames,
            "fps": fps,
            "pan_x": pan_x,
            "pan_y": pan_y,
            "drift_fill": drift_fill,
            "crf": crf,
            "repeat": repeat,
            "run_id": "",
            "status": "runner_fail",
            "error": proc.stderr.strip(),
        }
    summary = json.loads(proc.stdout)
    run_dir = OUTPUT_ROOT / summary["run_id"]
    metrics = json.loads((run_dir / "metrics.json").read_text())
    quality = json.loads((run_dir / "quality.json").read_text())
    return {
        "case": case.label,
        "source": str(case.source),
        "resolution": f"{width}x{height}",
        "frames": frames,
        "fps": fps,
        "pan_x": pan_x,
        "pan_y": pan_y,
        "drift_fill": drift_fill,
        "crf": crf,
        "repeat": repeat,
        "run_id": summary["run_id"],
        "status": metrics["status"],
        "wall_time_ms": metrics["wall_time_ms"],
        "preprocess_ms": metrics["preprocess_ms"],
        "mask_ms": metrics["mask_ms"],
        "render_ms": metrics["render_ms"],
        "encode_ms": metrics["encode_ms"],
        "effective_generated_fps": metrics["effective_generated_fps"],
        "layout_score": quality["layout_score"],
        "motion_score": quality["motion_score"],
        "loop_error": quality["loop_error"],
        "text_score": quality["text_score"],
        "output": metrics["artifacts"]["output"],
        "contact_sheet": metrics["artifacts"]["contact_sheet"],
    }


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def median(values: list[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def write_summary(path: Path, sweep_id: str, rows: list[dict[str, Any]], target_motion: float) -> None:
    passed = [row for row in rows if row.get("status") == "pass"]
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in passed:
        key = (row["case"], row["frames"], row["pan_x"], row["pan_y"], row.get("drift_fill", "pad"), row["crf"])
        groups[key].append(row)

    aggregate = []
    for (case, frames, pan_x, pan_y, drift_fill, crf), group in groups.items():
        aggregate.append(
            {
                "case": case,
                "frames": frames,
                "pan_x": pan_x,
                "pan_y": pan_y,
                "drift_fill": drift_fill,
                "crf": crf,
                "runs": len(group),
                "median_wall": median([float(row["wall_time_ms"]) for row in group]),
                "median_encode": median([float(row["encode_ms"]) for row in group]),
                "median_motion": median([float(row["motion_score"]) for row in group]),
                "median_layout": median([float(row["layout_score"]) for row in group]),
                "median_loop": median([float(row["loop_error"]) for row in group]),
                "example_output": group[0]["output"],
                "example_contact_sheet": group[0]["contact_sheet"],
            }
        )

    fastest = sorted(aggregate, key=lambda row: row["median_wall"])[:12]
    closest_motion = sorted(aggregate, key=lambda row: (abs(row["median_motion"] - target_motion), row["median_wall"]))[:12]
    by_case = []
    for case in sorted({row["case"] for row in aggregate}):
        candidates = [row for row in aggregate if row["case"] == case and row["frames"] == 121]
        if not candidates:
            continue
        by_case.append(min(candidates, key=lambda row: (abs(row["median_motion"] - target_motion), row["median_wall"])))

    def table(rows_to_write: list[dict[str, Any]]) -> str:
        lines = [
            "| case | frames | pan | fill | crf | median wall ms | median encode ms | motion | layout | loop |",
            "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in rows_to_write:
            lines.append(
                "| {case} | {frames} | {pan_x:g},{pan_y:g} | {drift_fill} | {crf} | {median_wall:.3f} | {median_encode:.3f} | {median_motion:.4f} | {median_layout:.4f} | {median_loop:.4f} |".format(
                    **row
                )
            )
        return "\n".join(lines)

    content = [
        f"# Track B ffmpeg-drift Sweep - {sweep_id}",
        "",
        f"Rows: {len(rows)}",
        f"Passed rows: {len(passed)}",
        f"Target Kling motion score: {target_motion:.4f}",
        "",
        "## Fastest Aggregates",
        "",
        table(fastest),
        "",
        "## Closest To Kling Motion",
        "",
        table(closest_motion),
        "",
        "## Best 121-Frame Candidate Per Case",
        "",
        table(sorted(by_case, key=lambda row: row["case"])),
        "",
        "## Interpretation",
        "",
        "This sweep measures deterministic page-plate drift, not generative re-layout. The useful product boundary is the fastest setting that remains visually subtle enough for a page family.",
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sweep Track B ffmpeg-drift speed and motion settings.")
    parser.add_argument("--profile", choices=["quick", "focused", "overnight"], default="quick")
    parser.add_argument("--resolution", default="960x540")
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--max-configs", type=int, default=None)
    parser.add_argument("--target-motion", type=float, default=0.0149)
    parser.add_argument("--drift-fill", choices=["pad", "overscan"], default="pad")
    parser.add_argument("--sweep-id", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    resolution = parse_resolution(args.resolution)
    sweep_id = args.sweep_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cases, frames_values, pan_values, crfs, profile_repeats = profile_grid(args.profile)
    repeats = args.repeats if args.repeats is not None else profile_repeats
    prepared_dir = OUTPUT_ROOT / "prepared" / sweep_id
    rows: list[dict[str, Any]] = []
    total_configs = len(cases) * len(frames_values) * len(pan_values) * len(crfs) * repeats
    if args.max_configs is not None:
        total_configs = min(total_configs, args.max_configs)

    config_index = 0
    for case in cases:
        if not case.source.exists():
            print(f"skip missing case {case.label}: {case.source}", flush=True)
            continue
        prepared = prepare_case(case, prepared_dir, resolution)
        for frames in frames_values:
            for pan_x, pan_y in pan_values:
                for crf in crfs:
                    for repeat in range(repeats):
                        if args.max_configs is not None and config_index >= args.max_configs:
                            break
                        config_index += 1
                        print(
                            f"[{config_index}/{total_configs}] {case.label} frames={frames} pan={pan_x:g},{pan_y:g} crf={crf} repeat={repeat}",
                            flush=True,
                        )
                        row = run_one(case, prepared, resolution, frames, args.fps, pan_x, pan_y, args.drift_fill, crf, repeat)
                        row["sweep_id"] = sweep_id
                        rows.append(row)
                    if args.max_configs is not None and config_index >= args.max_configs:
                        break
                if args.max_configs is not None and config_index >= args.max_configs:
                    break
            if args.max_configs is not None and config_index >= args.max_configs:
                break
        if args.max_configs is not None and config_index >= args.max_configs:
            break

    SWEEP_ROOT.mkdir(parents=True, exist_ok=True)
    rows_path = SWEEP_ROOT / f"ffmpeg-drift-sweep-{sweep_id}.tsv"
    summary_path = SWEEP_ROOT / f"ffmpeg-drift-sweep-{sweep_id}.md"
    write_rows(rows_path, rows)
    write_summary(summary_path, sweep_id, rows, args.target_motion)
    print(json.dumps({"sweep_id": sweep_id, "rows": len(rows), "tsv": str(rows_path), "summary": str(summary_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
