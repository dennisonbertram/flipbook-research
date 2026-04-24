#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from time import perf_counter

import modal
import numpy as np
from PIL import Image


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (parent / "docs").exists() and (parent / "scripts").exists():
            return parent
    return Path.cwd()


ROOT = _repo_root()
FIXTURE = ROOT / "fixtures" / "track-a" / "text-heavy-page.png"
OUTPUT_ROOT = ROOT / "outputs" / "track-c"
RESULTS_TSV = ROOT / "docs" / "experiments" / "track-c" / "results.tsv"

app = modal.App("flipbook-track-c-canvas")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install("torch", "Pillow", "numpy")
)


def parse_resolution(value: str) -> tuple[int, int]:
    width_s, height_s = value.lower().split("x", 1)
    return int(width_s), int(height_s)


def ensure_fixture() -> None:
    if FIXTURE.exists():
        return
    import sys

    sys.path.insert(0, str(ROOT / "scripts" / "track_a"))
    from fixtures import create_text_heavy_fixture

    create_text_heavy_fixture(FIXTURE)


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
        return result.stdout.strip()
    except Exception:
        return "nogit"


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def token_f1(a: str, b: str) -> float:
    from collections import Counter

    a_tokens = normalize_text(a).split()
    b_tokens = normalize_text(b).split()
    if not a_tokens or not b_tokens:
        return 0.0
    a_counts = Counter(a_tokens)
    b_counts = Counter(b_tokens)
    overlap = sum((a_counts & b_counts).values())
    precision = overlap / len(b_tokens)
    recall = overlap / len(a_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


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


def write_quality(run_dir: Path, metrics: dict) -> dict:
    input_path = run_dir / "input.png"
    render_960 = run_dir / "render-960.png"
    render_512 = run_dir / "render-512.png"
    crop_2x = run_dir / "crop-2x.png"

    input_ocr = ocr(input_path)
    render_ocr = ocr(render_960)
    char_similarity = SequenceMatcher(None, normalize_text(input_ocr), normalize_text(render_ocr)).ratio()
    token_similarity = token_f1(input_ocr, render_ocr)
    text_score = token_similarity
    layout_score = image_similarity(input_path, render_960)

    quality = {
        "run_id": metrics["run_id"],
        "input_ocr": input_ocr,
        "render_960_ocr": render_ocr,
        "ocr_similarity": text_score,
        "ocr_char_similarity": char_similarity,
        "ocr_token_f1": token_similarity,
        "layout_similarity": layout_score,
        "render_512_exists": render_512.exists(),
        "crop_2x_exists": crop_2x.exists(),
        "note": "C0 quality proxy: Tesseract token-F1 plus low-resolution image similarity. Manual review still required.",
    }
    (run_dir / "quality.json").write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
    return quality


def ensure_results_header() -> None:
    RESULTS_TSV.parent.mkdir(parents=True, exist_ok=True)
    if RESULTS_TSV.exists():
        return
    RESULTS_TSV.write_text(
        "\t".join(
            [
                "run_id",
                "commit",
                "canvas_type",
                "compile_ms",
                "render_960_ms",
                "render_33_wall_ms",
                "encode_ms",
                "ocr_similarity",
                "resize_consistency",
                "temporal_consistency",
                "status",
                "description",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def append_results(metrics: dict, quality: dict) -> None:
    ensure_results_header()
    row = [
        metrics["run_id"],
        metrics["commit"],
        metrics["canvas_type"],
        f'{metrics["compile_ms"]:.3f}',
        f'{metrics["render_960_ms"]:.3f}',
        f'{metrics["render_33_wall_ms"]:.3f}',
        f'{metrics["encode_ms"]:.3f}',
        f'{quality["ocr_similarity"]:.4f}',
        f'{metrics["resize_consistency"]:.4f}',
        f'{metrics["temporal_consistency"]:.4f}',
        metrics["status"],
        metrics["description"].replace("\t", " "),
    ]
    with RESULTS_TSV.open("a", encoding="utf-8") as handle:
        handle.write("\t".join(row) + "\n")


@app.function(image=image, gpu="L40S", timeout=1800, startup_timeout=1200)
def train_and_render(input_png: bytes, config: dict) -> dict:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from PIL import Image

    class NeuralCanvas(nn.Module):
        def __init__(self, width: int, height: int, channels: int, hidden: int, freq_bands: int):
            super().__init__()
            self.width = width
            self.height = height
            self.freq_bands = freq_bands
            self.canvas = nn.Parameter(torch.randn(1, channels, height, width) * 0.02)
            coord_dim = 2 + 4 * freq_bands
            self.mlp = nn.Sequential(
                nn.Linear(channels + coord_dim, hidden),
                nn.SiLU(),
                nn.Linear(hidden, hidden),
                nn.SiLU(),
                nn.Linear(hidden, 3),
            )

        def encode_coords(self, coords01: torch.Tensor) -> torch.Tensor:
            feats = [coords01]
            for i in range(self.freq_bands):
                freq = float(2**i) * torch.pi
                feats.append(torch.sin(coords01 * freq))
                feats.append(torch.cos(coords01 * freq))
            return torch.cat(feats, dim=-1)

        def forward(self, coords01: torch.Tensor) -> torch.Tensor:
            grid = coords01.mul(2.0).sub(1.0).view(1, -1, 1, 2)
            sampled = F.grid_sample(
                self.canvas,
                grid,
                mode="bilinear",
                padding_mode="border",
                align_corners=True,
            ).squeeze(0).squeeze(-1).transpose(0, 1)
            rgb = self.mlp(torch.cat([sampled, self.encode_coords(coords01)], dim=-1))
            return torch.sigmoid(rgb)

        @torch.inference_mode()
        def render(self, out_w: int, out_h: int, viewport: tuple[float, float, float, float]) -> torch.Tensor:
            x, y, w, h = viewport
            xs = torch.linspace(x, x + w, out_w, device=self.canvas.device)
            ys = torch.linspace(y, y + h, out_h, device=self.canvas.device)
            yy, xx = torch.meshgrid(ys, xs, indexing="ij")
            coords = torch.stack([xx.reshape(-1), yy.reshape(-1)], dim=-1).clamp(0.0, 1.0)
            parts = []
            chunk = 262144
            for start in range(0, coords.shape[0], chunk):
                parts.append(self.forward(coords[start : start + chunk]))
            img = torch.cat(parts, dim=0).view(out_h, out_w, 3)
            return img

    def tensor_to_png_bytes(tensor: torch.Tensor) -> bytes:
        arr = tensor.detach().clamp(0, 1).mul(255).to(torch.uint8).cpu().numpy()
        image_out = Image.fromarray(arr, "RGB")
        buffer = io.BytesIO()
        image_out.save(buffer, "PNG")
        return buffer.getvalue()

    def encode_mp4(frames: list[torch.Tensor], width: int, height: int, fps: int) -> tuple[bytes, float]:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.mp4"
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
                str(output_path),
            ]
            start = perf_counter()
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            assert proc.stdin is not None
            for frame in frames:
                arr = frame.detach().clamp(0, 1).mul(255).to(torch.uint8).cpu().numpy()
                proc.stdin.write(arr.tobytes())
            proc.stdin.close()
            stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
            return_code = proc.wait()
            encode_ms = (perf_counter() - start) * 1000
            if return_code != 0:
                raise RuntimeError(stderr)
            return output_path.read_bytes(), encode_ms

    device = "cuda"
    torch.backends.cuda.matmul.allow_tf32 = True
    train_w, train_h = parse_resolution(config["train_resolution"])
    steps = int(config["steps"])
    batch_size = int(config["batch_size"])

    source = Image.open(io.BytesIO(input_png)).convert("RGB").resize((train_w, train_h), Image.Resampling.LANCZOS)
    target = torch.from_numpy(np.asarray(source, dtype=np.float32) / 255.0).to(device)

    model = NeuralCanvas(
        width=train_w,
        height=train_h,
        channels=int(config["channels"]),
        hidden=int(config["hidden"]),
        freq_bands=int(config["freq_bands"]),
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=float(config["lr"]), weight_decay=0.0)
    compile_start = perf_counter()
    losses = []
    for step in range(steps):
        idx = torch.randint(0, train_w * train_h, (batch_size,), device=device)
        ys = torch.div(idx, train_w, rounding_mode="floor")
        xs = idx - ys * train_w
        coords = torch.stack(
            [
                xs.float() / max(1, train_w - 1),
                ys.float() / max(1, train_h - 1),
            ],
            dim=-1,
        )
        pred = model(coords)
        truth = target[ys, xs]
        loss = F.mse_loss(pred, truth)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        if step % max(1, steps // 20) == 0 or step == steps - 1:
            losses.append({"step": step, "mse": float(loss.detach().cpu())})
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    compile_ms = (perf_counter() - compile_start) * 1000

    artifacts: dict[str, str] = {}
    render_times: dict[str, float] = {}

    def render_named(name: str, width: int, height: int, viewport: tuple[float, float, float, float]):
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        start = perf_counter()
        img_tensor = model.render(width, height, viewport)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        render_times[name] = (perf_counter() - start) * 1000
        artifacts[name] = base64.b64encode(tensor_to_png_bytes(img_tensor)).decode("ascii")
        return img_tensor

    render_named("render-512.png", 512, 288, (0.0, 0.0, 1.0, 1.0))
    render_960 = render_named("render-960.png", 960, 544, (0.0, 0.0, 1.0, 1.0))
    render_named("crop-2x.png", 960, 544, (0.25, 0.25, 0.5, 0.5))
    render_named("crop-shifted.png", 960, 544, (0.08, 0.08, 0.62, 0.62))

    video_frames = []
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    video_start = perf_counter()
    for _ in range(int(config["frames"])):
        video_frames.append(model.render(960, 544, (0.0, 0.0, 1.0, 1.0)))
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    render_33_wall_ms = (perf_counter() - video_start) * 1000
    video_bytes, encode_ms = encode_mp4(video_frames, 960, 544, int(config["fps"]))
    artifacts["output.mp4"] = base64.b64encode(video_bytes).decode("ascii")

    metrics = {
        "canvas_type": "full-resolution-latent-feature-grid-mlp",
        "train_resolution": config["train_resolution"],
        "steps": steps,
        "batch_size": batch_size,
        "channels": int(config["channels"]),
        "hidden": int(config["hidden"]),
        "freq_bands": int(config["freq_bands"]),
        "lr": float(config["lr"]),
        "compile_ms": compile_ms,
        "final_mse": losses[-1]["mse"],
        "losses": losses,
        "render_times": render_times,
        "render_960_ms": render_times["render-960.png"],
        "render_33_wall_ms": render_33_wall_ms,
        "encode_ms": encode_ms,
        "resize_consistency": 0.0,
        "temporal_consistency": 1.0,
        "description": "C0 overfit neural canvas: trainable full-resolution latent feature grid plus MLP renderer",
    }

    return {
        "artifacts": artifacts,
        "metrics": metrics,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run C0 neural canvas overfit on Modal.")
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--train-resolution", default="960x544")
    parser.add_argument("--batch-size", type=int, default=131072)
    parser.add_argument("--channels", type=int, default=8)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--freq-bands", type=int, default=8)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--frames", type=int, default=33)
    parser.add_argument("--fps", type=int, default=24)
    return parser


@app.local_entrypoint()
def main(
    steps: int = 1500,
    train_resolution: str = "960x544",
    batch_size: int = 131072,
    channels: int = 8,
    hidden: int = 64,
    freq_bands: int = 8,
    lr: float = 0.01,
    frames: int = 33,
    fps: int = 24,
):
    ensure_fixture()
    config = {
        "steps": steps,
        "train_resolution": train_resolution,
        "batch_size": batch_size,
        "channels": channels,
        "hidden": hidden,
        "freq_bands": freq_bands,
        "lr": lr,
        "frames": frames,
        "fps": fps,
    }
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-c0-canvas-{train_resolution}-s{steps}"
    run_dir = OUTPUT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    input_path = run_dir / "input.png"
    input_path.write_bytes(FIXTURE.read_bytes())

    print(f"START {run_id} config={json.dumps(config, sort_keys=True)}", flush=True)
    result = train_and_render.remote(FIXTURE.read_bytes(), config)

    for name, encoded in result["artifacts"].items():
        (run_dir / name).write_bytes(base64.b64decode(encoded))

    metrics = result["metrics"]
    metrics.update(
        {
            "run_id": run_id,
            "commit": git_commit(),
            "track": "C",
            "width": 960,
            "height": 544,
            "frames": frames,
            "fps": fps,
            "artifacts": {
                "input": str(input_path),
                "render_512": str(run_dir / "render-512.png"),
                "render_960": str(run_dir / "render-960.png"),
                "crop_2x": str(run_dir / "crop-2x.png"),
                "crop_shifted": str(run_dir / "crop-shifted.png"),
                "output": str(run_dir / "output.mp4"),
                "metrics": str(run_dir / "metrics.json"),
                "quality": str(run_dir / "quality.json"),
            },
        }
    )

    quality = write_quality(run_dir, metrics)
    metrics["ocr_similarity"] = quality["ocr_similarity"]
    metrics["layout_similarity"] = quality["layout_similarity"]
    metrics["resize_consistency"] = quality["layout_similarity"]
    metrics["status"] = "pass" if metrics["render_33_wall_ms"] + metrics["encode_ms"] <= 1300 else "near_miss"
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    append_results(metrics, quality)

    print(json.dumps(metrics, indent=2), flush=True)
    print(f"DONE {run_id} quality={quality['ocr_similarity']:.4f}", flush=True)
