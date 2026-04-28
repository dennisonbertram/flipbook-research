#!/usr/bin/env python3
from __future__ import annotations

import base64
import io
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import modal
from PIL import Image


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (parent / "docs").exists() and (parent / "scripts").exists():
            return parent
    return Path.cwd()


ROOT = _repo_root()
DEFAULT_INPUT = ROOT / "fixtures" / "track-a" / "text-heavy-page.png"
OUTPUT_ROOT = ROOT / "outputs" / "track-v"
RESULTS_TSV = ROOT / "docs" / "experiments" / "track-v" / "modal-ltx-condition-results.tsv"

app = modal.App("flipbook-track-v-ltx-condition-probe")
hf_cache = modal.Volume.from_name("flipbook-hf-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "torch",
        "torchvision",
        "diffusers>=0.36.0",
        "transformers>=4.57.0",
        "accelerate",
        "sentencepiece",
        "safetensors",
        "Pillow",
        "protobuf",
        "numpy",
    )
)


def _parse_resolution(value: str) -> tuple[int, int]:
    width, height = value.lower().split("x", 1)
    return int(width), int(height)


def _git_commit() -> str:
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


def _fit_image(input_path: Path, output_path: Path, size: tuple[int, int]) -> None:
    width, height = size
    with Image.open(input_path) as source:
        img = source.convert("RGB")
        scale = min(width / img.width, height / img.height)
        resized = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "#fffdf8")
    canvas.paste(resized, ((width - resized.width) // 2, (height - resized.height) // 2))
    canvas.save(output_path, "PNG")


def _ensure_results_header() -> None:
    RESULTS_TSV.parent.mkdir(parents=True, exist_ok=True)
    if RESULTS_TSV.exists():
        return
    RESULTS_TSV.write_text(
        "\t".join(
            [
                "run_id",
                "commit",
                "model_id",
                "resolution",
                "frames",
                "fps",
                "steps",
                "wall_time_ms",
                "model_ms",
                "encode_ms",
                "peak_vram_gb",
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


def _score(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _append_results(metrics: dict[str, Any], quality: dict[str, Any] | None) -> None:
    _ensure_results_header()
    row = [
        metrics["run_id"],
        metrics["commit"],
        metrics["model_id"],
        f'{metrics["width"]}x{metrics["height"]}',
        str(metrics["frames"]),
        str(metrics["fps"]),
        str(metrics["steps"]),
        f'{metrics.get("wall_time_ms", 0.0):.3f}',
        f'{metrics.get("model_ms", 0.0):.3f}',
        f'{metrics.get("encode_ms", 0.0):.3f}',
        _score(metrics.get("peak_vram_gb")),
        _score((quality or {}).get("text_score")),
        _score((quality or {}).get("layout_score")),
        _score((quality or {}).get("motion_score")),
        _score((quality or {}).get("loop_error")),
        metrics["status"],
        metrics["description"].replace("\t", " "),
    ]
    with RESULTS_TSV.open("a", encoding="utf-8") as handle:
        handle.write("\t".join(row) + "\n")


@app.cls(
    image=image,
    gpu="L40S",
    timeout=3600,
    startup_timeout=1800,
    scaledown_window=900,
    volumes={"/root/.cache/huggingface": hf_cache},
)
class LTXConditionRunner:
    @modal.enter()
    def load(self) -> None:
        import torch
        from diffusers import LTXConditionPipeline

        self.torch = torch
        self.pipe = LTXConditionPipeline.from_pretrained(
            "Lightricks/LTX-Video-0.9.7-distilled",
            torch_dtype=torch.bfloat16,
        )
        self.pipe.to("cuda")
        if hasattr(self.pipe, "vae") and hasattr(self.pipe.vae, "enable_tiling"):
            self.pipe.vae.enable_tiling()

    @modal.method()
    def warm(self) -> bool:
        return True

    @modal.method()
    def run(self, input_png: bytes, config: dict[str, Any]) -> dict[str, Any]:
        import torch
        from diffusers.pipelines.ltx.pipeline_ltx_condition import LTXVideoCondition

        width, height = _parse_resolution(config["resolution"])
        frames_count = int(config["frames"])
        fps = int(config["fps"])
        steps = int(config["steps"])

        with Image.open(io.BytesIO(input_png)) as source:
            input_image = source.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)

        conditions = [
            LTXVideoCondition(image=input_image, frame_index=0),
            LTXVideoCondition(image=input_image, frame_index=frames_count - 1),
        ]
        generator = torch.Generator(device="cuda").manual_seed(int(config["seed"]))
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()

        model_start = perf_counter()
        with torch.inference_mode():
            result = self.pipe(
                conditions=conditions,
                prompt=config["prompt"],
                negative_prompt=config["negative_prompt"],
                width=width,
                height=height,
                num_frames=frames_count,
                frame_rate=fps,
                num_inference_steps=steps,
                timesteps=config.get("timesteps"),
                guidance_scale=float(config["guidance_scale"]),
                guidance_rescale=float(config["guidance_rescale"]),
                image_cond_noise_scale=float(config["image_cond_noise_scale"]),
                decode_timestep=float(config["decode_timestep"]),
                decode_noise_scale=float(config["decode_noise_scale"]),
                generator=generator,
                output_type="pil",
            )
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        model_ms = (perf_counter() - model_start) * 1000

        frames = result.frames[0]
        peak_vram_gb = None
        if torch.cuda.is_available():
            peak_vram_gb = torch.cuda.max_memory_allocated() / (1024**3)

        with tempfile.TemporaryDirectory() as tmp:
            output_mp4 = Path(tmp) / "output.mp4"
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
                "ultrafast",
                "-tune",
                "zerolatency",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output_mp4),
            ]
            encode_start = perf_counter()
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            assert proc.stdin is not None
            for frame in frames:
                if frame.size != (width, height):
                    frame = frame.resize((width, height), Image.Resampling.LANCZOS)
                proc.stdin.write(frame.convert("RGB").tobytes())
            proc.stdin.close()
            stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
            return_code = proc.wait()
            encode_ms = (perf_counter() - encode_start) * 1000
            if return_code != 0:
                raise RuntimeError(f"ffmpeg failed: {stderr}")

            preview_buffer = io.BytesIO()
            frames[min(len(frames) // 2, len(frames) - 1)].save(preview_buffer, format="JPEG", quality=90)
            return {
                "video_b64": base64.b64encode(output_mp4.read_bytes()).decode("ascii"),
                "preview_b64": base64.b64encode(preview_buffer.getvalue()).decode("ascii"),
                "metrics": {
                    "model_ms": model_ms,
                    "encode_ms": encode_ms,
                    "peak_vram_gb": peak_vram_gb,
                    "returned_frames": len(frames),
                },
            }


def _default_configs(resolution: str, frames: int, fps: int, steps: int) -> list[dict[str, Any]]:
    locked_prompt = (
        "Locked-off flat document scan. Keep the full page fixed in the exact same camera position. "
        "No zoom, no crop, no page turn, no folding paper, no page curl, no camera motion. "
        "Only extremely subtle ambient lighting shimmer in the paper texture. "
        "Preserve every word, letter, diagram line, layout, typography, and margins exactly."
    )
    return [
        {
            "resolution": resolution,
            "frames": frames,
            "fps": fps,
            "steps": steps,
            "guidance_scale": 1.0,
            "guidance_rescale": 0.0,
            "image_cond_noise_scale": 0.0,
            "decode_timestep": 0.05,
            "decode_noise_scale": 0.025,
            "seed": 0,
            "prompt": locked_prompt,
            "negative_prompt": "text distortion, warped letters, layout drift, jitter, melting, blurry, page turn, paper fold, camera movement",
            "timesteps": [1000, 993, 987, 981, 975, 909, 725, 0.03],
        }
    ]


@app.local_entrypoint()
def main(
    input_path: str = str(DEFAULT_INPUT),
    resolution: str = "768x448",
    frames: int = 49,
    fps: int = 24,
    steps: int = 8,
    max_runs: int = 1,
    config_json: str = "",
) -> None:
    from scripts.track_v.fal_video_benchmark import evaluate_video, probe_video

    input_source = Path(input_path)
    if not input_source.exists():
        raise SystemExit(f"input does not exist: {input_source}")

    width, height = _parse_resolution(resolution)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        prepared_path = Path(tmp.name)
    _fit_image(input_source, prepared_path, (width, height))
    input_png = prepared_path.read_bytes()
    configs = json.loads(config_json) if config_json else _default_configs(resolution, frames, fps, steps)
    commit = _git_commit()
    runner = LTXConditionRunner()
    print("Warming Modal LTX condition runner.", flush=True)
    runner.warm.remote()
    print("Modal runner warm.", flush=True)

    completed = 0
    for config in configs:
        if max_runs and completed >= max_runs:
            break
        config = dict(config)
        width, height = _parse_resolution(config["resolution"])
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{stamp}-modal-ltx-condition-anchor-s{config['steps']}-seed{config['seed']}-{width}x{height}"
        run_dir = OUTPUT_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        local_input = run_dir / "input.png"
        local_output = run_dir / "output.mp4"
        local_preview = run_dir / "preview.jpg"
        local_metrics = run_dir / "metrics.json"
        local_input.write_bytes(input_png)

        wall_start = perf_counter()
        print(f"START {run_id} config={json.dumps(config, sort_keys=True)}", flush=True)
        quality = None
        try:
            result = runner.run.remote(input_png, config)
            wall_time_ms = (perf_counter() - wall_start) * 1000
            local_output.write_bytes(base64.b64decode(result["video_b64"]))
            local_preview.write_bytes(base64.b64decode(result["preview_b64"]))
            probe = probe_video(local_output)
            quality = evaluate_video(local_input, local_output, run_dir, probe)
            text_ok = quality["text_score"] >= 0.70
            layout_ok = quality["layout_score"] >= 0.80
            status = "pass" if text_ok and layout_ok else "quality_fail"
            remote_metrics = result["metrics"]
            metrics = {
                "run_id": run_id,
                "commit": commit,
                "track": "V",
                "recipe": "modal_ltx_condition_first_last_anchor",
                "model_id": "Lightricks/LTX-Video-0.9.7-distilled",
                "width": width,
                "height": height,
                "frames": config["frames"],
                "fps": config["fps"],
                "steps": config["steps"],
                "wall_time_ms": wall_time_ms,
                "model_ms": remote_metrics["model_ms"],
                "encode_ms": remote_metrics["encode_ms"],
                "peak_vram_gb": remote_metrics["peak_vram_gb"],
                "status": status,
                "description": "Modal Diffusers LTXConditionPipeline with source image at first and last frame",
                "config": config,
                "quality": quality,
                "artifacts": {
                    "input": str(local_input),
                    "output": str(local_output),
                    "preview": str(local_preview),
                    "quality": str(run_dir / "quality.json"),
                    "metrics": str(local_metrics),
                },
            }
        except Exception as exc:
            wall_time_ms = (perf_counter() - wall_start) * 1000
            metrics = {
                "run_id": run_id,
                "commit": commit,
                "track": "V",
                "recipe": "modal_ltx_condition_first_last_anchor",
                "model_id": "Lightricks/LTX-Video-0.9.7-distilled",
                "width": width,
                "height": height,
                "frames": config["frames"],
                "fps": config["fps"],
                "steps": config["steps"],
                "wall_time_ms": wall_time_ms,
                "model_ms": 0.0,
                "encode_ms": 0.0,
                "peak_vram_gb": None,
                "status": "crash",
                "description": f"Modal LTX condition crash: {exc}",
                "config": config,
                "error": repr(exc),
                "artifacts": {
                    "input": str(local_input),
                    "output": str(local_output),
                    "preview": str(local_preview),
                    "metrics": str(local_metrics),
                },
            }

        local_metrics.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        _append_results(metrics, quality)
        completed += 1
        print(
            f"DONE {run_id} status={metrics['status']} wall_ms={metrics['wall_time_ms']:.1f} "
            f"model_ms={metrics['model_ms']:.1f} encode_ms={metrics['encode_ms']:.1f}",
            flush=True,
        )
