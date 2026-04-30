#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import requests
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.track_v.fal_video_benchmark import (  # noqa: E402
    DEFAULT_INPUT,
    OUTPUT_ROOT,
    append_results,
    evaluate_video,
    fit_image,
    git_commit,
    parse_resolution,
    probe_video,
)


ENDPOINT = "https://api.ltx.video/v1/image-to-video"
KEY_ENV_NAMES = ("LTXV_API_KEY", "LTX_API_KEY")
MAX_DATA_URI_BYTES = 7 * 1024 * 1024


def utc_run_id(model: str, label: str, width: int, height: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_slug = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
    label_slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "run"
    return f"{stamp}-ltx-api-{model_slug}-{label_slug}-{width}x{height}"


def api_key() -> str | None:
    for name in KEY_ENV_NAMES:
        value = os.environ.get(name)
        if value:
            return value
    return None


def image_data_uri(path: Path, quality: int) -> tuple[str, dict[str, Any]]:
    with Image.open(path) as source:
        image = source.convert("RGB")

    attempted: list[dict[str, int]] = []
    for candidate_quality in [quality, 90, 85, 80, 75, 70, 65, 60]:
        if attempted and attempted[-1]["quality"] == candidate_quality:
            continue
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=candidate_quality, optimize=True)
        raw = buffer.getvalue()
        encoded = base64.b64encode(raw)
        attempted.append({"quality": candidate_quality, "jpeg_bytes": len(raw), "encoded_bytes": len(encoded)})
        if len(encoded) <= MAX_DATA_URI_BYTES:
            return (
                "data:image/jpeg;base64," + encoded.decode("ascii"),
                {
                    "mime_type": "image/jpeg",
                    "quality": candidate_quality,
                    "jpeg_bytes": len(raw),
                    "encoded_bytes": len(encoded),
                    "attempted": attempted,
                },
            )

    raise RuntimeError(
        "Prepared image is too large for LTX data URI input after JPEG compression. "
        "Use a smaller --prep-resolution or implement the LTX /v1/upload path."
    )


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload)
    for key in ("image_uri", "last_frame_uri"):
        if key in redacted:
            redacted[key] = "<data-uri-redacted>"
    return redacted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark the official LTX image-to-video API for Flipbook page animation.")
    parser.add_argument("--model", default="ltx-2-3-fast", choices=["ltx-2-fast", "ltx-2-pro", "ltx-2-3-fast", "ltx-2-3-pro"])
    parser.add_argument("--label", default="page-i2v")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--last-frame", type=Path, default=None)
    parser.add_argument("--prep-resolution", type=parse_resolution, default=(1920, 1080))
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--append-results", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Prepare input and payload artifacts without calling LTX.")
    parser.add_argument(
        "--prompt",
        default="Subtle continuous camera motion and gentle parallax. Preserve every word, diagram line, page layout, and typography exactly.",
    )
    parser.add_argument("--duration", type=int, default=6, help="Requested video duration in seconds.")
    parser.add_argument("--resolution", default="1920x1080", help="Official LTX output resolution, e.g. 1920x1080.")
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--camera-motion", default="", help="Optional LTX camera_motion value.")
    parser.add_argument("--generate-audio", action="store_true")
    parser.add_argument("--data-uri-quality", type=int, default=90)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--min-text-score", type=float, default=0.70)
    parser.add_argument("--min-layout-score", type=float, default=0.80)
    parser.add_argument("--skip-text-gate", action="store_true", help="Use only layout/motion proxies for illustration-heavy inputs.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.input.exists():
        raise SystemExit(f"Input image does not exist: {args.input}")
    if args.last_frame is not None and not args.last_frame.exists():
        raise SystemExit(f"Last-frame image does not exist: {args.last_frame}")
    key = api_key()
    if not key and not args.dry_run:
        raise SystemExit("LTXV_API_KEY or LTX_API_KEY is not set in the environment.")

    width, height = args.prep_resolution
    run_id = utc_run_id(args.model, args.label, width, height)
    run_dir = args.output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    prepared_input = run_dir / "input.png"
    fit_image(args.input, prepared_input, (width, height))
    image_uri, image_encoding = image_data_uri(prepared_input, args.data_uri_quality)

    payload: dict[str, Any] = {
        "image_uri": image_uri,
        "prompt": args.prompt,
        "model": args.model,
        "duration": args.duration,
        "resolution": args.resolution,
        "fps": args.fps,
        "generate_audio": args.generate_audio,
    }
    if args.camera_motion:
        payload["camera_motion"] = args.camera_motion
    last_frame_encoding = None
    if args.last_frame is not None:
        prepared_last = run_dir / "last-frame.png"
        fit_image(args.last_frame, prepared_last, (width, height))
        last_frame_uri, last_frame_encoding = image_data_uri(prepared_last, args.data_uri_quality)
        payload["last_frame_uri"] = last_frame_uri

    payload_path = run_dir / "payload-redacted.json"
    payload_path.write_text(json.dumps(redact_payload(payload), indent=2) + "\n", encoding="utf-8")

    if args.dry_run:
        metrics = {
            "run_id": run_id,
            "commit": git_commit(),
            "model": f"ltx-api-{args.model}",
            "endpoint": ENDPOINT,
            "input_source": str(args.input),
            "input_resolution": f"{width}x{height}",
            "requested_frames": f"{args.duration}s@{args.fps}fps",
            "status": "dry_run",
            "description": "official LTX API dry run",
            "image_encoding": image_encoding,
            "last_frame_encoding": last_frame_encoding,
            "artifacts": {"input": str(prepared_input), "payload": str(payload_path)},
        }
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"run_id": run_id, "status": "dry_run", "payload": str(payload_path)}, indent=2))
        return 0

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "video/mp4",
    }
    print(f"[{run_id}] submitting {ENDPOINT}", flush=True)
    start = perf_counter()
    response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=args.timeout)
    api_wall_ms = (perf_counter() - start) * 1000
    print(f"[{run_id}] response received in {api_wall_ms:.1f}ms status={response.status_code}", flush=True)

    if response.status_code >= 400:
        error_path = run_dir / "error.json"
        error_path.write_text(
            json.dumps(
                {
                    "status_code": response.status_code,
                    "headers": {key: value for key, value in response.headers.items() if key.lower() != "authorization"},
                    "body_preview": response.text[:4000],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise SystemExit(f"LTX API request failed with HTTP {response.status_code}; see {error_path}")

    write_start = perf_counter()
    output_mp4 = run_dir / "output.mp4"
    output_mp4.write_bytes(response.content)
    write_ms = (perf_counter() - write_start) * 1000

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
        "model": f"ltx-api-{args.model}",
        "endpoint": ENDPOINT,
        "input_source": str(args.input),
        "input_resolution": f"{width}x{height}",
        "requested_frames": f"{args.duration}s@{args.fps}fps",
        "output_frames": output_frames,
        "duration_s": duration_s,
        "api_wall_ms": api_wall_ms,
        "download_ms": write_ms,
        "status": status,
        "description": f"official LTX API image-to-video benchmark model={args.model}",
        "gates": {
            "skip_text_gate": args.skip_text_gate,
            "min_text_score": args.min_text_score,
            "min_layout_score": args.min_layout_score,
            "text_ok": text_ok,
            "layout_ok": layout_ok,
        },
        "arguments": redact_payload(payload),
        "image_encoding": image_encoding,
        "last_frame_encoding": last_frame_encoding,
        "video_probe": probe,
        "response_headers": {key: value for key, value in response.headers.items() if key.lower() != "authorization"},
        "artifacts": {
            "input": str(prepared_input),
            "output": str(output_mp4),
            "contact_sheet": str(run_dir / "contact-sheet.jpg"),
            "quality": str(run_dir / "quality.json"),
            "payload": str(payload_path),
        },
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    if args.append_results:
        append_results(metrics, quality)
    print(json.dumps({"run_id": run_id, "status": status, "api_wall_ms": api_wall_ms, "output": str(output_mp4)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
