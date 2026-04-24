#!/usr/bin/env python3
from __future__ import annotations

import base64
import io
import json
import os
import re
import subprocess
import tempfile
from collections import Counter
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

app = modal.App("flipbook-track-c-canvas-c2-lite")

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
    override = os.environ.get("FLIPBOOK_COMMIT")
    if override:
        return override
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


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def token_f1(a: str, b: str) -> float:
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


def detect_text_boxes(path: Path, min_conf: float, min_chars: int = 1) -> list[dict]:
    result = subprocess.run(
        ["tesseract", str(path), "stdout", "--psm", "6", "--oem", "1", "tsv"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    boxes = []
    lines = result.stdout.splitlines()
    if not lines:
        return boxes
    header = lines[0].split("\t")
    for line in lines[1:]:
        values = line.split("\t")
        if len(values) != len(header):
            continue
        row = dict(zip(header, values))
        text = row.get("text", "").strip()
        normalized = normalize_text(text)
        if len(normalized) < min_chars:
            continue
        try:
            conf = float(row.get("conf", "-1"))
            left = int(row["left"])
            top = int(row["top"])
            width = int(row["width"])
            height = int(row["height"])
        except (KeyError, ValueError):
            continue
        if conf < min_conf or width <= 0 or height <= 0:
            continue
        boxes.append(
            {
                "x": left,
                "y": top,
                "w": width,
                "h": height,
                "conf": conf,
                "text": text,
            }
        )
    return boxes


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


def write_quality(run_dir: Path, metrics: dict) -> dict:
    input_path = run_dir / "input.png"
    render_960 = run_dir / "render-960.png"
    render_mid = run_dir / "render-element-mid.png"
    if not render_mid.exists():
        render_mid = run_dir / "render-layout-mid.png"
    if not render_mid.exists():
        render_mid = run_dir / "render-viewport-mid.png"
    if not render_mid.exists():
        render_mid = run_dir / "render-mid.png"
    render_last = run_dir / "render-last.png"

    input_ocr = ocr(input_path)
    render_ocr = ocr(render_mid)
    char_similarity = SequenceMatcher(None, normalize_text(input_ocr), normalize_text(render_ocr)).ratio()
    token_similarity = token_f1(input_ocr, render_ocr)
    layout_score = image_similarity(input_path, render_960)
    motion_delta = frame_diff(render_960, render_mid)
    loop_error = frame_diff(render_960, render_last)

    quality = {
        "run_id": metrics["run_id"],
        "input_ocr": input_ocr,
        "render_mid_ocr": render_ocr,
        "ocr_similarity": token_similarity,
        "ocr_char_similarity": char_similarity,
        "layout_similarity": layout_score,
        "motion_delta": motion_delta,
        "loop_error": loop_error,
        "note": "C2-lite quality proxy: OCR token-F1 on mid-frame, layout similarity on first frame, and low-res frame-diff motion/loop metrics.",
    }
    (run_dir / "quality.json").write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
    return quality


@app.function(image=image, gpu="L40S", timeout=1800, startup_timeout=1200)
def train_and_render_motion(input_png: bytes, config: dict) -> dict:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from PIL import Image

    class TimeCanvas(nn.Module):
        def __init__(self, width: int, height: int, channels: int, hidden: int, freq_bands: int, time_bands: int, flow_scale: float):
            super().__init__()
            self.width = width
            self.height = height
            self.freq_bands = freq_bands
            self.time_bands = time_bands
            self.flow_scale = flow_scale
            self.canvas = nn.Parameter(torch.randn(1, channels, height, width) * 0.02)
            coord_dim = 2 + 4 * freq_bands
            time_dim = 1 + 2 * time_bands
            self.flow = nn.Sequential(
                nn.Linear(coord_dim + time_dim, hidden),
                nn.SiLU(),
                nn.Linear(hidden, hidden),
                nn.SiLU(),
                nn.Linear(hidden, 2),
                nn.Tanh(),
            )
            self.mlp = nn.Sequential(
                nn.Linear(channels + coord_dim + time_dim, hidden),
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

        def encode_time(self, t: torch.Tensor) -> torch.Tensor:
            feats = [t]
            for i in range(self.time_bands):
                freq = float(2**i) * 2.0 * torch.pi
                feats.append(torch.sin(t * freq))
                feats.append(torch.cos(t * freq))
            return torch.cat(feats, dim=-1)

        def forward(self, coords01: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
            coord_enc = self.encode_coords(coords01)
            time_enc = self.encode_time(t)
            flow = self.flow(torch.cat([coord_enc, time_enc], dim=-1)) * self.flow_scale
            sample_coords = (coords01 + flow).clamp(0.0, 1.0)
            grid = sample_coords.mul(2.0).sub(1.0).view(1, -1, 1, 2)
            sampled = F.grid_sample(
                self.canvas,
                grid,
                mode="bilinear",
                padding_mode="border",
                align_corners=True,
            ).squeeze(0).squeeze(-1).transpose(0, 1)
            rgb = self.mlp(torch.cat([sampled, coord_enc, time_enc], dim=-1))
            return torch.sigmoid(rgb)

        @torch.inference_mode()
        def render(self, out_w: int, out_h: int, viewport: tuple[float, float, float, float], t_value: float) -> torch.Tensor:
            x, y, w, h = viewport
            xs = torch.linspace(x, x + w, out_w, device=self.canvas.device)
            ys = torch.linspace(y, y + h, out_h, device=self.canvas.device)
            yy, xx = torch.meshgrid(ys, xs, indexing="ij")
            coords = torch.stack([xx.reshape(-1), yy.reshape(-1)], dim=-1).clamp(0.0, 1.0)
            t = torch.full((coords.shape[0], 1), t_value, device=self.canvas.device)
            parts = []
            chunk = 262144
            for start in range(0, coords.shape[0], chunk):
                parts.append(self.forward(coords[start : start + chunk], t[start : start + chunk]))
            return torch.cat(parts, dim=0).view(out_h, out_w, 3)

    def target_coords_for_motion(coords: torch.Tensor, t: torch.Tensor, amp: float, mode: str) -> torch.Tensor:
        phase = t * 2.0 * torch.pi
        x = coords[:, 0:1]
        y = coords[:, 1:2]
        if mode in {"static", "identity", "none"}:
            return coords
        if mode == "frame-scale":
            envelope = torch.sin(t * torch.pi).square()
            scale_x = 1.0 - amp * envelope
            scale_y = 1.0 - amp * 0.72 * envelope
            pan_x = amp * 0.22 * torch.sin(phase) * envelope
            pan_y = amp * 0.12 * torch.cos(phase) * envelope
            moved_x = 0.5 + (x - 0.5) * scale_x + pan_x
            moved_y = 0.5 + (y - 0.5) * scale_y + pan_y
            return torch.cat([moved_x, moved_y], dim=-1)
        if mode == "responsive-squeeze":
            envelope = torch.sin(t * torch.pi).square()
            body = torch.sigmoid((y - 0.22) * 26.0)
            right_column = torch.sigmoid((x - 0.52) * 28.0) * body * torch.sigmoid((0.50 - y) * 18.0)
            diagram = torch.sigmoid((y - 0.42) * 26.0)
            dx = -amp * 0.70 * envelope * (x - 0.5) * body
            dx += amp * 0.12 * envelope * torch.sin(y * 2.0 * torch.pi)
            dy = amp * 0.68 * envelope * right_column
            dy += amp * 0.18 * envelope * diagram
            dy -= amp * 0.08 * envelope * body
            return coords + torch.cat([dx, dy], dim=-1)

        dx = amp * torch.sin(phase) * (0.65 + 0.35 * y)
        dy = amp * 0.55 * torch.cos(phase) * (0.45 + 0.55 * x)
        dx += amp * 0.18 * torch.sin(phase * 2.0 + y * 8.0)
        dy += amp * 0.12 * torch.cos(phase * 2.0 + x * 8.0)
        return coords + torch.cat([dx, dy], dim=-1)

    def sample_target(target_chw: torch.Tensor, coords01: torch.Tensor) -> torch.Tensor:
        grid = coords01.clamp(0.0, 1.0).mul(2.0).sub(1.0).view(1, -1, 1, 2)
        sampled = F.grid_sample(target_chw, grid, mode="bilinear", padding_mode="border", align_corners=True)
        return sampled.squeeze(0).squeeze(-1).transpose(0, 1)

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
    flow_scale = float(config["flow_scale"])
    motion_mode = str(config.get("motion_mode", "jiggle"))
    motion_strength = float(config.get("motion_strength", flow_scale))
    video_viewport_mode = str(config.get("video_viewport_mode", "static"))
    viewport_zoom = float(config.get("viewport_zoom", 0.0))
    viewport_pan = float(config.get("viewport_pan", 0.0))
    video_layout_mode = str(config.get("video_layout_mode", "none"))
    layout_transform_strength = float(config.get("layout_transform_strength", 0.0))
    layout_transform_pan = float(config.get("layout_transform_pan", 0.0))
    element_scale_ratio = float(config.get("element_scale_ratio", 0.25))
    element_anchor_padding = int(config.get("element_anchor_padding", 3))
    element_mask_mode = str(config.get("element_mask_mode", "rectangle"))
    element_anchor_mode = str(config.get("element_anchor_mode", "line"))
    edge_sample_ratio = float(config.get("edge_sample_ratio", 0.0))
    edge_loss_weight = float(config.get("edge_loss_weight", 0.0))
    text_box_sample_ratio = float(config.get("text_box_sample_ratio", 0.0))
    text_box_loss_weight = float(config.get("text_box_loss_weight", 0.0))
    text_box_padding = int(config.get("text_box_padding", 0))

    source = Image.open(io.BytesIO(input_png)).convert("RGB").resize((train_w, train_h), Image.Resampling.LANCZOS)
    target = torch.from_numpy(np.asarray(source, dtype=np.float32) / 255.0).to(device)
    target_chw = target.permute(2, 0, 1).unsqueeze(0)
    luminance = target.mean(dim=-1)
    gray = luminance.unsqueeze(0).unsqueeze(0)
    sobel_x = torch.tensor(
        [[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]],
        device=device,
    ).view(1, 1, 3, 3)
    sobel_y = torch.tensor(
        [[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]],
        device=device,
    ).view(1, 1, 3, 3)
    edge = torch.sqrt(F.conv2d(gray, sobel_x, padding=1).square() + F.conv2d(gray, sobel_y, padding=1).square())
    edge = edge.squeeze(0).squeeze(0)
    edge = edge / edge.max().clamp_min(1e-6)
    dark = (1.0 - luminance).clamp(0.0, 1.0)
    glyph_score = (0.10 + edge + 0.75 * edge * dark + 0.25 * dark).clamp_min(1e-6)
    glyph_prob = glyph_score.flatten()
    glyph_prob = glyph_prob / glyph_prob.sum().clamp_min(1e-6)
    glyph_weight_chw = (glyph_score / glyph_score.max().clamp_min(1e-6)).unsqueeze(0).unsqueeze(0)
    text_mask = torch.zeros((train_h, train_w), device=device)
    source_w, source_h = config.get("source_resolution", [train_w, train_h])
    scale_x = train_w / max(1, int(source_w))
    scale_y = train_h / max(1, int(source_h))
    scaled_text_boxes = []
    for box in config.get("text_boxes", []):
        x0 = max(0, int(round(float(box["x"]) * scale_x)) - text_box_padding)
        y0 = max(0, int(round(float(box["y"]) * scale_y)) - text_box_padding)
        x1 = min(train_w, int(round((float(box["x"]) + float(box["w"])) * scale_x)) + text_box_padding)
        y1 = min(train_h, int(round((float(box["y"]) + float(box["h"])) * scale_y)) + text_box_padding)
        if x1 > x0 and y1 > y0:
            text_mask[y0:y1, x0:x1] = 1.0
            scaled_text_boxes.append((x0, y0, x1, y1))
    text_score = (text_mask * (0.20 + edge + 0.25 * dark)).clamp_min(0.0)
    text_prob = text_score.flatten()
    text_prob_sum = text_prob.sum()
    text_has_pixels = text_prob_sum.detach().cpu().item() > 0
    if text_has_pixels:
        text_prob = text_prob / text_prob_sum.clamp_min(1e-6)
    text_weight_chw = text_score.clamp(0.0, 1.0).unsqueeze(0).unsqueeze(0)
    element_alpha = (text_mask * (0.55 * edge * dark + 0.35 * dark + 0.25 * edge)).clamp(0.0, 1.0)
    element_alpha = element_alpha / element_alpha.max().clamp_min(1e-6)
    element_alpha = F.max_pool2d(element_alpha.unsqueeze(0).unsqueeze(0), kernel_size=3, stride=1, padding=1)
    element_alpha = F.avg_pool2d(element_alpha, kernel_size=3, stride=1, padding=1).squeeze(0).squeeze(0).clamp(0.0, 1.0)
    element_alpha_chw = element_alpha.unsqueeze(0).unsqueeze(0)

    def build_line_boxes(boxes: list[tuple[int, int, int, int]]) -> list[tuple[float, float, float, float]]:
        if not boxes:
            return []
        heights = [max(1, y1 - y0) for _, y0, _, y1 in boxes]
        median_h = float(np.median(np.asarray(heights, dtype=np.float32)))
        y_threshold = max(8.0, median_h * 0.75)
        groups: list[dict] = []
        for x0, y0, x1, y1 in sorted(boxes, key=lambda item: ((item[1] + item[3]) * 0.5, item[0])):
            cy = (y0 + y1) * 0.5
            match = None
            for group in groups:
                if abs(cy - group["cy"]) <= y_threshold:
                    match = group
                    break
            if match is None:
                groups.append({"cy": cy, "boxes": [(x0, y0, x1, y1)]})
            else:
                match["boxes"].append((x0, y0, x1, y1))
                match["cy"] = sum((b[1] + b[3]) * 0.5 for b in match["boxes"]) / len(match["boxes"])

        line_boxes = []
        for group in groups:
            x0 = max(0, min(box[0] for box in group["boxes"]) - element_anchor_padding)
            y0 = max(0, min(box[1] for box in group["boxes"]) - element_anchor_padding)
            x1 = min(train_w, max(box[2] for box in group["boxes"]) + element_anchor_padding)
            y1 = min(train_h, max(box[3] for box in group["boxes"]) + element_anchor_padding)
            if x1 > x0 and y1 > y0:
                line_boxes.append((x0 / train_w, y0 / train_h, x1 / train_w, y1 / train_h))
        return line_boxes

    def build_word_boxes(boxes: list[tuple[int, int, int, int]]) -> list[tuple[float, float, float, float]]:
        word_boxes = []
        for x0, y0, x1, y1 in boxes:
            bx0 = max(0, x0 - element_anchor_padding)
            by0 = max(0, y0 - element_anchor_padding)
            bx1 = min(train_w, x1 + element_anchor_padding)
            by1 = min(train_h, y1 + element_anchor_padding)
            if bx1 > bx0 and by1 > by0:
                word_boxes.append((bx0 / train_w, by0 / train_h, bx1 / train_w, by1 / train_h))
        return word_boxes

    element_line_boxes = build_word_boxes(scaled_text_boxes) if element_anchor_mode == "word" else build_line_boxes(scaled_text_boxes)

    model = TimeCanvas(
        width=train_w,
        height=train_h,
        channels=int(config["channels"]),
        hidden=int(config["hidden"]),
        freq_bands=int(config["freq_bands"]),
        time_bands=int(config["time_bands"]),
        flow_scale=flow_scale * 1.4,
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=float(config["lr"]), weight_decay=0.0)
    compile_start = perf_counter()
    losses = []
    for step in range(steps):
        text_count = max(0, min(batch_size, int(batch_size * text_box_sample_ratio))) if text_has_pixels else 0
        remaining = batch_size - text_count
        edge_count = max(0, min(remaining, int(batch_size * edge_sample_ratio)))
        uniform_count = batch_size - text_count - edge_count
        idx_parts = []
        if uniform_count:
            idx_parts.append(torch.randint(0, train_w * train_h, (uniform_count,), device=device))
        if edge_count:
            idx_parts.append(torch.multinomial(glyph_prob, edge_count, replacement=True))
        if text_count:
            idx_parts.append(torch.multinomial(text_prob, text_count, replacement=True))
        idx = torch.cat(idx_parts, dim=0)
        ys = torch.div(idx, train_w, rounding_mode="floor")
        xs = idx - ys * train_w
        coords = torch.stack(
            [
                xs.float() / max(1, train_w - 1),
                ys.float() / max(1, train_h - 1),
            ],
            dim=-1,
        )
        t = torch.rand((batch_size, 1), device=device)
        target_coords = target_coords_for_motion(coords, t, motion_strength, motion_mode)
        truth = sample_target(target_chw, target_coords)
        pred = model(coords, t)
        if edge_loss_weight > 0 or text_box_loss_weight > 0:
            glyph_weights = sample_target(glyph_weight_chw, target_coords).squeeze(-1)
            text_weights = sample_target(text_weight_chw, target_coords).squeeze(-1)
            weights = 1.0 + edge_loss_weight * glyph_weights + text_box_loss_weight * text_weights
            loss = (((pred - truth).square().mean(dim=-1)) * weights).mean()
        else:
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

    def render_named(name: str, width: int, height: int, viewport: tuple[float, float, float, float], t_value: float):
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        start = perf_counter()
        img_tensor = model.render(width, height, viewport, t_value)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        render_times[name] = (perf_counter() - start) * 1000
        artifacts[name] = base64.b64encode(tensor_to_png_bytes(img_tensor)).decode("ascii")
        return img_tensor

    def frame_viewport(t_value: float) -> tuple[float, float, float, float]:
        if video_viewport_mode == "zoom-pulse":
            envelope = float(np.sin(np.pi * t_value) ** 2)
            width = max(0.40, 1.0 - viewport_zoom * envelope)
            height = max(0.40, 1.0 - viewport_zoom * 0.72 * envelope)
            pan_x = viewport_pan * float(np.sin(2.0 * np.pi * t_value)) * envelope
            pan_y = viewport_pan * 0.45 * float(np.cos(2.0 * np.pi * t_value)) * envelope
            x0 = min(max((1.0 - width) * 0.5 + pan_x, 0.0), 1.0 - width)
            y0 = min(max((1.0 - height) * 0.5 + pan_y, 0.0), 1.0 - height)
            return (x0, y0, width, height)
        return (0.0, 0.0, 1.0, 1.0)

    @torch.inference_mode()
    def render_layout_frame(width: int, height: int, t_value: float) -> torch.Tensor:
        xs = torch.linspace(0.0, 1.0, width, device=device)
        ys = torch.linspace(0.0, 1.0, height, device=device)
        yy, xx = torch.meshgrid(ys, xs, indexing="ij")
        coords = torch.stack([xx.reshape(-1), yy.reshape(-1)], dim=-1)
        valid = torch.ones((coords.shape[0], 1), device=device, dtype=torch.bool)
        if video_layout_mode in {"frame-scale", "element-frame-scale"}:
            envelope = float(np.sin(np.pi * t_value) ** 2)
            scale_x = max(0.35, 1.0 - layout_transform_strength * envelope)
            scale_y = max(0.35, 1.0 - layout_transform_strength * 0.72 * envelope)
            pan_x = layout_transform_pan * float(np.sin(2.0 * np.pi * t_value)) * envelope
            pan_y = layout_transform_pan * 0.45 * float(np.cos(2.0 * np.pi * t_value)) * envelope
            canonical = torch.empty_like(coords)
            canonical[:, 0] = 0.5 + (coords[:, 0] - 0.5 - pan_x) / scale_x
            canonical[:, 1] = 0.5 + (coords[:, 1] - 0.5 - pan_y) / scale_y
            valid = (
                (canonical[:, 0:1] >= 0.0)
                & (canonical[:, 0:1] <= 1.0)
                & (canonical[:, 1:2] >= 0.0)
                & (canonical[:, 1:2] <= 1.0)
            )
            coords = canonical.clamp(0.0, 1.0)

        t = torch.zeros((coords.shape[0], 1), device=device)
        parts = []
        chunk = 262144
        for start in range(0, coords.shape[0], chunk):
            parts.append(model.forward(coords[start : start + chunk], t[start : start + chunk]))
        frame = torch.cat(parts, dim=0)
        if video_layout_mode != "none":
            frame = torch.where(valid, frame, torch.ones_like(frame))
        frame = frame.view(height, width, 3)

        if video_layout_mode == "element-frame-scale" and element_line_boxes:
            envelope = float(np.sin(np.pi * t_value) ** 2)
            scale_x = max(0.35, 1.0 - layout_transform_strength * envelope)
            scale_y = max(0.35, 1.0 - layout_transform_strength * 0.72 * envelope)
            pan_x = layout_transform_pan * float(np.sin(2.0 * np.pi * t_value)) * envelope
            pan_y = layout_transform_pan * 0.45 * float(np.cos(2.0 * np.pi * t_value)) * envelope
            elem_scale_x = 1.0 - (1.0 - scale_x) * element_scale_ratio
            elem_scale_y = 1.0 - (1.0 - scale_y) * element_scale_ratio
            for bx0, by0, bx1, by1 in element_line_boxes:
                bw = bx1 - bx0
                bh = by1 - by0
                if bw <= 0 or bh <= 0:
                    continue
                cx = (bx0 + bx1) * 0.5
                cy = (by0 + by1) * 0.5
                out_cx = 0.5 + (cx - 0.5) * scale_x + pan_x
                out_cy = 0.5 + (cy - 0.5) * scale_y + pan_y
                out_w = bw * elem_scale_x
                out_h = bh * elem_scale_y
                ox0 = max(0, int(round((out_cx - out_w * 0.5) * width)))
                oy0 = max(0, int(round((out_cy - out_h * 0.5) * height)))
                ox1 = min(width, int(round((out_cx + out_w * 0.5) * width)))
                oy1 = min(height, int(round((out_cy + out_h * 0.5) * height)))
                patch_w = ox1 - ox0
                patch_h = oy1 - oy0
                if patch_w < 2 or patch_h < 2:
                    continue
                patch_xs = torch.linspace(bx0, bx1, patch_w, device=device)
                patch_ys = torch.linspace(by0, by1, patch_h, device=device)
                patch_yy, patch_xx = torch.meshgrid(patch_ys, patch_xs, indexing="ij")
                patch_coords = torch.stack([patch_xx.reshape(-1), patch_yy.reshape(-1)], dim=-1).clamp(0.0, 1.0)
                patch_t = torch.zeros((patch_coords.shape[0], 1), device=device)
                patch_parts = []
                for start in range(0, patch_coords.shape[0], chunk):
                    patch_parts.append(model.forward(patch_coords[start : start + chunk], patch_t[start : start + chunk]))
                patch = torch.cat(patch_parts, dim=0).view(patch_h, patch_w, 3)
                if element_mask_mode == "text-alpha":
                    alpha = sample_target(element_alpha_chw, patch_coords).view(patch_h, patch_w, 1).clamp(0.0, 1.0)
                    frame[oy0:oy1, ox0:ox1] = patch * alpha + frame[oy0:oy1, ox0:ox1] * (1.0 - alpha)
                else:
                    frame[oy0:oy1, ox0:ox1] = patch

        return frame

    first = render_named("render-960.png", 960, 544, (0.0, 0.0, 1.0, 1.0), 0.0)
    render_named("render-mid.png", 960, 544, (0.0, 0.0, 1.0, 1.0), 0.5)
    render_named("render-last.png", 960, 544, (0.0, 0.0, 1.0, 1.0), 1.0)
    render_named("render-512.png", 512, 288, (0.0, 0.0, 1.0, 1.0), 0.25)
    render_named("crop-2x.png", 960, 544, (0.25, 0.25, 0.5, 0.5), 0.25)
    if video_viewport_mode != "static":
        render_named("render-viewport-mid.png", 960, 544, frame_viewport(0.5), 0.5)
    if video_layout_mode != "none":
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        start = perf_counter()
        layout_mid = render_layout_frame(960, 544, 0.5)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        mid_name = "render-element-mid.png" if video_layout_mode == "element-frame-scale" else "render-layout-mid.png"
        render_times[mid_name] = (perf_counter() - start) * 1000
        artifacts[mid_name] = base64.b64encode(tensor_to_png_bytes(layout_mid)).decode("ascii")
    artifacts["text-mask.png"] = base64.b64encode(
        tensor_to_png_bytes(text_mask.unsqueeze(-1).repeat(1, 1, 3))
    ).decode("ascii")
    artifacts["element-alpha-mask.png"] = base64.b64encode(
        tensor_to_png_bytes(element_alpha.unsqueeze(-1).repeat(1, 1, 3))
    ).decode("ascii")

    video_frames = []
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    video_start = perf_counter()
    frame_count = int(config["frames"])
    for i in range(frame_count):
        t_value = i / max(1, frame_count - 1)
        if video_layout_mode != "none":
            video_frames.append(render_layout_frame(960, 544, t_value))
        else:
            video_frames.append(model.render(960, 544, frame_viewport(t_value), t_value))
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    render_33_wall_ms = (perf_counter() - video_start) * 1000
    video_bytes, encode_ms = encode_mp4(video_frames, 960, 544, int(config["fps"]))
    artifacts["output.mp4"] = base64.b64encode(video_bytes).decode("ascii")

    motion_delta = float(torch.mean(torch.abs(first - video_frames[frame_count // 2])).detach().cpu())
    loop_error = float(torch.mean(torch.abs(first - video_frames[-1])).detach().cpu())

    glyph_enabled = edge_sample_ratio > 0 or edge_loss_weight > 0
    text_enabled = text_box_sample_ratio > 0 or text_box_loss_weight > 0
    metrics = {
        "canvas_type": (
            "stable-latent-feature-grid-element-anchor-layout-text-box-weighted"
            if text_enabled and video_layout_mode == "element-frame-scale"
            else "stable-latent-feature-grid-layout-transform-text-box-weighted"
            if text_enabled and video_layout_mode != "none"
            else "time-conditioned-latent-feature-grid-learned-flow-mlp-text-box-weighted"
            if text_enabled
            else "time-conditioned-latent-feature-grid-learned-flow-mlp-glyph-weighted"
            if glyph_enabled
            else "time-conditioned-latent-feature-grid-learned-flow-mlp"
        ),
        "train_resolution": config["train_resolution"],
        "steps": steps,
        "batch_size": batch_size,
        "channels": int(config["channels"]),
        "hidden": int(config["hidden"]),
        "freq_bands": int(config["freq_bands"]),
        "time_bands": int(config["time_bands"]),
        "lr": float(config["lr"]),
        "flow_scale": flow_scale,
        "motion_mode": motion_mode,
        "motion_strength": motion_strength,
        "video_viewport_mode": video_viewport_mode,
        "viewport_zoom": viewport_zoom,
        "viewport_pan": viewport_pan,
        "video_layout_mode": video_layout_mode,
        "layout_transform_strength": layout_transform_strength,
        "layout_transform_pan": layout_transform_pan,
        "element_scale_ratio": element_scale_ratio,
        "element_anchor_padding": element_anchor_padding,
        "element_mask_mode": element_mask_mode,
        "element_anchor_mode": element_anchor_mode,
        "element_line_count": len(element_line_boxes),
        "min_ocr_similarity": float(config.get("min_ocr_similarity", 0.5)),
        "min_motion_delta": float(config.get("min_motion_delta", 0.001)),
        "edge_sample_ratio": edge_sample_ratio,
        "edge_loss_weight": edge_loss_weight,
        "text_box_sample_ratio": text_box_sample_ratio,
        "text_box_loss_weight": text_box_loss_weight,
        "text_box_padding": text_box_padding,
        "text_box_count": len(config.get("text_boxes", [])),
        "text_mask_coverage": float(text_mask.mean().detach().cpu()),
        "element_alpha_coverage": float((element_alpha > 0.05).float().mean().detach().cpu()),
        "compile_ms": compile_ms,
        "final_mse": losses[-1]["mse"],
        "losses": losses,
        "render_times": render_times,
        "render_960_ms": render_times["render-960.png"],
        "render_33_wall_ms": render_33_wall_ms,
        "encode_ms": encode_ms,
        "resize_consistency": 0.0,
        "temporal_consistency": max(0.0, 1.0 - loop_error),
        "motion_delta_model": motion_delta,
        "loop_error_model": loop_error,
        "description": (
            f"C2.6 neural canvas: stable content with OCR {element_anchor_mode} anchors, {element_mask_mode} masks, and {video_layout_mode} layout transform"
            if text_enabled and video_layout_mode == "element-frame-scale"
            else f"C2.3 neural canvas: stable content with {video_layout_mode} layout transform"
            if text_enabled and video_layout_mode != "none"
            else f"C2.1 neural canvas: learned {motion_mode} motion with OCR text-box-weighted sampling/loss"
            if text_enabled
            else "C2-lite neural canvas: learned time-conditioned motion field with glyph-weighted sampling/loss"
            if glyph_enabled
            else "C2-lite neural canvas: learned time-conditioned motion field sampling a persistent latent canvas"
        ),
    }
    return {"artifacts": artifacts, "metrics": metrics}


@app.local_entrypoint()
def main(
    steps: int = 3000,
    train_resolution: str = "960x544",
    batch_size: int = 131072,
    channels: int = 16,
    hidden: int = 96,
    freq_bands: int = 8,
    time_bands: int = 4,
    lr: float = 0.01,
    flow_scale: float = 0.006,
    motion_mode: str = "jiggle",
    motion_strength: float = -1.0,
    video_viewport_mode: str = "static",
    viewport_zoom: float = 0.0,
    viewport_pan: float = 0.0,
    video_layout_mode: str = "none",
    layout_transform_strength: float = 0.0,
    layout_transform_pan: float = 0.0,
    element_scale_ratio: float = 0.25,
    element_anchor_padding: int = 3,
    element_mask_mode: str = "rectangle",
    element_anchor_mode: str = "line",
    experiment_label: str = "",
    edge_sample_ratio: float = 0.0,
    edge_loss_weight: float = 0.0,
    text_box_sample_ratio: float = 0.0,
    text_box_loss_weight: float = 0.0,
    text_box_padding: int = 3,
    text_box_min_conf: float = 55.0,
    min_ocr_similarity: float = 0.5,
    min_motion_delta: float = 0.001,
    frames: int = 33,
    fps: int = 24,
):
    ensure_fixture()
    with Image.open(FIXTURE) as fixture_image:
        source_resolution = list(fixture_image.size)
    text_boxes = detect_text_boxes(FIXTURE, text_box_min_conf) if text_box_sample_ratio > 0 or text_box_loss_weight > 0 else []
    if motion_strength < 0:
        motion_strength = flow_scale
    config = {
        "steps": steps,
        "train_resolution": train_resolution,
        "batch_size": batch_size,
        "channels": channels,
        "hidden": hidden,
        "freq_bands": freq_bands,
        "time_bands": time_bands,
        "lr": lr,
        "flow_scale": flow_scale,
        "motion_mode": motion_mode,
        "motion_strength": motion_strength,
        "video_viewport_mode": video_viewport_mode,
        "viewport_zoom": viewport_zoom,
        "viewport_pan": viewport_pan,
        "video_layout_mode": video_layout_mode,
        "layout_transform_strength": layout_transform_strength,
        "layout_transform_pan": layout_transform_pan,
        "element_scale_ratio": element_scale_ratio,
        "element_anchor_padding": element_anchor_padding,
        "element_mask_mode": element_mask_mode,
        "element_anchor_mode": element_anchor_mode,
        "experiment_label": experiment_label,
        "min_ocr_similarity": min_ocr_similarity,
        "min_motion_delta": min_motion_delta,
        "edge_sample_ratio": edge_sample_ratio,
        "edge_loss_weight": edge_loss_weight,
        "text_box_sample_ratio": text_box_sample_ratio,
        "text_box_loss_weight": text_box_loss_weight,
        "text_box_padding": text_box_padding,
        "text_box_min_conf": text_box_min_conf,
        "text_boxes": text_boxes,
        "source_resolution": source_resolution,
        "frames": frames,
        "fps": fps,
    }
    motion_suffix = "" if motion_mode == "jiggle" and video_viewport_mode == "static" and video_layout_mode == "none" else f"-{motion_mode}"
    if video_layout_mode != "none":
        motion_suffix += f"-layout-{video_layout_mode}"
    suffix = "-text" if text_box_sample_ratio > 0 or text_box_loss_weight > 0 else "-glyph" if edge_sample_ratio > 0 or edge_loss_weight > 0 else ""
    label_suffix = f"-{slugify(experiment_label)}" if experiment_label else ""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"{timestamp}-c2-lite{suffix}{motion_suffix}{label_suffix}-{train_resolution}-s{steps}"
    run_dir = OUTPUT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    input_path = run_dir / "input.png"
    input_path.write_bytes(FIXTURE.read_bytes())
    (run_dir / "text-boxes.json").write_text(json.dumps(text_boxes, indent=2) + "\n", encoding="utf-8")

    log_config = {**config, "text_boxes": f"{len(text_boxes)} boxes"}
    print(f"START {run_id} config={json.dumps(log_config, sort_keys=True)}", flush=True)
    result = train_and_render_motion.remote(FIXTURE.read_bytes(), config)

    for name, encoded in result["artifacts"].items():
        (run_dir / name).write_bytes(base64.b64decode(encoded))

    metrics = result["metrics"]
    artifact_paths = {
        "input": str(input_path),
        "render_960": str(run_dir / "render-960.png"),
        "render_mid": str(run_dir / "render-mid.png"),
        "render_last": str(run_dir / "render-last.png"),
        "render_512": str(run_dir / "render-512.png"),
        "crop_2x": str(run_dir / "crop-2x.png"),
        "text_mask": str(run_dir / "text-mask.png"),
        "element_alpha_mask": str(run_dir / "element-alpha-mask.png"),
        "text_boxes": str(run_dir / "text-boxes.json"),
        "output": str(run_dir / "output.mp4"),
        "metrics": str(run_dir / "metrics.json"),
        "quality": str(run_dir / "quality.json"),
    }
    if video_viewport_mode != "static":
        artifact_paths["render_viewport_mid"] = str(run_dir / "render-viewport-mid.png")
    if video_layout_mode != "none":
        if video_layout_mode == "element-frame-scale":
            artifact_paths["render_element_mid"] = str(run_dir / "render-element-mid.png")
        else:
            artifact_paths["render_layout_mid"] = str(run_dir / "render-layout-mid.png")
    metrics.update(
        {
            "run_id": run_id,
            "commit": git_commit(),
            "track": "C",
            "width": 960,
            "height": 544,
            "frames": frames,
            "fps": fps,
            "artifacts": artifact_paths,
        }
    )
    quality = write_quality(run_dir, metrics)
    metrics["ocr_similarity"] = quality["ocr_similarity"]
    metrics["layout_similarity"] = quality["layout_similarity"]
    metrics["resize_consistency"] = quality["layout_similarity"]
    metrics["motion_delta"] = quality["motion_delta"]
    metrics["loop_error"] = quality["loop_error"]
    total_ms = metrics["render_33_wall_ms"] + metrics["encode_ms"]
    metrics["status"] = (
        "pass"
        if total_ms <= 1300
        and quality["motion_delta"] > min_motion_delta
        and quality["ocr_similarity"] >= min_ocr_similarity
        else "near_miss"
    )
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    append_results(metrics, quality)

    print(json.dumps(metrics, indent=2), flush=True)
    print(f"DONE {run_id} quality={quality['ocr_similarity']:.4f} motion={quality['motion_delta']:.4f}", flush=True)
