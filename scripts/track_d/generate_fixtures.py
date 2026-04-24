#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = ROOT / "fixtures" / "track-d"
WIDTH = 1280
HEIGHT = 736

PALETTES = [
    {
        "paper": "#f7f4ec",
        "panel": "#fffdf8",
        "ink": "#16181d",
        "muted": "#5d6672",
        "line": "#c8bfae",
        "a": "#0f6b83",
        "b": "#8f4d2e",
        "c": "#497a46",
        "d": "#735aa6",
    },
    {
        "paper": "#eef4f2",
        "panel": "#fbfffd",
        "ink": "#17201e",
        "muted": "#63726f",
        "line": "#b7c8c2",
        "a": "#1f7a5c",
        "b": "#b24a5a",
        "c": "#365c9c",
        "d": "#8a6d2a",
    },
    {
        "paper": "#f4f6fb",
        "panel": "#ffffff",
        "ink": "#121927",
        "muted": "#5c6475",
        "line": "#cad1df",
        "a": "#315ea8",
        "b": "#a43d67",
        "c": "#2c7658",
        "d": "#9a6b28",
    },
]

TEMPLATES = [
    "article",
    "dashboard",
    "diagram",
    "product_grid",
    "map_labels",
    "illustration",
    "microtext",
]

MOTION_PROGRAMS = [
    {"id": "subtle-motion-loop", "motion_mode": "jiggle", "motion_strength": 0.0125},
    {"id": "viewport-zoom-pulse", "motion_mode": "jiggle", "motion_strength": 0.010, "viewport_zoom": 0.05},
    {"id": "responsive-squeeze", "motion_mode": "responsive-squeeze", "motion_strength": 0.012},
]


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


@dataclass
class FixtureState:
    image: Image.Image
    draw: ImageDraw.ImageDraw
    palette: dict[str, str]
    rng: random.Random
    regions: list[dict[str, Any]] = field(default_factory=list)
    text_fragments: list[str] = field(default_factory=list)
    next_region: int = 0

    def add_region(self, kind: str, bbox: tuple[int, int, int, int], **extra: Any) -> None:
        x0, y0, x1, y1 = bbox
        self.regions.append(
            {
                "id": f"r{self.next_region:03d}",
                "kind": kind,
                "bbox": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
                **extra,
            }
        )
        self.next_region += 1

    def text(self, xy: tuple[int, int], text: str, font: ImageFont.ImageFont, fill: str | None = None, role: str = "body") -> tuple[int, int, int, int]:
        x, y = xy
        fill = fill or self.palette["ink"]
        self.draw.text((x, y), text, fill=fill, font=font)
        bbox = self.draw.textbbox((x, y), text, font=font)
        self.add_region("text", bbox, role=role, text=text)
        self.text_fragments.append(text)
        return bbox


def split_for(index: int) -> str:
    bucket = index % 10
    if bucket <= 6:
        return "train"
    if bucket == 7:
        return "val"
    return "test"


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = word if not line else f"{line} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            line = candidate
            continue
        if line:
            lines.append(line)
        line = word
    if line:
        lines.append(line)
    return lines


def wrapped_text(state: FixtureState, xy: tuple[int, int], text: str, font: ImageFont.ImageFont, max_width: int, fill: str | None = None, spacing: int = 6, role: str = "body") -> int:
    x, y = xy
    for line in wrap(state.draw, text, font, max_width):
        bbox = state.text((x, y), line, font, fill=fill, role=role)
        y = bbox[3] + spacing
    return y


def rounded_panel(state: FixtureState, bbox: tuple[int, int, int, int], fill: str | None = None, outline: str | None = None, radius: int = 10, width: int = 2, role: str = "panel") -> None:
    fill = fill or state.palette["panel"]
    outline = outline or state.palette["line"]
    state.draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)
    state.add_region("semantic", bbox, role=role)


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], fill: str, width: int = 3) -> None:
    x0, y0 = start
    x1, y1 = end
    draw.line((x0, y0, x1, y1), fill=fill, width=width)
    angle = math.atan2(y1 - y0, x1 - x0)
    size = 12
    left = (x1 - size * math.cos(angle - 0.45), y1 - size * math.sin(angle - 0.45))
    right = (x1 - size * math.cos(angle + 0.45), y1 - size * math.sin(angle + 0.45))
    draw.polygon([(x1, y1), left, right], fill=fill)


def draw_rotated_text(state: FixtureState, center: tuple[int, int], text: str, font: ImageFont.ImageFont, angle: float, fill: str, role: str = "label") -> None:
    bbox = state.draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0] + 12
    h = bbox[3] - bbox[1] + 12
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.text((6, 6), text, font=font, fill=fill)
    rotated = layer.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    x = center[0] - rotated.width // 2
    y = center[1] - rotated.height // 2
    state.image.paste(rotated, (x, y), rotated)
    state.add_region("text", (x, y, x + rotated.width, y + rotated.height), role=role, text=text, angle=angle)
    state.text_fragments.append(text)


def draw_article(state: FixtureState) -> None:
    p = state.palette
    rounded_panel(state, (58, 44, 1222, 692), radius=14, role="article-page")
    title = _font(43, bold=True)
    subtitle = _font(19)
    head = _font(22, bold=True)
    body = _font(16)
    small = _font(12)
    state.text((96, 82), "Field Notes: Cities That Learn", title, role="title")
    state.text((100, 136), "A page fixture with dense copy, captions, small labels, and diagrams.", subtitle, fill=p["muted"], role="subtitle")

    lefts = [100, 455, 810]
    heads = ["Transit Signals", "Public Memory", "Water Edges"]
    bodies = [
        "Sensors record demand, but the visible interface must stay legible while the scene moves around it.",
        "Archives, plaques, and pedestrian maps become a shared operating system for streets and civic rooms.",
        "Canals, ferries, and flood marks create spatial labels that are easy to redraw incorrectly.",
    ]
    for x, heading, text in zip(lefts, heads, bodies):
        state.text((x, 208), heading, head, role="section-heading")
        state.draw.line((x, 242, x + 300, 242), fill=p["line"], width=2)
        wrapped_text(state, (x, 260), text, body, 300)

    table = (96, 438, 540, 642)
    rounded_panel(state, table, fill="#f3f8f7", outline="#b3cbc5", role="data-table")
    state.text((124, 462), "Pilot Log", head, role="table-title")
    rows = [("Zone", "Load", "Drift"), ("North Gate", "42%", "+1.2"), ("Canal East", "67%", "-0.4"), ("Archive Row", "58%", "+0.8"), ("Harbor Loop", "73%", "+1.5")]
    y = 502
    for row in rows:
        x = 124
        for value in row:
            state.text((x, y), value, small if y > 502 else _font(13, bold=True), role="table-cell")
            x += 128
        y += 28

    chart = (604, 430, 1164, 642)
    rounded_panel(state, chart, fill="#fbfaf5", outline="#d7cbb7", role="annotated-chart")
    state.text((632, 456), "Signal Stability", head, role="chart-title")
    points = [(650, 590), (730, 556), (812, 574), (900, 518), (988, 532), (1088, 492)]
    state.draw.line(points, fill=p["a"], width=5, joint="curve")
    for px, py in points:
        state.draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=p["b"])
    for text, xy in [("OCR floor", (1048, 515)), ("motion", (732, 532)), ("loop quiet", (896, 486))]:
        state.text(xy, text, small, fill=p["muted"], role="chart-label")


def draw_dashboard(state: FixtureState) -> None:
    p = state.palette
    state.draw.rectangle((0, 0, WIDTH, HEIGHT), fill=p["paper"])
    state.text((54, 34), "Realtime Operations Canvas", _font(34, bold=True), role="title")
    state.text((58, 82), "Held-out dashboard fixture with numbers that should not repaint.", _font(16), fill=p["muted"], role="subtitle")

    cards = [("Revenue", "$42.8k", "+12%"), ("Latency", "548 ms", "-7%"), ("Streams", "24 fps", "stable"), ("Failures", "0.8%", "-0.3")]
    x = 54
    for label, value, delta in cards:
        rounded_panel(state, (x, 124, x + 270, 244), radius=8, role="metric-card")
        state.text((x + 22, 144), label, _font(15), fill=p["muted"], role="metric-label")
        state.text((x + 22, 172), value, _font(32, bold=True), role="metric-value")
        state.text((x + 178, 188), delta, _font(15, bold=True), fill=p["c"], role="metric-delta")
        x += 300

    rounded_panel(state, (54, 282, 750, 666), role="trend-chart")
    state.text((82, 310), "GPU Segment Wall Time", _font(22, bold=True), role="chart-title")
    base_y = 610
    state.draw.line((92, base_y, 710, base_y), fill=p["line"], width=2)
    state.draw.line((92, 350, 92, base_y), fill=p["line"], width=2)
    pts = []
    for i in range(12):
        px = 112 + i * 50
        py = 560 - int(80 * math.sin(i * 0.8)) - state.rng.randint(0, 32)
        pts.append((px, py))
    state.draw.line(pts, fill=p["a"], width=4)
    for px, py in pts:
        state.draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=p["d"])
    for tick, label in [(350, "900"), (438, "700"), (526, "500"), (610, "300")]:
        state.draw.line((88, tick, 96, tick), fill=p["line"], width=1)
        state.text((104, tick - 9), label, _font(11), fill=p["muted"], role="axis-label")

    rounded_panel(state, (790, 282, 1226, 666), role="run-table")
    state.text((818, 310), "Experiment Queue", _font(22, bold=True), role="table-title")
    rows = [
        ("c33-edge075", "running", "0.82"),
        ("c33-edge15", "running", "0.82"),
        ("c33-cap24", "queued", "0.84"),
        ("track-d-000", "draft", "0.75"),
        ("track-d-001", "draft", "0.75"),
        ("track-d-002", "heldout", "0.82"),
    ]
    y = 360
    for name, status, gate in rows:
        state.text((822, y), name, _font(15), role="run-name")
        state.text((988, y), status, _font(15), fill=p["a"] if status == "running" else p["muted"], role="run-status")
        state.text((1128, y), gate, _font(15), role="run-gate")
        state.draw.line((814, y + 28, 1192, y + 28), fill=p["line"], width=1)
        y += 42


def draw_diagram(state: FixtureState) -> None:
    p = state.palette
    rounded_panel(state, (62, 52, 1218, 684), radius=14, role="diagram-page")
    state.text((96, 82), "Neural Canvas Compiler", _font(38, bold=True), role="title")
    state.text((100, 132), "A labeled flow diagram for spatial identity and small technical labels.", _font(17), fill=p["muted"], role="subtitle")

    nodes = [
        ("Prompt", (110, 260, 300, 350), p["a"]),
        ("Page Image", (110, 430, 300, 520), p["b"]),
        ("Encoder", (450, 340, 640, 430), p["c"]),
        ("Latent Canvas", (780, 260, 1032, 350), p["d"]),
        ("Renderer Query", (780, 430, 1032, 520), p["a"]),
    ]
    for label, bbox, color in nodes:
        rounded_panel(state, bbox, fill="#ffffff", outline=color, radius=12, role="diagram-node")
        state.text((bbox[0] + 26, bbox[1] + 30), label, _font(21, bold=True), fill=color, role="node-label")
    draw_arrow(state.draw, (300, 304), (450, 382), p["line"], width=4)
    draw_arrow(state.draw, (300, 474), (450, 388), p["line"], width=4)
    draw_arrow(state.draw, (640, 382), (780, 304), p["line"], width=4)
    draw_arrow(state.draw, (640, 390), (780, 474), p["line"], width=4)
    draw_arrow(state.draw, (906, 352), (906, 430), p["line"], width=4)

    labels = [
        ("text never overlays", (326, 250)),
        ("held-out split", (326, 528)),
        ("persistent grid", (700, 232)),
        ("viewport + time", (1038, 462)),
        ("33 frames <= 1.3s", (820, 560)),
    ]
    for text, xy in labels:
        state.text(xy, text, _font(14), fill=p["muted"], role="diagram-caption")

    for i in range(8):
        x = 824 + (i % 4) * 42
        y = 294 + (i // 4) * 24
        state.draw.rectangle((x, y, x + 26, y + 14), fill=[p["a"], p["b"], p["c"], p["d"]][i % 4])


def draw_product_grid(state: FixtureState) -> None:
    p = state.palette
    state.text((54, 42), "Solar Workshop Catalog", _font(37, bold=True), role="title")
    state.text((58, 92), "Product cards mix images, prices, badges, and dense labels.", _font(17), fill=p["muted"], role="subtitle")
    names = ["Flux Lamp", "Copper Shade", "Field Meter", "Panel Clip", "Night Lens", "Signal Loom"]
    prices = ["$48", "$128", "$76", "$19", "$54", "$210"]
    for idx, name in enumerate(names):
        col = idx % 3
        row = idx // 3
        x = 58 + col * 405
        y = 142 + row * 260
        rounded_panel(state, (x, y, x + 350, y + 220), role="product-card")
        color = [p["a"], p["b"], p["c"], p["d"]][idx % 4]
        state.draw.rounded_rectangle((x + 24, y + 24, x + 154, y + 150), radius=14, fill="#eef1f5", outline=p["line"], width=2)
        state.draw.ellipse((x + 56, y + 48, x + 124, y + 116), fill=color)
        state.draw.rectangle((x + 74, y + 118, x + 106, y + 150), fill="#ffffff", outline=p["line"])
        state.text((x + 180, y + 32), name, _font(22, bold=True), role="product-name")
        state.text((x + 180, y + 72), prices[idx], _font(26, bold=True), fill=color, role="price")
        state.text((x + 180, y + 112), f"sku {idx + 1842}-Q", _font(13), fill=p["muted"], role="sku")
        state.text((x + 180, y + 142), "rated for outdoor rigs", _font(13), role="description")
        state.text((x + 28, y + 170), "limited batch", _font(12, bold=True), fill=p["b"], role="badge")


def draw_map_labels(state: FixtureState) -> None:
    p = state.palette
    rounded_panel(state, (54, 48, 1226, 688), fill="#fbfcf6", role="map-page")
    state.text((92, 82), "Harbor Floorplan", _font(38, bold=True), role="title")
    state.text((96, 132), "Rotated labels and irregular regions catch text-box overfitting.", _font(17), fill=p["muted"], role="subtitle")
    rooms = [
        (120, 220, 420, 440, "#e9f3f0", "North Gallery"),
        (430, 190, 710, 376, "#f3eae7", "Archive Hall"),
        (730, 220, 1120, 500, "#edf0fa", "Canal Studio"),
        (220, 470, 620, 620, "#f6f1df", "Service Court"),
        (650, 520, 1060, 638, "#eaf4e3", "Market Walk"),
    ]
    for x0, y0, x1, y1, fill, label in rooms:
        state.draw.rounded_rectangle((x0, y0, x1, y1), radius=18, fill=fill, outline=p["line"], width=3)
        state.add_region("semantic", (x0, y0, x1, y1), role="map-region", label=label)
    corridors = [(420, 300, 730, 346), (560, 376, 620, 520), (620, 552, 650, 604), (710, 340, 780, 410)]
    for bbox in corridors:
        state.draw.rounded_rectangle(bbox, radius=12, fill="#ffffff", outline=p["line"], width=2)
        state.add_region("semantic", bbox, role="corridor")
    draw_rotated_text(state, (270, 330), "North Gallery", _font(22, bold=True), -8, p["a"])
    draw_rotated_text(state, (570, 284), "Archive Hall", _font(21, bold=True), 5, p["b"])
    draw_rotated_text(state, (925, 354), "Canal Studio", _font(24, bold=True), 12, p["c"])
    draw_rotated_text(state, (430, 548), "Service Court", _font(20, bold=True), -3, p["d"])
    draw_rotated_text(state, (848, 585), "Market Walk", _font(20, bold=True), 2, p["a"])
    for text, xy in [("Gate A", (124, 190)), ("Lift 02", (644, 402)), ("Dock labels should stay fixed", (812, 154)), ("Scale 1:240", (1000, 650))]:
        state.text(xy, text, _font(13), fill=p["muted"], role="map-note")


def draw_illustration(state: FixtureState) -> None:
    p = state.palette
    state.draw.rectangle((0, 0, WIDTH, HEIGHT), fill="#eff5f7")
    state.text((70, 54), "Low-Text Illustration Page", _font(38, bold=True), role="title")
    state.text((74, 104), "This fixture checks visual identity without leaning on OCR.", _font(17), fill=p["muted"], role="subtitle")
    state.draw.rectangle((0, 546, WIDTH, HEIGHT), fill="#dfe8df")
    state.draw.polygon([(120, 546), (320, 240), (520, 546)], fill="#9fb7b5")
    state.draw.polygon([(392, 546), (642, 180), (898, 546)], fill="#b9a999")
    state.draw.polygon([(760, 546), (1058, 300), (1260, 546)], fill="#91a9c2")
    for x in range(110, 1160, 120):
        h = state.rng.randint(68, 150)
        state.draw.rectangle((x, 546 - h, x + 44, 546), fill=p["a"])
        state.draw.rectangle((x + 12, 546 - h - 42, x + 32, 546 - h), fill=p["b"])
    rounded_panel(state, (814, 126, 1156, 268), fill="#ffffff", role="caption")
    wrapped_text(state, (842, 152), "Illustration pages expose whether the model can preserve visual motifs when text is sparse.", _font(16), 280)
    state.text((92, 610), "caption: hills, masts, and panel edges should remain coherent", _font(14), fill=p["muted"], role="caption")


def draw_microtext(state: FixtureState) -> None:
    p = state.palette
    rounded_panel(state, (50, 42, 1230, 694), role="microtext-page")
    state.text((84, 74), "Small Print Stress Sheet", _font(35, bold=True), role="title")
    state.text((88, 120), "Many tiny tokens create a brutal but useful held-out OCR target.", _font(16), fill=p["muted"], role="subtitle")
    tiny = _font(10)
    head = _font(14, bold=True)
    for col in range(4):
        x = 86 + col * 286
        state.text((x, 174), f"Column {col + 1}", head, role="small-heading")
        y = 206
        for row in range(13):
            code = f"{chr(65 + col)}{row:02d}-{state.rng.randint(100, 999)}"
            value = f"{code} validation token stable under resize"
            state.text((x, y), value, tiny, role="small-print")
            y += 28
    state.draw.line((80, 584, 1180, 584), fill=p["line"], width=2)
    for i, label in enumerate(["alpha-13", "beta-29", "gamma-47", "delta-88", "epsilon-05"]):
        x = 116 + i * 206
        state.draw.rounded_rectangle((x, 618, x + 148, 652), radius=8, fill="#eef3f8", outline=p["line"])
        state.text((x + 18, 626), label, _font(13, bold=True), fill=p["a"], role="tag")


DRAWERS = {
    "article": draw_article,
    "dashboard": draw_dashboard,
    "diagram": draw_diagram,
    "product_grid": draw_product_grid,
    "map_labels": draw_map_labels,
    "illustration": draw_illustration,
    "microtext": draw_microtext,
}


def make_fixture(index: int, seed: int, width: int, height: int, out_dir: Path) -> dict[str, Any]:
    rng = random.Random(seed + index * 1009)
    template = TEMPLATES[index % len(TEMPLATES)]
    palette = PALETTES[index % len(PALETTES)]
    image = Image.new("RGB", (width, height), palette["paper"])
    state = FixtureState(image=image, draw=ImageDraw.Draw(image), palette=palette, rng=rng)
    DRAWERS[template](state)

    split = split_for(index)
    fixture_id = f"trackd-{index:04d}-{template}"
    image_path = out_dir / "pages" / f"{fixture_id}.png"
    meta_path = out_dir / "metadata" / f"{fixture_id}.json"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(image_path, "PNG")

    motion = MOTION_PROGRAMS[index % len(MOTION_PROGRAMS)]
    record = {
        "id": fixture_id,
        "track": "track-d",
        "split": split,
        "template": template,
        "seed": seed + index * 1009,
        "image": str(image_path.relative_to(ROOT)),
        "metadata": str(meta_path.relative_to(ROOT)),
        "width": width,
        "height": height,
        "expected_text": " ".join(state.text_fragments),
        "text_region_count": sum(1 for region in state.regions if region["kind"] == "text"),
        "semantic_region_count": sum(1 for region in state.regions if region["kind"] == "semantic"),
        "motion_program": motion,
        "regions": state.regions,
    }
    meta_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def write_manifest(records: list[dict[str, Any]], out_dir: Path) -> None:
    manifest = out_dir / "manifest.jsonl"
    manifest.write_text("\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n", encoding="utf-8")

    summary = {
        "count": len(records),
        "splits": {split: sum(1 for record in records if record["split"] == split) for split in ["train", "val", "test"]},
        "templates": {template: sum(1 for record in records if record["template"] == template) for template in TEMPLATES},
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Track D held-out neural canvas fixture pages.")
    parser.add_argument("--count", type=int, default=21)
    parser.add_argument("--seed", type=int, default=20260424)
    parser.add_argument("--width", type=int, default=WIDTH)
    parser.add_argument("--height", type=int, default=HEIGHT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    records = [make_fixture(index, args.seed, args.width, args.height, args.out_dir) for index in range(args.count)]
    write_manifest(records, args.out_dir)
    print(json.dumps({"out_dir": str(args.out_dir), "count": len(records)}, sort_keys=True))


if __name__ == "__main__":
    main()
