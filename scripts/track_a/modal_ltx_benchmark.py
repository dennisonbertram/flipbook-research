#!/usr/bin/env python3
from __future__ import annotations

import base64
import io
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

import modal


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (parent / "docs").exists() and (parent / "scripts").exists():
            return parent
    return Path.cwd()


ROOT = _repo_root()
DEFAULT_FIXTURE = ROOT / "fixtures" / "track-a" / "text-heavy-page.png"
RESULTS_TSV = ROOT / "docs" / "experiments" / "track-a" / "results.tsv"
OUTPUT_ROOT = ROOT / "outputs" / "track-a"

app = modal.App("flipbook-track-a-ltx")
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
    )
)


def _default_configs() -> list[dict]:
    configs = []
    # One-step runs currently crash in the Diffusers FlowMatch scheduler for
    # this pipeline, so the overnight loop starts at two denoising steps.
    for resolution in ["768x448", "896x512", "960x544", "1024x576", "1280x736"]:
        for steps in [2, 3, 4, 6, 8]:
            configs.append(
                {
                    "resolution": resolution,
                    "frames": 33,
                    "fps": 24,
                    "steps": steps,
                    "guidance_scale": 1.0,
                    "seed": 0,
                    "model_id": "Lightricks/LTX-Video",
                    "prompt": "subtle continuous loop, gentle parallax, small ambient motion, preserve text and diagram layout",
                    "negative_prompt": "text distortion, warped letters, layout drift, jitter, melting, blurry",
                }
            )
    return configs


def _parse_resolution(value: str) -> tuple[int, int]:
    width, height = value.lower().split("x", 1)
    return int(width), int(height)


def _next_local_deadline(hhmm: str) -> datetime:
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    hour, minute = [int(part) for part in hhmm.split(":", 1)]
    deadline = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if deadline <= now:
        deadline += timedelta(days=1)
    return deadline


def _ensure_default_fixture() -> None:
    if DEFAULT_FIXTURE.exists():
        return
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fixtures import create_text_heavy_fixture

    create_text_heavy_fixture(DEFAULT_FIXTURE)


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


def _ensure_results_header() -> None:
    RESULTS_TSV.parent.mkdir(parents=True, exist_ok=True)
    if RESULTS_TSV.exists():
        return
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
    RESULTS_TSV.write_text("\t".join(header) + "\n", encoding="utf-8")


def _score(value) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _append_results(metrics: dict) -> None:
    _ensure_results_header()
    row = [
        metrics["run_id"],
        metrics["commit"],
        f'{metrics["width"]}x{metrics["height"]}',
        f'{metrics.get("wall_time_ms", 0.0):.3f}',
        f'{metrics.get("model_ms", 0.0):.3f}',
        f'{metrics.get("decode_ms", 0.0):.3f}',
        f'{metrics.get("encode_ms", 0.0):.3f}',
        _score(metrics.get("peak_vram_gb")),
        _score(metrics.get("text_score")),
        _score(metrics.get("layout_score")),
        _score(metrics.get("motion_score")),
        _score(metrics.get("loop_error")),
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
class LTXRunner:
    @modal.enter()
    def load(self):
        import torch
        from diffusers import LTXImageToVideoPipeline

        self.torch = torch
        self.pipe = LTXImageToVideoPipeline.from_pretrained(
            "Lightricks/LTX-Video",
            torch_dtype=torch.bfloat16,
        )
        self.pipe.to("cuda")
        if hasattr(self.pipe, "vae") and hasattr(self.pipe.vae, "enable_tiling"):
            self.pipe.vae.enable_tiling()

    @modal.method()
    def warm(self) -> bool:
        return True

    @modal.method()
    def run(self, input_png: bytes, config: dict) -> dict:
        import os
        import tempfile
        from PIL import Image

        torch = self.torch
        width, height = _parse_resolution(config["resolution"])
        fps = int(config["fps"])
        frames_count = int(config["frames"])

        with Image.open(io.BytesIO(input_png)) as source:
            input_image = source.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)

        generator = torch.Generator(device="cuda").manual_seed(int(config["seed"]))
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()

        model_start = perf_counter()
        with torch.inference_mode():
            result = self.pipe(
                image=input_image,
                prompt=config["prompt"],
                negative_prompt=config["negative_prompt"],
                width=width,
                height=height,
                num_frames=frames_count,
                num_inference_steps=int(config["steps"]),
                guidance_scale=float(config["guidance_scale"]),
                generator=generator,
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
                    "denoise_ms": model_ms,
                    "decode_ms": 0.0,
                    "encode_ms": encode_ms,
                    "peak_vram_gb": peak_vram_gb,
                    "returned_frames": len(frames),
                },
            }


@app.local_entrypoint()
def main(until: str = "08:00", max_runs: int = 0, config_json: str = ""):
    _ensure_default_fixture()
    input_png = DEFAULT_FIXTURE.read_bytes()
    configs = json.loads(config_json) if config_json else _default_configs()
    deadline = _next_local_deadline(until)
    commit = _git_commit()
    runner = LTXRunner()

    print(f"Track A Modal loop deadline: {deadline.isoformat()}")
    print(f"Config count per cycle: {len(configs)}")
    print("Warming Modal container before measured runs.", flush=True)
    runner.warm.remote()
    print("Modal container warm.", flush=True)

    completed = 0
    cycle = 0
    while datetime.now(deadline.tzinfo) < deadline:
        cycle += 1
        for base_config in configs:
            if datetime.now(deadline.tzinfo) >= deadline:
                break
            if max_runs and completed >= max_runs:
                print(f"Reached max_runs={max_runs}")
                return

            config = dict(base_config)
            config["seed"] = int(base_config.get("seed", 0)) + cycle - 1
            width, height = _parse_resolution(config["resolution"])
            stamp = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
            run_id = f"{stamp}-modal-ltx-s{config['steps']}-seed{config['seed']}-{width}x{height}"
            output_dir = OUTPUT_ROOT / run_id
            output_dir.mkdir(parents=True, exist_ok=False)
            local_input = output_dir / "input.png"
            local_video = output_dir / "output.mp4"
            local_preview = output_dir / "preview.jpg"
            local_metrics = output_dir / "metrics.json"
            local_input.write_bytes(input_png)

            wall_start = perf_counter()
            print(f"START {run_id} cycle={cycle} config={json.dumps(config, sort_keys=True)}", flush=True)
            try:
                result = runner.run.remote(input_png, config)
                wall_time_ms = (perf_counter() - wall_start) * 1000
                local_video.write_bytes(base64.b64decode(result["video_b64"]))
                local_preview.write_bytes(base64.b64decode(result["preview_b64"]))
                remote_metrics = result["metrics"]
                status = "pass" if wall_time_ms <= 1300 else "near_miss" if wall_time_ms <= 3000 else "fail"
                metrics = {
                    "run_id": run_id,
                    "commit": commit,
                    "track": "A",
                    "recipe": "modal_ltx_diffusers_i2v",
                    "width": width,
                    "height": height,
                    "frames": config["frames"],
                    "fps": config["fps"],
                    "steps": config["steps"],
                    "guidance_scale": config["guidance_scale"],
                    "model_id": config["model_id"],
                    "wall_time_ms": wall_time_ms,
                    "model_ms": remote_metrics["model_ms"],
                    "denoise_ms": remote_metrics["denoise_ms"],
                    "decode_ms": remote_metrics["decode_ms"],
                    "decode_or_composite_ms": remote_metrics["decode_ms"],
                    "encode_ms": remote_metrics["encode_ms"],
                    "effective_generated_fps": config["frames"] / (wall_time_ms / 1000),
                    "peak_vram_gb": remote_metrics["peak_vram_gb"],
                    "text_score": None,
                    "layout_score": None,
                    "motion_score": None,
                    "loop_error": None,
                    "status": status,
                    "description": f"Modal LTX I2V steps={config['steps']} guidance={config['guidance_scale']}",
                    "artifacts": {
                        "input": str(local_input),
                        "output": str(local_video),
                        "preview": str(local_preview),
                        "metrics": str(local_metrics),
                    },
                    "config": config,
                    "remote_metrics": remote_metrics,
                }
            except Exception as exc:
                wall_time_ms = (perf_counter() - wall_start) * 1000
                metrics = {
                    "run_id": run_id,
                    "commit": commit,
                    "track": "A",
                    "recipe": "modal_ltx_diffusers_i2v",
                    "width": width,
                    "height": height,
                    "frames": config["frames"],
                    "fps": config["fps"],
                    "steps": config["steps"],
                    "guidance_scale": config["guidance_scale"],
                    "model_id": config["model_id"],
                    "wall_time_ms": wall_time_ms,
                    "model_ms": 0.0,
                    "denoise_ms": 0.0,
                    "decode_ms": 0.0,
                    "decode_or_composite_ms": 0.0,
                    "encode_ms": 0.0,
                    "effective_generated_fps": 0.0,
                    "peak_vram_gb": None,
                    "text_score": None,
                    "layout_score": None,
                    "motion_score": None,
                    "loop_error": None,
                    "status": "crash",
                    "description": f"Modal LTX crash: {exc}",
                    "artifacts": {
                        "input": str(local_input),
                        "output": str(local_video),
                        "preview": str(local_preview),
                        "metrics": str(local_metrics),
                    },
                    "config": config,
                    "error": repr(exc),
                }

            local_metrics.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
            _append_results(metrics)
            completed += 1
            print(
                f"DONE {run_id} status={metrics['status']} wall_ms={metrics['wall_time_ms']:.1f} "
                f"model_ms={metrics['model_ms']:.1f} encode_ms={metrics['encode_ms']:.1f}",
                flush=True,
            )

    print(f"Deadline reached after {completed} completed runs.")
