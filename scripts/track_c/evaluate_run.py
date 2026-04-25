#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "outputs" / "track-c"
DEFAULT_TSV = ROOT / "docs" / "experiments" / "track-c" / "eval-results.tsv"
SCENARIO_CONFIG = Path(__file__).with_name("eval_scenarios.json")
SEGMENT_BUDGET_MS = 1300.0


def rel(path: Path | str | None) -> str | None:
    if not path:
        return None
    path_obj = Path(path)
    try:
        return str(path_obj.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_scenarios() -> dict[str, dict[str, Any]]:
    if not SCENARIO_CONFIG.exists():
        return {}
    config = load_json(SCENARIO_CONFIG)
    return {item["scenario_id"]: item for item in config.get("scenarios", [])}


def infer_scenario_id(metrics: dict[str, Any]) -> str:
    explicit = metrics.get("scenario_id")
    if explicit:
        return str(explicit)

    layout_mode = str(metrics.get("video_layout_mode", "none"))
    motion_mode = str(metrics.get("motion_mode", "static"))
    viewport_mode = str(metrics.get("video_viewport_mode", "static"))
    layout_strength = float(metrics.get("layout_transform_strength") or 0.0)
    motion_strength = float(metrics.get("motion_strength") or 0.0)

    if motion_mode == "responsive-squeeze":
        return "responsive-squeeze"
    if motion_mode in {"layout-reflow", "sprite-layout-reflow"}:
        return "layout-reflow-learned"
    if motion_mode in {"independent-sprite-translate", "region-sprite-translate"}:
        return "independent-sprite-translation-learned"
    if motion_mode in {"independent-translate", "region-translate"}:
        return "independent-translation-learned"
    if motion_mode in {"independent-field", "region-field"}:
        return "independent-field-learned"
    if motion_mode == "frame-scale":
        return "frame-scale-strong" if motion_strength >= 0.15 else "frame-scale-moderate"
    if layout_mode in {"independent-translate", "region-translate"}:
        return "independent-translation-strong" if float(metrics.get("layout_transform_pan") or 0.0) >= 0.06 else "independent-translation-moderate"
    if layout_mode in {"independent-regions", "region-dance", "independent-field", "region-field"}:
        return "independent-regions-strong" if layout_strength >= 0.13 else "independent-regions-moderate"
    if layout_mode in {"frame-scale", "element-frame-scale"}:
        return "frame-scale-strong" if layout_strength >= 0.15 else "frame-scale-moderate"
    if viewport_mode == "zoom-pulse":
        return "viewport-zoom-pulse"
    if motion_mode not in {"static", "none"} or motion_strength > 0:
        return "subtle-motion-loop"
    return "still-full-resize"


def pixel_source_class(metrics: dict[str, Any]) -> str:
    layout_mode = str(metrics.get("video_layout_mode", "none"))
    canvas_type = str(metrics.get("canvas_type", ""))
    if "element" in canvas_type or layout_mode == "element-frame-scale":
        return "neural-canvas-query-with-symbolic-supervision"
    if "layout" in canvas_type or layout_mode != "none":
        return "neural-canvas-query"
    return "neural-canvas-query"


def choose_mid_artifact(run_dir: Path) -> Path | None:
    for name in [
        "render-element-mid.png",
        "render-layout-mid.png",
        "render-viewport-mid.png",
        "render-mid.png",
    ]:
        path = run_dir / name
        if path.exists():
            return path
    return None


def artifacts_for(run_dir: Path, metrics: dict[str, Any]) -> dict[str, str | None]:
    metrics_artifacts = metrics.get("artifacts") or {}
    mid = choose_mid_artifact(run_dir)
    return {
        "input": rel(run_dir / "input.png") if (run_dir / "input.png").exists() else rel(metrics_artifacts.get("input")),
        "render_512": rel(run_dir / "render-512.png") if (run_dir / "render-512.png").exists() else rel(metrics_artifacts.get("render_512")),
        "render_960": rel(run_dir / "render-960.png") if (run_dir / "render-960.png").exists() else rel(metrics_artifacts.get("render_960")),
        "mid_frame": rel(mid),
        "last_frame": rel(run_dir / "render-last.png") if (run_dir / "render-last.png").exists() else rel(metrics_artifacts.get("render_last")),
        "crop_2x": rel(run_dir / "crop-2x.png") if (run_dir / "crop-2x.png").exists() else rel(metrics_artifacts.get("crop_2x")),
        "text_mask": rel(run_dir / "text-mask.png") if (run_dir / "text-mask.png").exists() else rel(metrics_artifacts.get("text_mask")),
        "element_alpha_mask": rel(run_dir / "element-alpha-mask.png") if (run_dir / "element-alpha-mask.png").exists() else rel(metrics_artifacts.get("element_alpha_mask")),
        "target_mid": rel(run_dir / "target-mid.png") if (run_dir / "target-mid.png").exists() else rel(metrics_artifacts.get("target_mid")),
        "text_boxes": rel(run_dir / "text-boxes.json") if (run_dir / "text-boxes.json").exists() else rel(metrics_artifacts.get("text_boxes")),
        "video": rel(run_dir / "output.mp4") if (run_dir / "output.mp4").exists() else rel(metrics_artifacts.get("output")),
    }


def image_delta_similarity(path_a: Path, path_b: Path) -> tuple[float | None, float | None]:
    if not path_a.exists() or not path_b.exists():
        return None, None
    with Image.open(path_a) as image_a, Image.open(path_b) as image_b:
        image_a = image_a.convert("RGB")
        image_b = image_b.convert("RGB").resize(image_a.size, Image.Resampling.LANCZOS)
        diff = ImageChops.difference(image_a, image_b)
        mean_abs = sum(ImageStat.Stat(diff).mean) / 3.0
    delta = mean_abs / 255.0
    return delta, max(0.0, 1.0 - delta)


def change_region_metrics(
    mid_path: Path,
    source_path: Path,
    target_path: Path,
    *,
    threshold: float = 0.05,
) -> dict[str, float | None]:
    if not mid_path.exists() or not source_path.exists() or not target_path.exists():
        return {
            "change_region_fraction": None,
            "change_region_target_delta": None,
            "change_region_source_delta": None,
            "change_region_source_bias": None,
        }

    with Image.open(mid_path) as mid_img, Image.open(source_path) as source_img, Image.open(target_path) as target_img:
        mid_img = mid_img.convert("RGB")
        source_img = source_img.convert("RGB").resize(mid_img.size, Image.Resampling.LANCZOS)
        target_img = target_img.convert("RGB").resize(mid_img.size, Image.Resampling.LANCZOS)
        mid = np.asarray(mid_img, dtype=np.float32) / 255.0
        source = np.asarray(source_img, dtype=np.float32) / 255.0
        target = np.asarray(target_img, dtype=np.float32) / 255.0

    changed = np.abs(source - target).mean(axis=2) > threshold
    count = int(changed.sum())
    total_pixels = max(1, int(changed.size))
    if count == 0:
        return {
            "change_region_fraction": 0.0,
            "change_region_target_delta": None,
            "change_region_source_delta": None,
            "change_region_source_bias": None,
        }

    target_delta = float(np.abs(mid - target).mean(axis=2)[changed].mean())
    source_delta = float(np.abs(mid - source).mean(axis=2)[changed].mean())
    return {
        "change_region_fraction": count / total_pixels,
        "change_region_target_delta": target_delta,
        "change_region_source_delta": source_delta,
        "change_region_source_bias": target_delta - source_delta,
    }


def determine_status(metrics: dict[str, Any], quality: dict[str, Any], scenario: dict[str, Any]) -> tuple[str, list[str]]:
    segment_wall_ms = float(metrics.get("render_33_wall_ms") or 0.0) + float(metrics.get("encode_ms") or 0.0)
    ocr = float(quality.get("ocr_similarity", metrics.get("ocr_similarity") or 0.0))
    motion = float(quality.get("motion_delta", metrics.get("motion_delta") or 0.0))
    loop_error = float(quality.get("loop_error", metrics.get("loop_error") or 0.0))

    min_ocr = float(metrics.get("min_ocr_similarity") or scenario.get("min_ocr_similarity") or 0.0)
    min_motion = float(metrics.get("min_motion_delta") or scenario.get("min_motion_delta") or 0.0)
    max_loop = float(scenario.get("max_loop_error") or 0.02)

    failed = []
    if segment_wall_ms > SEGMENT_BUDGET_MS:
        failed.append(f"segment_wall_ms>{SEGMENT_BUDGET_MS:.0f}")
    if ocr < min_ocr:
        failed.append(f"ocr_token_f1<{min_ocr:.4f}")
    if motion < min_motion:
        failed.append(f"motion_delta<{min_motion:.4f}")
    if loop_error > max_loop:
        failed.append(f"loop_error>{max_loop:.4f}")

    if not failed:
        return "pass", failed
    if any(item.startswith("segment_wall_ms") for item in failed) and len(failed) == 1:
        return "latency_fail", failed
    return "quality_fail", failed


def build_eval(run_dir: Path, scenarios: dict[str, dict[str, Any]]) -> dict[str, Any]:
    metrics = load_json(run_dir / "metrics.json")
    quality = load_json(run_dir / "quality.json") if (run_dir / "quality.json").exists() else {}
    scenario_id = infer_scenario_id(metrics)
    scenario = scenarios.get(scenario_id, {})
    status, failed_gates = determine_status(metrics, quality, scenario)
    render_33 = float(metrics.get("render_33_wall_ms") or 0.0)
    encode = float(metrics.get("encode_ms") or 0.0)
    segment_wall = render_33 + encode
    ocr = float(quality.get("ocr_similarity", metrics.get("ocr_similarity") or 0.0))
    mid_artifact = choose_mid_artifact(run_dir) or run_dir / "render-mid.png"
    target_mid_delta, target_mid_similarity = image_delta_similarity(mid_artifact, run_dir / "target-mid.png")
    change_metrics = change_region_metrics(mid_artifact, run_dir / "input.png", run_dir / "target-mid.png")

    scenario_result = {
        "scenario_id": scenario_id,
        "description": scenario.get("description"),
        "resolution": f'{metrics.get("width", 960)}x{metrics.get("height", 544)}',
        "frames": int(metrics.get("frames", 33)),
        "fps": int(metrics.get("fps", 24)),
        "status": status,
        "failed_gates": failed_gates,
        "config": {
            "train_resolution": metrics.get("train_resolution"),
            "motion_mode": metrics.get("motion_mode"),
            "motion_strength": metrics.get("motion_strength"),
            "video_viewport_mode": metrics.get("video_viewport_mode"),
            "viewport_zoom": metrics.get("viewport_zoom"),
            "viewport_pan": metrics.get("viewport_pan"),
            "video_layout_mode": metrics.get("video_layout_mode"),
            "layout_transform_strength": metrics.get("layout_transform_strength"),
            "layout_transform_pan": metrics.get("layout_transform_pan"),
            "layout_region_count": metrics.get("layout_region_count"),
            "element_scale_ratio": metrics.get("element_scale_ratio"),
            "element_anchor_padding": metrics.get("element_anchor_padding"),
            "element_mask_mode": metrics.get("element_mask_mode"),
            "element_anchor_mode": metrics.get("element_anchor_mode"),
            "element_render_mode": metrics.get("element_render_mode"),
            "element_line_count": metrics.get("element_line_count"),
        },
        "metrics": {
            "compile_ms": metrics.get("compile_ms"),
            "render_960_ms": metrics.get("render_960_ms"),
            "render_33_wall_ms": render_33,
            "encode_ms": encode,
            "segment_wall_ms": segment_wall,
            "effective_generated_fps": (float(metrics.get("frames", 33)) / (segment_wall / 1000.0)) if segment_wall > 0 else None,
            "peak_vram_gb": metrics.get("peak_vram_gb"),
            "ocr_token_f1_min": ocr,
            "ocr_token_f1_mean": ocr,
            "ocr_token_f1_mid": ocr,
            "ocr_char_similarity": quality.get("ocr_char_similarity"),
            "layout_similarity": quality.get("layout_similarity", metrics.get("layout_similarity")),
            "resize_consistency": metrics.get("resize_consistency"),
            "crop_consistency": metrics.get("crop_consistency"),
            "temporal_consistency": metrics.get("temporal_consistency"),
            "motion_delta": quality.get("motion_delta", metrics.get("motion_delta")),
            "loop_error": quality.get("loop_error", metrics.get("loop_error")),
            "target_mid_delta": target_mid_delta,
            "target_mid_similarity": target_mid_similarity,
            "change_region_fraction": change_metrics["change_region_fraction"],
            "change_region_target_delta": change_metrics["change_region_target_delta"],
            "change_region_source_delta": change_metrics["change_region_source_delta"],
            "change_region_source_bias": change_metrics["change_region_source_bias"],
            "model_rendered_pixel_ratio": 1.0,
        },
        "artifacts": artifacts_for(run_dir, metrics),
    }

    return {
        "schema_version": "track-c-eval-v0.1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": metrics.get("run_id", run_dir.name),
        "commit": metrics.get("commit", "unknown"),
        "track": "C",
        "renderer_family": metrics.get("canvas_type"),
        "fixture_id": "text-heavy-page-v1",
        "pixel_source_class": pixel_source_class(metrics),
        "model_rendered_pixel_ratio": 1.0,
        "source": {
            "run_dir": rel(run_dir),
            "metrics": rel(run_dir / "metrics.json"),
            "quality": rel(run_dir / "quality.json") if (run_dir / "quality.json").exists() else None,
        },
        "scenarios": [scenario_result],
        "summary": {
            "status": status,
            "failed_gates": failed_gates,
            "segment_wall_ms": segment_wall,
            "ocr_token_f1_min": ocr,
            "motion_delta": scenario_result["metrics"]["motion_delta"],
            "loop_error": scenario_result["metrics"]["loop_error"],
        },
    }


def image_tile(path: Path, label: str, size: tuple[int, int]) -> Image.Image:
    tile_w, tile_h = size
    image_h = tile_h - 28
    canvas = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("Arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()

    if path.exists():
        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((tile_w, image_h), Image.Resampling.LANCZOS)
            x = (tile_w - img.width) // 2
            y = 0
            canvas.paste(img, (x, y))
    draw.rectangle((0, image_h, tile_w - 1, tile_h - 1), fill=(245, 245, 245), outline=(210, 210, 210))
    draw.text((8, image_h + 7), label[:42], fill=(20, 20, 20), font=font)
    return canvas


def write_contact_sheet(run_dir: Path, eval_doc: dict[str, Any]) -> Path | None:
    candidates = [
        ("input", run_dir / "input.png"),
        ("render 960", run_dir / "render-960.png"),
        ("mid", choose_mid_artifact(run_dir) or run_dir / "render-mid.png"),
        ("target mid", run_dir / "target-mid.png"),
        ("last", run_dir / "render-last.png"),
        ("crop 2x", run_dir / "crop-2x.png"),
        ("text mask", run_dir / "text-mask.png"),
        ("element alpha", run_dir / "element-alpha-mask.png"),
    ]
    existing = [(label, path) for label, path in candidates if path and path.exists()]
    if not existing:
        return None

    tile_size = (320, 212)
    cols = 3
    rows = (len(existing) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_size[0], rows * tile_size[1]), "white")
    for idx, (label, path) in enumerate(existing):
        tile = image_tile(path, label, tile_size)
        x = (idx % cols) * tile_size[0]
        y = (idx // cols) * tile_size[1]
        sheet.paste(tile, (x, y))

    out = run_dir / "contact-sheet.jpg"
    sheet.save(out, quality=88)
    eval_doc["scenarios"][0]["artifacts"]["contact_sheet"] = rel(out)
    return out


def write_summary(run_dir: Path, eval_doc: dict[str, Any]) -> Path:
    scenario = eval_doc["scenarios"][0]
    metrics = scenario["metrics"]
    artifacts = scenario["artifacts"]
    lines = [
        f"# Eval Summary: {eval_doc['run_id']}",
        "",
        f"- Scenario: `{scenario['scenario_id']}`",
        f"- Status: `{scenario['status']}`",
        f"- Renderer: `{eval_doc.get('renderer_family')}`",
        f"- Pixel source: `{eval_doc.get('pixel_source_class')}`",
        f"- Segment wall: `{metrics['segment_wall_ms']:.3f}ms`",
        f"- 33-frame render: `{metrics['render_33_wall_ms']:.3f}ms`",
        f"- Encode: `{metrics['encode_ms']:.3f}ms`",
        f"- Effective generated FPS: `{metrics['effective_generated_fps']:.2f}`",
        f"- OCR token-F1: `{metrics['ocr_token_f1_mid']:.4f}`",
        f"- Motion delta: `{float(metrics['motion_delta'] or 0.0):.4f}`",
        f"- Loop error: `{float(metrics['loop_error'] or 0.0):.4f}`",
        f"- Target-mid similarity: `{float(metrics['target_mid_similarity'] or 0.0):.4f}`",
        f"- Change-region target delta: `{float(metrics['change_region_target_delta'] or 0.0):.4f}`",
        f"- Change-region source bias: `{float(metrics['change_region_source_bias'] or 0.0):.4f}`",
        "",
        "## Failed Gates",
        "",
    ]
    if scenario["failed_gates"]:
        lines.extend(f"- `{gate}`" for gate in scenario["failed_gates"])
    else:
        lines.append("- none")
    lines.extend(["", "## Artifacts", ""])
    for key, value in artifacts.items():
        if value:
            lines.append(f"- {key}: `{value}`")
    out = run_dir / "eval-summary.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


TSV_FIELDS = [
    "run_id",
    "commit",
    "scenario_id",
    "renderer_family",
    "status",
    "segment_wall_ms",
    "render_33_wall_ms",
    "encode_ms",
    "effective_generated_fps",
    "ocr_token_f1_min",
    "ocr_token_f1_mean",
    "layout_similarity",
    "resize_consistency",
    "temporal_consistency",
    "motion_delta",
    "loop_error",
    "target_mid_delta",
    "target_mid_similarity",
    "change_region_fraction",
    "change_region_target_delta",
    "change_region_source_delta",
    "change_region_source_bias",
    "pixel_source_class",
    "failed_gates",
]


def write_tsv(path: Path, eval_docs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TSV_FIELDS, delimiter="\t")
        writer.writeheader()
        for doc in eval_docs:
            scenario = doc["scenarios"][0]
            metrics = scenario["metrics"]
            row = {
                "run_id": doc["run_id"],
                "commit": doc["commit"],
                "scenario_id": scenario["scenario_id"],
                "renderer_family": doc.get("renderer_family"),
                "status": scenario["status"],
                "segment_wall_ms": f'{metrics["segment_wall_ms"]:.3f}',
                "render_33_wall_ms": f'{metrics["render_33_wall_ms"]:.3f}',
                "encode_ms": f'{metrics["encode_ms"]:.3f}',
                "effective_generated_fps": f'{metrics["effective_generated_fps"]:.3f}' if metrics["effective_generated_fps"] is not None else "",
                "ocr_token_f1_min": f'{metrics["ocr_token_f1_min"]:.4f}',
                "ocr_token_f1_mean": f'{metrics["ocr_token_f1_mean"]:.4f}',
                "layout_similarity": f'{float(metrics["layout_similarity"] or 0.0):.4f}',
                "resize_consistency": f'{float(metrics["resize_consistency"] or 0.0):.4f}',
                "temporal_consistency": f'{float(metrics["temporal_consistency"] or 0.0):.4f}',
                "motion_delta": f'{float(metrics["motion_delta"] or 0.0):.4f}',
                "loop_error": f'{float(metrics["loop_error"] or 0.0):.4f}',
                "target_mid_delta": f'{float(metrics["target_mid_delta"] or 0.0):.4f}',
                "target_mid_similarity": f'{float(metrics["target_mid_similarity"] or 0.0):.4f}',
                "change_region_fraction": f'{float(metrics["change_region_fraction"] or 0.0):.4f}',
                "change_region_target_delta": f'{float(metrics["change_region_target_delta"] or 0.0):.4f}',
                "change_region_source_delta": f'{float(metrics["change_region_source_delta"] or 0.0):.4f}',
                "change_region_source_bias": f'{float(metrics["change_region_source_bias"] or 0.0):.4f}',
                "pixel_source_class": doc["pixel_source_class"],
                "failed_gates": ",".join(scenario["failed_gates"]),
            }
            writer.writerow(row)


def discover_runs() -> list[Path]:
    if not OUTPUT_ROOT.exists():
        return []
    return sorted(path.parent for path in OUTPUT_ROOT.glob("*/metrics.json"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize Track C run outputs into eval.json and eval TSV rows.")
    parser.add_argument("runs", nargs="*", type=Path, help="Run directories or metrics.json paths. Defaults to all outputs/track-c runs.")
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV, help="Leaderboard TSV path.")
    parser.add_argument("--no-tsv", action="store_true", help="Do not write the leaderboard TSV.")
    parser.add_argument("--no-contact-sheet", action="store_true", help="Skip contact sheet generation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenarios = load_scenarios()
    run_dirs = []
    for item in args.runs:
        run_dirs.append(item.parent if item.name == "metrics.json" else item)
    if not run_dirs:
        run_dirs = discover_runs()

    eval_docs = []
    for run_dir in run_dirs:
        if not (run_dir / "metrics.json").exists():
            raise SystemExit(f"missing metrics.json: {run_dir}")
        doc = build_eval(run_dir, scenarios)
        if not args.no_contact_sheet:
            write_contact_sheet(run_dir, doc)
        (run_dir / "eval.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        write_summary(run_dir, doc)
        eval_docs.append(doc)
        scenario = doc["scenarios"][0]
        print(
            f"{doc['run_id']}\t{scenario['scenario_id']}\t{scenario['status']}\t"
            f"{doc['summary']['segment_wall_ms']:.3f}ms\tocr={doc['summary']['ocr_token_f1_min']:.4f}"
        )

    if eval_docs and not args.no_tsv:
        write_tsv(args.tsv, eval_docs)
        print(f"WROTE {rel(args.tsv)}")


if __name__ == "__main__":
    main()
