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
from PIL import Image, ImageDraw, ImageFont


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


def fixture_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if current and bbox[2] - bbox[0] > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def create_clean_reflow_target(width: int, height: int, variant: str = "diagram-left") -> Image.Image:
    variant_key = str(variant or "diagram-left").lower().replace("_", "-")
    if variant_key in {"right-diagram", "cards-left", "variant1", "v1"}:
        return create_clean_reflow_target_right_diagram(width, height)
    if variant_key in {"stacked", "poster-grid", "variant2", "v2"}:
        return create_clean_reflow_target_stacked(width, height)
    if variant_key in {"unboxed-columns", "open-columns", "variant3", "v3"}:
        return create_clean_reflow_target_unboxed_columns(width, height)
    if variant_key in {"callout-map", "diagram-callouts", "variant4", "v4"}:
        return create_clean_reflow_target_callout_map(width, height)
    if variant_key in {"changed-unboxed", "new-copy-unboxed", "variant5", "v5"}:
        return create_clean_reflow_target_unboxed_columns(width, height, changed=True)
    if variant_key in {"changed-callout", "new-copy-callout", "variant6", "v6"}:
        return create_clean_reflow_target_callout_map(width, height, changed=True)

    img = Image.new("RGB", (width, height), "#f6f4ef")
    draw = ImageDraw.Draw(img)

    margin = int(width * 0.055)
    top = int(height * 0.055)
    ink = "#171717"
    muted = "#5f6368"
    line = "#c8c1b4"
    accent = "#146c94"
    green = "#557a46"

    draw.rounded_rectangle(
        [margin, top, width - margin, height - top],
        radius=max(10, width // 110),
        fill="#fffdf8",
        outline=line,
        width=2,
    )

    title_font = fixture_font(max(28, width // 31), bold=True)
    sub_font = fixture_font(max(14, width // 78))
    h_font = fixture_font(max(17, width // 64), bold=True)
    body_font = fixture_font(max(13, width // 84))
    tiny_font = fixture_font(max(10, width // 112))

    x0 = margin + int(width * 0.033)
    y0 = top + int(height * 0.035)
    draw.text((x0, y0), "Sketchapedia: Roman Colosseum", fill=ink, font=title_font)
    draw.text(
        (x0, y0 + int(height * 0.062)),
        "A structured visual page with labels, diagrams, and dense text for stability checks.",
        fill=muted,
        font=sub_font,
    )

    content_top = top + int(height * 0.155)
    content_bottom = height - top - int(height * 0.055)
    left_x = x0
    left_w = int(width * 0.54)
    right_x = x0 + left_w + int(width * 0.035)
    right_w = width - margin - int(width * 0.035) - right_x

    diagram_top = content_top
    diagram_bottom = content_bottom - int(height * 0.115)
    draw.rounded_rectangle(
        [left_x, diagram_top, left_x + left_w, diagram_bottom],
        radius=max(8, width // 140),
        fill="#f1f7f6",
        outline="#b7cdc8",
        width=2,
    )
    draw.text((left_x + 24, diagram_top + 22), "Annotated Section Diagram", fill=ink, font=h_font)

    cx = left_x + int(left_w * 0.50)
    cy = diagram_top + int((diagram_bottom - diagram_top) * 0.56)
    rx = int(left_w * 0.34)
    ry = int((diagram_bottom - diagram_top) * 0.19)
    for offset, color in [(0, accent), (18, "#6aa6b8"), (36, green), (54, "#8d7a4f")]:
        draw.ellipse([cx - rx + offset, cy - ry + offset // 3, cx + rx - offset, cy + ry - offset // 3], outline=color, width=3)
    draw.rectangle([cx - 18, cy - 58, cx + 18, cy + 58], fill="#fffdf8", outline=line)
    for text, lx, ly in [
        ("upper seating", cx + rx - 10, cy - ry - 20),
        ("awnings", cx - rx - 74, cy - ry + 38),
        ("arena floor", cx + rx + 12, cy + 6),
        ("service level", cx - rx - 98, cy + ry - 28),
    ]:
        draw.text((lx, ly), text, fill=ink, font=tiny_font)
        draw.line((lx - 8, ly + 8, cx, cy), fill="#8aa4a1", width=1)

    sections = [
        ("Arena Floor", "Trapdoors, lifts, and service passages created sudden reveals during public spectacles."),
        ("Velarium", "A retractable awning system shaded spectators and required coordinated rope handling."),
        ("Seating", "Social order was encoded into the architecture through tiered, separated seating bands."),
        ("Materials", "Travertine, tuff, brick, and concrete carried both structure and ornament."),
    ]
    card_gap = int(height * 0.025)
    card_h = (diagram_bottom - diagram_top - card_gap * 3) // 4
    for index, (heading, body) in enumerate(sections):
        y = diagram_top + index * (card_h + card_gap)
        draw.rounded_rectangle(
            [right_x, y, right_x + right_w, y + card_h],
            radius=max(7, width // 180),
            fill="#fffaf0",
            outline="#ddd5c7",
            width=1,
        )
        draw.text((right_x + 18, y + 14), heading, fill=ink, font=h_font)
        draw.line((right_x + 18, y + 42, right_x + right_w - 18, y + 42), fill=line, width=1)
        wrapped = wrap_text(draw, body, body_font, right_w - 36)
        draw.multiline_text((right_x + 18, y + 54), wrapped, fill="#2d2d2d", font=body_font, spacing=4)

    notes_y = diagram_bottom + int(height * 0.025)
    notes = [
        "1. Text remains readable across frames.",
        "2. Diagram geometry stays stable.",
        "3. Motion can affect light and atmosphere.",
        "4. Page layout is the canonical frame.",
        "5. Loop boundary stays visually quiet.",
    ]
    note_gap = int(width * 0.022)
    note_col_w = (width - 2 * x0 - 2 * note_gap) // 3
    for idx, note in enumerate(notes):
        col = idx % 3
        row = idx // 3
        nx = x0 + col * (note_col_w + note_gap)
        ny = notes_y + row * int(height * 0.045)
        draw.multiline_text(
            (nx, ny),
            wrap_text(draw, note, tiny_font, note_col_w),
            fill="#263238",
            font=tiny_font,
            spacing=3,
        )

    return img


def create_clean_reflow_target_right_diagram(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height), "#f4f6f8")
    draw = ImageDraw.Draw(img)
    margin = int(width * 0.055)
    top = int(height * 0.055)
    ink = "#15191d"
    muted = "#59636f"
    line = "#bdc7cf"
    accent = "#0e7490"
    green = "#567c4f"

    draw.rounded_rectangle(
        [margin, top, width - margin, height - top],
        radius=max(10, width // 110),
        fill="#ffffff",
        outline=line,
        width=2,
    )
    title_font = fixture_font(max(28, width // 32), bold=True)
    sub_font = fixture_font(max(14, width // 82))
    h_font = fixture_font(max(17, width // 66), bold=True)
    body_font = fixture_font(max(13, width // 88))
    tiny_font = fixture_font(max(10, width // 116))

    x0 = margin + int(width * 0.032)
    y0 = top + int(height * 0.035)
    draw.text((x0, y0), "Sketchapedia: Roman Colosseum", fill=ink, font=title_font)
    draw.text((x0, y0 + int(height * 0.058)), "Clean target variant: cards shift left, diagram moves right.", fill=muted, font=sub_font)

    content_top = top + int(height * 0.145)
    content_bottom = height - top - int(height * 0.075)
    gap = int(width * 0.028)
    cards_x = x0
    cards_w = int(width * 0.39)
    diagram_x = cards_x + cards_w + gap
    diagram_w = width - margin - int(width * 0.032) - diagram_x

    sections = [
        ("Arena Floor", "Trapdoors, lifts, and service passages created sudden reveals during public spectacles."),
        ("Velarium", "A retractable awning system shaded spectators and required coordinated rope handling."),
        ("Seating", "Social order was encoded into the architecture through tiered, separated seating bands."),
        ("Materials", "Travertine, tuff, brick, and concrete carried both structure and ornament."),
    ]
    card_gap = int(height * 0.022)
    card_h = (content_bottom - content_top - 3 * card_gap) // 4
    for index, (heading, body) in enumerate(sections):
        y = content_top + index * (card_h + card_gap)
        draw.rounded_rectangle(
            [cards_x, y, cards_x + cards_w, y + card_h],
            radius=max(7, width // 180),
            fill="#fffaf2",
            outline="#ded3c5",
            width=1,
        )
        draw.text((cards_x + 18, y + 12), heading, fill=ink, font=h_font)
        draw.line((cards_x + 18, y + 40, cards_x + cards_w - 18, y + 40), fill="#d5c8b8", width=1)
        draw.multiline_text((cards_x + 18, y + 52), wrap_text(draw, body, body_font, cards_w - 36), fill="#252525", font=body_font, spacing=4)

    draw.rounded_rectangle(
        [diagram_x, content_top, diagram_x + diagram_w, content_bottom],
        radius=max(8, width // 140),
        fill="#eef7f4",
        outline="#a8c7bf",
        width=2,
    )
    draw.text((diagram_x + 24, content_top + 22), "Annotated Section Diagram", fill=ink, font=h_font)
    cx = diagram_x + int(diagram_w * 0.50)
    cy = content_top + int((content_bottom - content_top) * 0.54)
    rx = int(diagram_w * 0.36)
    ry = int((content_bottom - content_top) * 0.18)
    for offset, color in [(0, accent), (18, "#66a8bd"), (36, green), (54, "#937d50")]:
        draw.ellipse([cx - rx + offset, cy - ry + offset // 3, cx + rx - offset, cy + ry - offset // 3], outline=color, width=3)
    draw.rectangle([cx - 16, cy - 58, cx + 16, cy + 58], fill="#fffdf8", outline="#cabfae")
    for text, lx, ly in [
        ("upper seating", cx + rx - 4, cy - ry - 22),
        ("awnings", cx - rx - 78, cy - ry + 34),
        ("arena floor", cx + rx + 12, cy + 6),
        ("service level", cx - rx - 96, cy + ry - 28),
    ]:
        draw.text((lx, ly), text, fill=ink, font=tiny_font)
        draw.line((lx - 8, ly + 8, cx, cy), fill="#8aa4a1", width=1)

    note_y = content_bottom + int(height * 0.025)
    notes = ["Text remains readable.", "Diagram stays stable.", "Loop boundary stays quiet."]
    note_w = (width - 2 * x0) // 3
    for idx, note in enumerate(notes):
        draw.text((x0 + idx * note_w, note_y), f"{idx + 1}. {note}", fill="#263238", font=tiny_font)
    return img


def create_clean_reflow_target_stacked(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height), "#f7f3ed")
    draw = ImageDraw.Draw(img)
    margin = int(width * 0.055)
    top = int(height * 0.055)
    ink = "#171717"
    muted = "#5d5f66"
    line = "#c9c0b2"
    accent = "#146c94"
    green = "#557a46"

    draw.rounded_rectangle(
        [margin, top, width - margin, height - top],
        radius=max(10, width // 110),
        fill="#fffefa",
        outline=line,
        width=2,
    )
    title_font = fixture_font(max(28, width // 32), bold=True)
    sub_font = fixture_font(max(14, width // 82))
    h_font = fixture_font(max(17, width // 66), bold=True)
    body_font = fixture_font(max(12, width // 92))
    tiny_font = fixture_font(max(10, width // 116))

    x0 = margin + int(width * 0.032)
    y0 = top + int(height * 0.032)
    draw.text((x0, y0), "Sketchapedia: Roman Colosseum", fill=ink, font=title_font)
    draw.text((x0, y0 + int(height * 0.058)), "Clean target variant: wide diagram above four compact study cards.", fill=muted, font=sub_font)

    diagram_top = top + int(height * 0.14)
    diagram_h = int(height * 0.42)
    diagram_x = x0
    diagram_w = width - 2 * x0
    draw.rounded_rectangle(
        [diagram_x, diagram_top, diagram_x + diagram_w, diagram_top + diagram_h],
        radius=max(8, width // 140),
        fill="#eef6f8",
        outline="#a9c4ce",
        width=2,
    )
    draw.text((diagram_x + 24, diagram_top + 20), "Annotated Section Diagram", fill=ink, font=h_font)
    cx = diagram_x + int(diagram_w * 0.50)
    cy = diagram_top + int(diagram_h * 0.58)
    rx = int(diagram_w * 0.28)
    ry = int(diagram_h * 0.22)
    for offset, color in [(0, accent), (18, "#6aa6b8"), (36, green), (54, "#8d7a4f")]:
        draw.ellipse([cx - rx + offset, cy - ry + offset // 3, cx + rx - offset, cy + ry - offset // 3], outline=color, width=3)
    draw.rectangle([cx - 18, cy - 56, cx + 18, cy + 56], fill="#fffdf8", outline=line)
    labels = [
        ("upper seating", cx + rx + 18, cy - ry - 8),
        ("awnings", cx - rx - 92, cy - ry + 18),
        ("arena floor", cx + rx + 24, cy + 10),
        ("service level", cx - rx - 112, cy + ry - 24),
    ]
    for text, lx, ly in labels:
        draw.text((lx, ly), text, fill=ink, font=tiny_font)
        draw.line((lx - 8, ly + 8, cx, cy), fill="#8aa4a1", width=1)

    sections = [
        ("Arena Floor", "Trapdoors, lifts, and service passages created sudden reveals during public spectacles."),
        ("Velarium", "A retractable awning system shaded spectators and required coordinated rope handling."),
        ("Seating", "Social order was encoded into the architecture through tiered, separated seating bands."),
        ("Materials", "Travertine, tuff, brick, and concrete carried both structure and ornament."),
    ]
    cards_top = diagram_top + diagram_h + int(height * 0.035)
    card_gap = int(width * 0.018)
    card_w = (diagram_w - 3 * card_gap) // 4
    card_h = height - top - int(height * 0.06) - cards_top
    for index, (heading, body) in enumerate(sections):
        x = diagram_x + index * (card_w + card_gap)
        draw.rounded_rectangle([x, cards_top, x + card_w, cards_top + card_h], radius=max(7, width // 180), fill="#fff9ef", outline="#ddd1bf", width=1)
        draw.text((x + 14, cards_top + 12), heading, fill=ink, font=h_font)
        draw.line((x + 14, cards_top + 40, x + card_w - 14, cards_top + 40), fill="#d5c8b8", width=1)
        draw.multiline_text((x + 14, cards_top + 52), wrap_text(draw, body, body_font, card_w - 28), fill="#2b2b2b", font=body_font, spacing=4)
    return img


def create_clean_reflow_target_unboxed_columns(width: int, height: int, changed: bool = False) -> Image.Image:
    img = Image.new("RGB", (width, height), "#f3f6f2")
    draw = ImageDraw.Draw(img)
    margin = int(width * 0.055)
    top = int(height * 0.055)
    ink = "#151719"
    muted = "#586166"
    line = "#b8c2b6"
    accent = "#0e7490"
    green = "#557a46"

    draw.rounded_rectangle(
        [margin, top, width - margin, height - top],
        radius=max(10, width // 110),
        fill="#fffef8",
        outline=line,
        width=2,
    )
    title_font = fixture_font(max(28, width // 32), bold=True)
    sub_font = fixture_font(max(14, width // 82))
    h_font = fixture_font(max(17, width // 66), bold=True)
    body_font = fixture_font(max(13, width // 90))
    tiny_font = fixture_font(max(10, width // 116))

    x0 = margin + int(width * 0.032)
    y0 = top + int(height * 0.032)
    draw.text((x0, y0), "Sketchapedia: Roman Colosseum", fill=ink, font=title_font)
    subtitle = (
        "Clean target variant: changed copy in open columns."
        if changed
        else "Clean target variant: open columns without card boxes."
    )
    draw.text((x0, y0 + int(height * 0.058)), subtitle, fill=muted, font=sub_font)

    content_top = top + int(height * 0.145)
    content_bottom = height - top - int(height * 0.055)
    left_x = x0
    left_w = int(width * 0.46)
    right_x = left_x + left_w + int(width * 0.055)
    right_w = width - margin - int(width * 0.035) - right_x
    draw.line((right_x - int(width * 0.025), content_top, right_x - int(width * 0.025), content_bottom), fill="#d7ddd4", width=2)

    draw.text((left_x, content_top), "Annotated Section Diagram", fill=ink, font=h_font)
    cx = left_x + int(left_w * 0.50)
    cy = content_top + int(height * 0.285)
    rx = int(left_w * 0.38)
    ry = int(height * 0.075)
    for offset, color in [(0, accent), (16, "#6aa6b8"), (32, green), (48, "#8d7a4f")]:
        draw.ellipse([cx - rx + offset, cy - ry + offset // 3, cx + rx - offset, cy + ry - offset // 3], outline=color, width=3)
    draw.rectangle([cx - 15, cy - 50, cx + 15, cy + 50], fill="#fffdf8", outline="#c9c0b2")
    for text, lx, ly in [
        ("upper seating", cx + rx - 10, cy - ry - 28),
        ("awnings", cx - rx - 68, cy - ry + 22),
        ("arena floor", cx + rx + 8, cy + 6),
        ("service level", cx - rx - 86, cy + ry - 18),
    ]:
        draw.text((lx, ly), text, fill=ink, font=tiny_font)
        draw.line((lx - 8, ly + 8, cx, cy), fill="#8aa4a1", width=1)

    summary_y = cy + int(height * 0.16)
    draw.text((left_x, summary_y), "Reading Checks", fill=ink, font=h_font)
    checks = (
        [
            "Changed copy must be painted cleanly.",
            "Old wording should not ghost into the target.",
            "Loop endpoints return quietly to the first page state.",
        ]
        if changed
        else [
            "Text remains crisp after layout changes.",
            "The diagram moves without becoming a pasted remnant.",
            "Loop endpoints return quietly to the first page state.",
        ]
    )
    for index, check in enumerate(checks):
        y = summary_y + int(height * 0.052) + index * int(height * 0.055)
        draw.text((left_x, y), f"{index + 1}.", fill=accent, font=h_font)
        draw.multiline_text((left_x + 38, y + 2), wrap_text(draw, check, body_font, left_w - 48), fill="#273035", font=body_font, spacing=4)

    sections = (
        [
            ("Construction", "Arches spread heavy loads across stacked corridors and vaults."),
            ("Crowd Flow", "Ramps, numbered gates, and passages moved thousands of visitors quickly."),
            ("Sunshade", "Canvas sails filtered glare while crews adjusted ropes above the stands."),
            ("Stonework", "Cut blocks, brick cores, and concrete vaults formed a resilient shell."),
        ]
        if changed
        else [
            ("Arena Floor", "Trapdoors, lifts, and service passages created sudden reveals during public spectacles."),
            ("Velarium", "A retractable awning system shaded spectators and required coordinated rope handling."),
            ("Seating", "Social order was encoded into the architecture through tiered, separated seating bands."),
            ("Materials", "Travertine, tuff, brick, and concrete carried both structure and ornament."),
        ]
    )
    col_gap = int(width * 0.025)
    col_w = (right_w - col_gap) // 2
    row_h = int((content_bottom - content_top - int(height * 0.07)) / 2)
    for index, (heading, body) in enumerate(sections):
        col = index % 2
        row = index // 2
        x = right_x + col * (col_w + col_gap)
        y = content_top + row * (row_h + int(height * 0.07))
        draw.text((x, y), heading, fill=ink, font=h_font)
        draw.line((x, y + int(height * 0.038), x + col_w, y + int(height * 0.038)), fill="#cfc8bb", width=1)
        draw.multiline_text((x, y + int(height * 0.055)), wrap_text(draw, body, body_font, col_w), fill="#292d2f", font=body_font, spacing=4)
    return img


def create_clean_reflow_target_callout_map(width: int, height: int, changed: bool = False) -> Image.Image:
    img = Image.new("RGB", (width, height), "#f7f4ef")
    draw = ImageDraw.Draw(img)
    margin = int(width * 0.055)
    top = int(height * 0.055)
    ink = "#171717"
    muted = "#5d6268"
    line = "#c8c0b5"
    accent = "#0d6f91"
    green = "#567c4f"

    draw.rounded_rectangle(
        [margin, top, width - margin, height - top],
        radius=max(10, width // 110),
        fill="#fffdf8",
        outline=line,
        width=2,
    )
    title_font = fixture_font(max(28, width // 32), bold=True)
    sub_font = fixture_font(max(14, width // 82))
    h_font = fixture_font(max(16, width // 70), bold=True)
    body_font = fixture_font(max(12, width // 96))
    tiny_font = fixture_font(max(10, width // 116))

    x0 = margin + int(width * 0.032)
    y0 = top + int(height * 0.032)
    draw.text((x0, y0), "Sketchapedia: Roman Colosseum", fill=ink, font=title_font)
    subtitle = (
        "Clean target variant: changed callout copy floats around the diagram."
        if changed
        else "Clean target variant: callout text floats around the diagram."
    )
    draw.text((x0, y0 + int(height * 0.058)), subtitle, fill=muted, font=sub_font)

    content_top = top + int(height * 0.155)
    content_bottom = height - top - int(height * 0.055)
    center_x = width // 2
    center_y = content_top + int((content_bottom - content_top) * 0.50)
    rx = int(width * 0.235)
    ry = int(height * 0.105)
    draw.text((center_x - int(width * 0.14), content_top), "Annotated Section Diagram", fill=ink, font=h_font)
    for offset, color in [(0, accent), (18, "#6aa6b8"), (36, green), (54, "#8d7a4f")]:
        draw.ellipse([center_x - rx + offset, center_y - ry + offset // 3, center_x + rx - offset, center_y + ry - offset // 3], outline=color, width=3)
    draw.rectangle([center_x - 18, center_y - 60, center_x + 18, center_y + 60], fill="#fffdf8", outline=line)

    callouts = (
        [
            ("Construction", "Arches spread heavy loads across corridors.", x0, content_top + int(height * 0.05), center_x - int(rx * 0.35), center_y),
            ("Crowd Flow", "Numbered gates moved visitors quickly.", width - x0 - int(width * 0.29), content_top + int(height * 0.05), center_x + int(rx * 0.25), center_y - int(ry * 0.55)),
            ("Sunshade", "Canvas sails filtered glare above the stands.", x0 + int(width * 0.02), content_bottom - int(height * 0.18), center_x - int(rx * 0.6), center_y + int(ry * 0.5)),
            ("Stonework", "Cut blocks and concrete vaults formed the shell.", width - x0 - int(width * 0.31), content_bottom - int(height * 0.18), center_x + int(rx * 0.7), center_y + int(ry * 0.2)),
        ]
        if changed
        else [
            ("Arena Floor", "Trapdoors and lifts created sudden reveals.", x0, content_top + int(height * 0.05), center_x - int(rx * 0.35), center_y),
            ("Velarium", "A retractable awning shaded spectators.", width - x0 - int(width * 0.29), content_top + int(height * 0.05), center_x + int(rx * 0.25), center_y - int(ry * 0.55)),
            ("Seating", "Tiered bands encoded social order.", x0 + int(width * 0.02), content_bottom - int(height * 0.18), center_x - int(rx * 0.6), center_y + int(ry * 0.5)),
            ("Materials", "Travertine, tuff, brick, and concrete carried the structure.", width - x0 - int(width * 0.31), content_bottom - int(height * 0.18), center_x + int(rx * 0.7), center_y + int(ry * 0.2)),
        ]
    )
    for heading, body, x, y, ax, ay in callouts:
        w = int(width * 0.27)
        draw.text((x, y), heading, fill=ink, font=h_font)
        draw.line((x, y + int(height * 0.037), x + w, y + int(height * 0.037)), fill="#d4c8b9", width=1)
        draw.multiline_text((x, y + int(height * 0.052)), wrap_text(draw, body, body_font, w), fill="#2d2d2d", font=body_font, spacing=4)
        elbow_x = x + w if x < center_x else x
        elbow_y = y + int(height * 0.07)
        draw.line((elbow_x, elbow_y, ax, ay), fill="#8aa4a1", width=1)

    labels = [
        ("upper seating", center_x + rx - 10, center_y - ry - 28),
        ("awnings", center_x - rx - 78, center_y - ry + 18),
        ("arena floor", center_x + rx + 12, center_y + 4),
        ("service level", center_x - rx - 96, center_y + ry - 18),
    ]
    for text, lx, ly in labels:
        draw.text((lx, ly), text, fill=ink, font=tiny_font)
        draw.line((lx - 8, ly + 8, center_x, center_y), fill="#8aa4a1", width=1)

    footer = (
        "Changed copy, labels, and diagram must resolve as one generated page state."
        if changed
        else "No card boxes. Text, labels, and diagram must resolve as one generated page state."
    )
    draw.text((x0, content_bottom - int(height * 0.02)), footer, fill=muted, font=tiny_font)
    return img


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
    target_mid = run_dir / "target-mid.png"
    clean_reference_modes = {"layout-clean-reflow", "clean-layout-reflow"}

    input_ocr = ocr(input_path)
    render_ocr = ocr(render_mid)
    target_mid_ocr = ocr(target_mid) if target_mid.exists() else ""
    use_target_reference = str(metrics.get("motion_mode", "")) in clean_reference_modes and bool(target_mid_ocr)
    reference_ocr = target_mid_ocr if use_target_reference else input_ocr
    reference_kind = "target-mid" if use_target_reference else "input"
    char_similarity = SequenceMatcher(None, normalize_text(reference_ocr), normalize_text(render_ocr)).ratio()
    token_similarity = token_f1(reference_ocr, render_ocr)
    layout_score = image_similarity(input_path, render_960)
    motion_delta = frame_diff(render_960, render_mid)
    loop_error = frame_diff(render_960, render_last)

    quality = {
        "run_id": metrics["run_id"],
        "input_ocr": input_ocr,
        "target_mid_ocr": target_mid_ocr,
        "ocr_reference": reference_kind,
        "render_mid_ocr": render_ocr,
        "ocr_similarity": token_similarity,
        "ocr_char_similarity": char_similarity,
        "layout_similarity": layout_score,
        "motion_delta": motion_delta,
        "loop_error": loop_error,
        "note": "C2-lite quality proxy: OCR token-F1 on mid-frame against the active reference, layout similarity on first frame, and low-res frame-diff motion/loop metrics.",
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
        def __init__(
            self,
            width: int,
            height: int,
            channels: int,
            hidden: int,
            freq_bands: int,
            time_bands: int,
            flow_scale: float,
            detail_channels: int = 0,
            detail_hidden: int | None = None,
            detail_scale: float = 0.0,
            detail_init_scale: float = 0.01,
            source_coord_features: bool = False,
            latent_neighborhood_mode: str = "none",
            latent_neighborhood_radius_px: float = 0.0,
            latent_sample_mode: str = "source",
            context_channels: int = 0,
            context_scale: float = 0.25,
            context_init_scale: float = 0.02,
            context_sample_mode: str = "source",
            decoder_mode: str = "single",
            target_branch_scale: float = 0.0,
            target_branch_hidden: int | None = None,
            rgb_skip_scale: float = 0.0,
            rgb_skip_mode: str = "source",
            rgb_skip_base_scale: float = 1.0,
            rgb_skip_gate_mode: str = "none",
            rgb_skip_gate_init: float = 0.5,
        ):
            super().__init__()
            self.width = width
            self.height = height
            self.freq_bands = freq_bands
            self.time_bands = time_bands
            self.flow_scale = flow_scale
            self.detail_channels = detail_channels
            self.detail_scale = detail_scale
            self.source_coord_features = source_coord_features
            decoder_mode = decoder_mode.lower().replace("_", "-")
            if decoder_mode in {"dual", "dual-target", "dual-residual", "target-residual"}:
                decoder_mode = "dual-residual"
            elif decoder_mode in {"dual-fused", "fused-dual", "dual-residual-fused", "fused-residual"}:
                decoder_mode = "dual-residual-fused"
            elif decoder_mode in {"dual-gate", "gated-dual", "target-gate"}:
                decoder_mode = "dual-gate"
            else:
                decoder_mode = "single"
            self.decoder_mode = decoder_mode
            self.target_branch_scale = float(target_branch_scale)
            self.target_branch_hidden = hidden if target_branch_hidden is None else max(8, int(target_branch_hidden))
            rgb_skip_mode = rgb_skip_mode.lower()
            if rgb_skip_mode in {"target", "dest", "destination", "output"}:
                rgb_skip_mode = "target"
            elif rgb_skip_mode != "both":
                rgb_skip_mode = "source"
            self.rgb_skip_scale = float(rgb_skip_scale)
            self.rgb_skip_mode = rgb_skip_mode
            self.rgb_skip_base_scale = float(rgb_skip_base_scale)
            rgb_skip_gate_mode = rgb_skip_gate_mode.lower().replace("_", "-")
            if rgb_skip_gate_mode not in {"none", "learned", "edge"}:
                rgb_skip_gate_mode = "none"
            self.rgb_skip_gate_mode = rgb_skip_gate_mode
            gate_init = min(0.98, max(0.02, float(rgb_skip_gate_init)))
            self.canvas = nn.Parameter(torch.randn(1, channels, height, width) * 0.02)
            self.rgb_canvas = (
                nn.Parameter(torch.zeros(1, 3, height, width))
                if self.rgb_skip_scale > 0.0
                else None
            )
            self.rgb_gate_canvas = (
                nn.Parameter(torch.full((1, 1, height, width), float(np.log(gate_init / (1.0 - gate_init)))))
                if self.rgb_skip_scale > 0.0 and self.rgb_skip_gate_mode != "none"
                else None
            )
            if context_channels > 0:
                context_sample_mode = context_sample_mode.lower()
                if context_sample_mode in {"target", "dest", "destination", "output"}:
                    context_sample_mode = "target"
                elif context_sample_mode != "both":
                    context_sample_mode = "source"
                self.context_sample_mode = context_sample_mode
                context_w = max(4, int(round(width * max(0.01, float(context_scale)))))
                context_h = max(4, int(round(height * max(0.01, float(context_scale)))))
                self.context_canvas = nn.Parameter(
                    torch.randn(1, context_channels, context_h, context_w) * context_init_scale
                )
            else:
                self.context_canvas = None
                self.context_sample_mode = "source"
            mode = latent_neighborhood_mode.lower()
            if mode not in {"none", "center", "cross", "grid"}:
                mode = "none"
            latent_sample_mode = latent_sample_mode.lower()
            if latent_sample_mode in {"target", "dest", "destination", "output"}:
                latent_sample_mode = "target"
            elif latent_sample_mode != "both":
                latent_sample_mode = "source"
            self.latent_sample_mode = latent_sample_mode
            radius_px = max(0.0, float(latent_neighborhood_radius_px))
            offsets = [(0.0, 0.0)]
            if radius_px > 0.0 and mode == "cross":
                rx = radius_px / max(1, width - 1)
                ry = radius_px / max(1, height - 1)
                offsets.extend([(rx, 0.0), (-rx, 0.0), (0.0, ry), (0.0, -ry)])
            elif radius_px > 0.0 and mode == "grid":
                rx = radius_px / max(1, width - 1)
                ry = radius_px / max(1, height - 1)
                offsets = [(dx, dy) for dy in (-ry, 0.0, ry) for dx in (-rx, 0.0, rx)]
            self.register_buffer("latent_offsets", torch.tensor(offsets, dtype=torch.float32), persistent=False)
            coord_dim = 2 + 4 * freq_bands
            time_dim = 1 + 2 * time_bands
            condition_dim = coord_dim + time_dim + (coord_dim if source_coord_features else 0)
            context_taps = 2 if context_channels > 0 and self.context_sample_mode == "both" else 1
            latent_taps = 2 if self.latent_sample_mode == "both" else 1
            latent_dim = (
                channels * len(offsets) * latent_taps
                + (context_channels * context_taps if context_channels > 0 else 0)
            )
            branch_latent_dim = channels * len(offsets) + (context_channels if context_channels > 0 else 0)
            self.flow = nn.Sequential(
                nn.Linear(coord_dim + time_dim, hidden),
                nn.SiLU(),
                nn.Linear(hidden, hidden),
                nn.SiLU(),
                nn.Linear(hidden, 2),
                nn.Tanh(),
            )
            if self.rgb_skip_scale > 0.0:
                nn.init.zeros_(self.flow[-2].weight)
                nn.init.zeros_(self.flow[-2].bias)

            def make_rgb_mlp(input_dim: int, mlp_hidden: int) -> nn.Sequential:
                return nn.Sequential(
                    nn.Linear(input_dim, mlp_hidden),
                    nn.SiLU(),
                    nn.Linear(mlp_hidden, mlp_hidden),
                    nn.SiLU(),
                    nn.Linear(mlp_hidden, 3),
                )

            if self.decoder_mode == "single":
                self.mlp = make_rgb_mlp(latent_dim + condition_dim, hidden)
                if self.rgb_skip_scale > 0.0:
                    nn.init.zeros_(self.mlp[-1].weight)
                    nn.init.zeros_(self.mlp[-1].bias)
                self.source_mlp = None
                self.target_mlp = None
                self.gate_mlp = None
            else:
                self.mlp = None
                target_input_dim = branch_latent_dim + condition_dim
                if self.decoder_mode == "dual-residual-fused":
                    target_input_dim = branch_latent_dim * 2 + condition_dim
                self.source_mlp = make_rgb_mlp(branch_latent_dim + condition_dim, hidden)
                self.target_mlp = make_rgb_mlp(target_input_dim, self.target_branch_hidden)
                self.gate_mlp = nn.Sequential(
                    nn.Linear(condition_dim, self.target_branch_hidden),
                    nn.SiLU(),
                    nn.Linear(self.target_branch_hidden, 1),
                )
                if self.decoder_mode in {"dual-residual", "dual-residual-fused"}:
                    nn.init.zeros_(self.target_mlp[-1].weight)
                    nn.init.zeros_(self.target_mlp[-1].bias)
                    nn.init.zeros_(self.gate_mlp[-1].weight)
                    nn.init.constant_(self.gate_mlp[-1].bias, -1.5)
            if detail_channels > 0 and detail_scale != 0.0:
                detail_hidden = hidden if detail_hidden is None else detail_hidden
                self.detail_canvas = nn.Parameter(torch.randn(1, detail_channels, height, width) * detail_init_scale)
                self.detail_mlp = nn.Sequential(
                    nn.Linear(detail_channels + condition_dim, detail_hidden),
                    nn.SiLU(),
                    nn.Linear(detail_hidden, detail_hidden),
                    nn.SiLU(),
                    nn.Linear(detail_hidden, 3),
                )
            else:
                self.detail_canvas = None
                self.detail_mlp = None

        def sample_one_canvas_features(self, coords: torch.Tensor) -> torch.Tensor:
            offsets = self.latent_offsets.to(device=coords.device, dtype=coords.dtype)
            expanded = (coords.unsqueeze(1) + offsets.unsqueeze(0)).clamp(0.0, 1.0)
            grid = expanded.mul(2.0).sub(1.0).reshape(1, -1, 1, 2)
            sampled = F.grid_sample(
                self.canvas,
                grid,
                mode="bilinear",
                padding_mode="border",
                align_corners=True,
            ).squeeze(0).squeeze(-1).transpose(0, 1)
            return sampled.reshape(coords.shape[0], offsets.shape[0], -1).reshape(coords.shape[0], -1)

        def sample_canvas_features(self, coords01: torch.Tensor, sample_coords: torch.Tensor) -> torch.Tensor:
            if self.latent_sample_mode == "target":
                return self.sample_one_canvas_features(coords01)
            if self.latent_sample_mode == "both":
                return torch.cat(
                    [self.sample_one_canvas_features(sample_coords), self.sample_one_canvas_features(coords01)],
                    dim=-1,
                )
            return self.sample_one_canvas_features(sample_coords)

        def sample_one_context(self, coords: torch.Tensor) -> torch.Tensor:
            grid = coords.clamp(0.0, 1.0).mul(2.0).sub(1.0).view(1, -1, 1, 2)
            return F.grid_sample(
                self.context_canvas,
                grid,
                mode="bilinear",
                padding_mode="border",
                align_corners=True,
            ).squeeze(0).squeeze(-1).transpose(0, 1)

        def sample_context_features(self, coords01: torch.Tensor, sample_coords: torch.Tensor) -> torch.Tensor | None:
            if self.context_canvas is None:
                return None
            if self.context_sample_mode == "target":
                return self.sample_one_context(coords01)
            if self.context_sample_mode == "both":
                return torch.cat([self.sample_one_context(sample_coords), self.sample_one_context(coords01)], dim=-1)
            return self.sample_one_context(sample_coords)

        def sample_branch_features(self, coords: torch.Tensor) -> torch.Tensor:
            sampled = self.sample_one_canvas_features(coords)
            if self.context_canvas is not None:
                sampled = torch.cat([sampled, self.sample_one_context(coords)], dim=-1)
            return sampled

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

        def decode_from_sample(
            self,
            coords01: torch.Tensor,
            t: torch.Tensor,
            sample_coords: torch.Tensor,
            coord_enc: torch.Tensor | None = None,
            time_enc: torch.Tensor | None = None,
        ) -> torch.Tensor:
            if coord_enc is None:
                coord_enc = self.encode_coords(coords01)
            if time_enc is None:
                time_enc = self.encode_time(t)
            condition_parts = [coord_enc]
            if self.source_coord_features:
                condition_parts.append(self.encode_coords(sample_coords))
            condition_parts.append(time_enc)
            condition = torch.cat(condition_parts, dim=-1)
            grid = sample_coords.mul(2.0).sub(1.0).view(1, -1, 1, 2)
            if self.decoder_mode == "single":
                sampled = self.sample_canvas_features(coords01, sample_coords)
                context_sampled = self.sample_context_features(coords01, sample_coords)
                if context_sampled is not None:
                    sampled = torch.cat([sampled, context_sampled], dim=-1)
                logits = self.mlp(torch.cat([sampled, condition], dim=-1))
            else:
                source_sampled = self.sample_branch_features(sample_coords)
                target_sampled = self.sample_branch_features(coords01)
                source_logits = self.source_mlp(torch.cat([source_sampled, condition], dim=-1))
                target_input = torch.cat([target_sampled, condition], dim=-1)
                if self.decoder_mode == "dual-residual-fused":
                    target_input = torch.cat([source_sampled, target_sampled, condition], dim=-1)
                target_logits = self.target_mlp(target_input)
                gate = torch.sigmoid(self.gate_mlp(condition))
                if self.decoder_mode == "dual-gate":
                    logits = source_logits * (1.0 - gate) + target_logits * gate
                else:
                    logits = source_logits + self.target_branch_scale * gate * torch.tanh(target_logits)
            if self.detail_canvas is not None and self.detail_mlp is not None:
                detail_sampled = F.grid_sample(
                    self.detail_canvas,
                    grid,
                    mode="bilinear",
                    padding_mode="border",
                    align_corners=True,
                ).squeeze(0).squeeze(-1).transpose(0, 1)
                detail_logits = self.detail_mlp(torch.cat([detail_sampled, condition], dim=-1))
                logits = logits + self.detail_scale * torch.tanh(detail_logits)
            if self.rgb_canvas is not None:
                if self.rgb_skip_mode == "target":
                    rgb_coords = coords01
                elif self.rgb_skip_mode == "both":
                    rgb_coords = (coords01 + sample_coords) * 0.5
                else:
                    rgb_coords = sample_coords
                rgb_grid = rgb_coords.mul(2.0).sub(1.0).view(1, -1, 1, 2)
                base_logits = F.grid_sample(
                    self.rgb_canvas,
                    rgb_grid,
                    mode="bilinear",
                    padding_mode="border",
                    align_corners=True,
                ).squeeze(0).squeeze(-1).transpose(0, 1)
                if self.rgb_gate_canvas is not None:
                    gate = torch.sigmoid(
                        F.grid_sample(
                            self.rgb_gate_canvas,
                            rgb_grid,
                            mode="bilinear",
                            padding_mode="border",
                            align_corners=True,
                        ).squeeze(0).squeeze(-1).transpose(0, 1)
                    )
                else:
                    gate = 1.0
                logits = gate * self.rgb_skip_base_scale * base_logits + self.rgb_skip_scale * torch.tanh(logits)
            return torch.sigmoid(logits)

        def forward_with_warp(self, coords01: torch.Tensor, t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            coord_enc = self.encode_coords(coords01)
            time_enc = self.encode_time(t)
            flow = self.flow(torch.cat([coord_enc, time_enc], dim=-1)) * self.flow_scale
            sample_coords = (coords01 + flow).clamp(0.0, 1.0)
            return self.decode_from_sample(coords01, t, sample_coords, coord_enc, time_enc), sample_coords

        def forward_with_source_coords(
            self,
            coords01: torch.Tensor,
            t: torch.Tensor,
            sample_coords: torch.Tensor,
        ) -> torch.Tensor:
            return self.decode_from_sample(coords01, t, sample_coords.clamp(0.0, 1.0))

        def forward(self, coords01: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
            return self.forward_with_warp(coords01, t)[0]

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

    independent_layout_regions = [
        (0.04, 0.035, 0.96, 0.17, 0.85, -0.28, 0.35, -0.18, 1, 0.00),
        (0.055, 0.205, 0.505, 0.58, -0.95, 0.80, -0.70, 0.48, 2, 0.16),
        (0.535, 0.205, 0.955, 0.57, 1.05, 0.58, 0.62, -0.42, 1, 0.34),
        (0.06, 0.61, 0.52, 0.935, -0.65, -0.85, 0.48, 0.58, 3, 0.08),
        (0.54, 0.60, 0.95, 0.93, 0.75, -0.62, -0.50, 0.52, 2, 0.42),
    ]
    layout_reflow_regions = [
        ((0.035, 0.025, 0.965, 0.135), (0.055, 0.035, 0.945, 0.125)),
        ((0.040, 0.135, 0.495, 0.300), (0.055, 0.145, 0.455, 0.295)),
        ((0.505, 0.135, 0.965, 0.300), (0.500, 0.145, 0.945, 0.295)),
        ((0.040, 0.300, 0.495, 0.420), (0.055, 0.755, 0.455, 0.910)),
        ((0.505, 0.300, 0.965, 0.420), (0.500, 0.755, 0.945, 0.910)),
        ((0.040, 0.420, 0.635, 0.925), (0.070, 0.335, 0.650, 0.735)),
        ((0.635, 0.420, 0.965, 0.925), (0.665, 0.335, 0.945, 0.735)),
    ]
    independent_hard_layout_modes = {"independent-regions", "region-dance"}
    independent_translate_layout_modes = {"independent-translate", "region-translate"}
    independent_field_layout_modes = {"independent-field", "region-field"} | independent_translate_layout_modes
    independent_layout_modes = independent_hard_layout_modes | independent_field_layout_modes
    independent_sprite_motion_modes = {"independent-sprite-translate", "region-sprite-translate"}
    clean_layout_motion_modes = {"layout-clean-reflow", "clean-layout-reflow"}
    layout_reflow_motion_modes = {"layout-reflow", "sprite-layout-reflow"} | clean_layout_motion_modes

    def apply_independent_region_field(
        coords: torch.Tensor,
        t_value: torch.Tensor | float,
        strength: float,
        pan: float,
    ) -> torch.Tensor:
        x = coords[:, 0:1]
        y = coords[:, 1:2]
        t_col = t_value if torch.is_tensor(t_value) else torch.full((coords.shape[0], 1), float(t_value), device=coords.device)
        envelope = torch.sin(t_col * torch.pi).square()
        weighted_delta = torch.zeros_like(coords)
        total_weight = torch.zeros_like(x)
        for x0, y0, x1, y1, pan_x_mul, pan_y_mul, scale_x_mul, scale_y_mul, speed, phase in independent_layout_regions:
            cx = (x0 + x1) * 0.5
            cy = (y0 + y1) * 0.5
            source_w = x1 - x0
            source_h = y1 - y0
            norm_x = (x - cx) / max(1e-6, source_w * 0.55)
            norm_y = (y - cy) / max(1e-6, source_h * 0.55)
            weight = torch.exp(-2.35 * (norm_x.square() + norm_y.square()))
            angle = 2.0 * torch.pi * (float(speed) * t_col + phase)
            pan_x = pan * pan_x_mul * envelope * torch.sin(angle)
            pan_y = pan * pan_y_mul * envelope * torch.cos(angle + torch.pi * 0.23)
            scale_x = (
                1.0 + strength * scale_x_mul * envelope * torch.sin(angle + torch.pi * 0.31)
            ).clamp(0.55, 1.50)
            scale_y = (
                1.0 + strength * scale_y_mul * envelope * torch.cos(angle + torch.pi * 0.19)
            ).clamp(0.55, 1.50)
            local_x = cx + (x - cx - pan_x) / scale_x
            local_y = cy + (y - cy - pan_y) / scale_y
            local_coords = torch.cat([local_x, local_y], dim=-1)
            weighted_delta += weight * (local_coords - coords)
            total_weight += weight
        influence = total_weight.clamp(0.0, 1.0)
        delta = weighted_delta / total_weight.clamp_min(1e-6)
        return (coords + delta * influence).clamp(0.0, 1.0)

    def target_coords_for_motion(coords: torch.Tensor, t: torch.Tensor, amp: float, mode: str) -> torch.Tensor:
        phase = t * 2.0 * torch.pi
        x = coords[:, 0:1]
        y = coords[:, 1:2]
        if mode in {"static", "identity", "none"}:
            return coords
        if mode in independent_sprite_motion_modes or mode in layout_reflow_motion_modes:
            return coords
        if mode in independent_translate_layout_modes:
            return apply_independent_region_field(coords, t, 0.0, amp)
        if mode in {"independent-field", "region-field"}:
            return apply_independent_region_field(coords, t, amp, amp * 0.24)
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

    def smooth_box_alpha(coords01: torch.Tensor, x0: float, y0: float, x1: float, y1: float, edge: float) -> torch.Tensor:
        x = coords01[:, 0:1]
        y = coords01[:, 1:2]
        left = torch.sigmoid((x - x0) / edge)
        right = torch.sigmoid((x1 - x) / edge)
        top = torch.sigmoid((y - y0) / edge)
        bottom = torch.sigmoid((y1 - y) / edge)
        return (left * right * top * bottom).clamp(0.0, 1.0)

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
    seed = int(config.get("seed", 0))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cuda.matmul.allow_tf32 = True
    train_w, train_h = parse_resolution(config["train_resolution"])
    steps = int(config["steps"])
    batch_size = int(config["batch_size"])
    flow_scale = float(config["flow_scale"])
    base_lr = float(config["lr"])
    lr_schedule = str(config.get("lr_schedule", "constant"))
    min_lr_ratio = float(config.get("min_lr_ratio", 0.1))
    grad_clip = float(config.get("grad_clip", 0.0))
    l1_loss_weight = float(config.get("l1_loss_weight", 0.0))
    gradient_loss_weight = float(config.get("gradient_loss_weight", 0.0))
    gradient_loss_ratio = float(config.get("gradient_loss_ratio", 0.125))
    gradient_loss_offset_px = float(config.get("gradient_loss_offset_px", 1.0))
    motion_mode = str(config.get("motion_mode", "jiggle"))
    motion_strength = float(config.get("motion_strength", flow_scale))
    clean_target_variant = str(config.get("clean_target_variant", "diagram-left"))
    video_viewport_mode = str(config.get("video_viewport_mode", "static"))
    viewport_zoom = float(config.get("viewport_zoom", 0.0))
    viewport_pan = float(config.get("viewport_pan", 0.0))
    video_layout_mode = str(config.get("video_layout_mode", "none"))
    layout_transform_strength = float(config.get("layout_transform_strength", 0.0))
    layout_transform_pan = float(config.get("layout_transform_pan", 0.0))
    layout_supersample = float(config.get("layout_supersample", 1.0))
    element_scale_ratio = float(config.get("element_scale_ratio", 0.25))
    element_anchor_padding = int(config.get("element_anchor_padding", 3))
    element_mask_mode = str(config.get("element_mask_mode", "rectangle"))
    element_anchor_mode = str(config.get("element_anchor_mode", "line"))
    element_render_mode = str(config.get("element_render_mode", "sequential"))
    edge_sample_ratio = float(config.get("edge_sample_ratio", 0.0))
    edge_loss_weight = float(config.get("edge_loss_weight", 0.0))
    text_box_sample_ratio = float(config.get("text_box_sample_ratio", 0.0))
    text_box_loss_weight = float(config.get("text_box_loss_weight", 0.0))
    text_box_padding = int(config.get("text_box_padding", 0))
    layout_target_sampling = bool(int(config.get("layout_target_sampling", 0)))
    layout_target_weighting = bool(int(config.get("layout_target_weighting", 0)))
    layout_target_sampling_ratio = float(config.get("layout_target_sampling_ratio", 1.0))
    layout_target_mid_sampling_ratio = float(config.get("layout_target_mid_sampling_ratio", 0.0))
    layout_target_mid_time_width = float(config.get("layout_target_mid_time_width", config.get("layout_mid_time_width", 0.24)))
    layout_target_pair_ratio = float(config.get("layout_target_pair_ratio", 0.0))
    layout_target_pair_weight = float(config.get("layout_target_pair_weight", 1.0))
    layout_mid_time_ratio = float(config.get("layout_mid_time_ratio", 0.0))
    layout_mid_time_width = float(config.get("layout_mid_time_width", 0.24))
    layout_flow_loss_weight = float(config.get("layout_flow_loss_weight", 0.0))
    layout_oracle_flow = bool(int(config.get("layout_oracle_flow", 0)))
    layout_motion_curriculum_ratio = float(config.get("layout_motion_curriculum_ratio", 0.0))
    layout_motion_curriculum_start = float(config.get("layout_motion_curriculum_start", 0.0))
    layout_endpoint_ratio = float(config.get("layout_endpoint_ratio", 0.0))
    layout_endpoint_target_ratio = float(config.get("layout_endpoint_target_ratio", 0.5))
    detail_channels = int(config.get("detail_channels", 0))
    detail_hidden = int(config.get("detail_hidden", config["hidden"]))
    detail_scale = float(config.get("detail_scale", 0.0))
    detail_init_scale = float(config.get("detail_init_scale", 0.01))
    source_coord_features = bool(int(config.get("source_coord_features", 0)))
    latent_neighborhood_mode = str(config.get("latent_neighborhood_mode", "none"))
    latent_neighborhood_radius_px = float(config.get("latent_neighborhood_radius_px", 0.0))
    latent_sample_mode = str(config.get("latent_sample_mode", "source"))
    context_channels = int(config.get("context_channels", 0))
    context_scale = float(config.get("context_scale", 0.25))
    context_init_scale = float(config.get("context_init_scale", 0.02))
    context_sample_mode = str(config.get("context_sample_mode", "source"))
    decoder_mode = str(config.get("decoder_mode", "single"))
    target_branch_scale = float(config.get("target_branch_scale", 0.0))
    target_branch_hidden = int(config.get("target_branch_hidden", config["hidden"]))
    rgb_skip_scale = float(config.get("rgb_skip_scale", 0.0))
    rgb_skip_mode = str(config.get("rgb_skip_mode", "source"))
    rgb_skip_base_scale = float(config.get("rgb_skip_base_scale", 1.0))
    rgb_skip_gate_mode = str(config.get("rgb_skip_gate_mode", "none"))
    rgb_skip_gate_init = float(config.get("rgb_skip_gate_init", 0.5))

    sobel_x = torch.tensor(
        [[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]],
        device=device,
    ).view(1, 1, 3, 3)
    sobel_y = torch.tensor(
        [[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]],
        device=device,
    ).view(1, 1, 3, 3)

    def glyph_features(image_hwc: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        luminance_local = image_hwc.mean(dim=-1)
        gray_local = luminance_local.unsqueeze(0).unsqueeze(0)
        edge_local = torch.sqrt(
            F.conv2d(gray_local, sobel_x, padding=1).square() + F.conv2d(gray_local, sobel_y, padding=1).square()
        )
        edge_local = edge_local.squeeze(0).squeeze(0)
        edge_local = edge_local / edge_local.max().clamp_min(1e-6)
        dark_local = (1.0 - luminance_local).clamp(0.0, 1.0)
        glyph_score_local = (0.10 + edge_local + 0.75 * edge_local * dark_local + 0.25 * dark_local).clamp_min(1e-6)
        glyph_prob_local = glyph_score_local.flatten()
        glyph_prob_local = glyph_prob_local / glyph_prob_local.sum().clamp_min(1e-6)
        glyph_weight_local = (glyph_score_local / glyph_score_local.max().clamp_min(1e-6)).unsqueeze(0).unsqueeze(0)
        return luminance_local, edge_local, dark_local, glyph_prob_local, glyph_weight_local

    source = Image.open(io.BytesIO(input_png)).convert("RGB").resize((train_w, train_h), Image.Resampling.LANCZOS)
    target = torch.from_numpy(np.asarray(source, dtype=np.float32) / 255.0).to(device)
    target_chw = target.permute(2, 0, 1).unsqueeze(0)
    clean_target = None
    clean_target_chw = None
    clean_glyph_prob = None
    clean_glyph_weight_chw = None
    if motion_mode in clean_layout_motion_modes:
        clean_image = create_clean_reflow_target(train_w, train_h, clean_target_variant)
        clean_target = torch.from_numpy(np.asarray(clean_image, dtype=np.float32) / 255.0).to(device)
        clean_target_chw = clean_target.permute(2, 0, 1).unsqueeze(0)

    luminance, edge, dark, glyph_prob, glyph_weight_chw = glyph_features(target)
    if clean_target is not None:
        _clean_luminance, _clean_edge, _clean_dark, clean_glyph_prob, clean_glyph_weight_chw = glyph_features(clean_target)
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

    def sample_independent_sprite_translation(coords01: torch.Tensor, t_col: torch.Tensor, pan: float) -> torch.Tensor:
        canvas = sample_target(target_chw, coords01)
        white = torch.ones_like(canvas)
        edge = 0.006
        envelope = torch.sin(t_col * torch.pi).square()

        # Clear original source regions first, then composite translated region content back in.
        for x0, y0, x1, y1, *_rest in independent_layout_regions:
            alpha = smooth_box_alpha(coords01, x0, y0, x1, y1, edge)
            canvas = canvas * (1.0 - alpha) + white * alpha

        x = coords01[:, 0:1]
        y = coords01[:, 1:2]
        for x0, y0, x1, y1, pan_x_mul, pan_y_mul, _scale_x_mul, _scale_y_mul, speed, phase in independent_layout_regions:
            angle = 2.0 * torch.pi * (float(speed) * t_col + phase)
            pan_x = pan * pan_x_mul * envelope * torch.sin(angle)
            pan_y = pan * pan_y_mul * envelope * torch.cos(angle + torch.pi * 0.23)
            moved_x0 = torch.full_like(pan_x, x0) + pan_x
            moved_y0 = torch.full_like(pan_y, y0) + pan_y
            moved_x1 = torch.full_like(pan_x, x1) + pan_x
            moved_y1 = torch.full_like(pan_y, y1) + pan_y
            alpha = (
                torch.sigmoid((x - moved_x0) / edge)
                * torch.sigmoid((moved_x1 - x) / edge)
                * torch.sigmoid((y - moved_y0) / edge)
                * torch.sigmoid((moved_y1 - y) / edge)
            ).clamp(0.0, 1.0)
            source_coords = torch.cat([x - pan_x, y - pan_y], dim=-1)
            patch = sample_target(target_chw, source_coords)
            canvas = patch * alpha + canvas * (1.0 - alpha)
        return canvas

    def forward_layout_reflow_coords(coords01: torch.Tensor, t_col: torch.Tensor, amount: float) -> torch.Tensor:
        out = coords01.clone()
        assigned = torch.zeros((coords01.shape[0], 1), device=coords01.device, dtype=torch.bool)
        progress = torch.sin(t_col * torch.pi).square().clamp(0.0, 1.0) * amount
        x = coords01[:, 0:1]
        y = coords01[:, 1:2]

        for source_box, target_box in layout_reflow_regions:
            sx0, sy0, sx1, sy1 = source_box
            tx0, ty0, tx1, ty1 = target_box
            dx0 = sx0 + (tx0 - sx0) * progress
            dy0 = sy0 + (ty0 - sy0) * progress
            dx1 = sx1 + (tx1 - sx1) * progress
            dy1 = sy1 + (ty1 - sy1) * progress
            in_box = (x >= sx0) & (x <= sx1) & (y >= sy0) & (y <= sy1) & ~assigned
            dest_x = dx0 + (x - sx0) * ((dx1 - dx0) / max(1e-6, sx1 - sx0))
            dest_y = dy0 + (y - sy0) * ((dy1 - dy0) / max(1e-6, sy1 - sy0))
            out = torch.where(in_box, torch.cat([dest_x, dest_y], dim=-1), out)
            assigned = assigned | in_box
        return out.clamp(0.0, 1.0)

    def sample_layout_reflow_from(
        source_chw: torch.Tensor,
        coords01: torch.Tensor,
        t_col: torch.Tensor,
        amount: float,
        background_value: float,
    ) -> torch.Tensor:
        channels_local = int(source_chw.shape[1])
        canvas = torch.full((coords01.shape[0], channels_local), float(background_value), device=coords01.device)
        edge = 0.006
        progress = torch.sin(t_col * torch.pi).square().clamp(0.0, 1.0) * amount
        x = coords01[:, 0:1]
        y = coords01[:, 1:2]

        for source_box, target_box in layout_reflow_regions:
            sx0, sy0, sx1, sy1 = source_box
            tx0, ty0, tx1, ty1 = target_box
            dx0 = sx0 + (tx0 - sx0) * progress
            dy0 = sy0 + (ty0 - sy0) * progress
            dx1 = sx1 + (tx1 - sx1) * progress
            dy1 = sy1 + (ty1 - sy1) * progress
            alpha = (
                torch.sigmoid((x - dx0) / edge)
                * torch.sigmoid((dx1 - x) / edge)
                * torch.sigmoid((y - dy0) / edge)
                * torch.sigmoid((dy1 - y) / edge)
            ).clamp(0.0, 1.0)
            source_x = sx0 + (x - dx0) * ((sx1 - sx0) / (dx1 - dx0).clamp_min(1e-6))
            source_y = sy0 + (y - dy0) * ((sy1 - sy0) / (dy1 - dy0).clamp_min(1e-6))
            patch = sample_target(source_chw, torch.cat([source_x, source_y], dim=-1))
            canvas = patch * alpha + canvas * (1.0 - alpha)
        return canvas

    def sample_layout_reflow(coords01: torch.Tensor, t_col: torch.Tensor, amount: float) -> torch.Tensor:
        return sample_layout_reflow_from(target_chw, coords01, t_col, amount, 1.0)

    def clean_progress(t_col: torch.Tensor, amount: float) -> torch.Tensor:
        return (torch.sin(t_col * torch.pi).square().clamp(0.0, 1.0) * amount).clamp(0.0, 1.0)

    def sample_clean_layout_reflow_from(
        source_chw: torch.Tensor,
        target_clean_chw: torch.Tensor,
        coords01: torch.Tensor,
        t_col: torch.Tensor,
        amount: float,
    ) -> torch.Tensor:
        progress = clean_progress(t_col, amount)
        source_sample = sample_target(source_chw, coords01)
        target_sample = sample_target(target_clean_chw, coords01)
        return source_sample * (1.0 - progress) + target_sample * progress

    def sample_clean_layout_reflow(coords01: torch.Tensor, t_col: torch.Tensor, amount: float) -> torch.Tensor:
        if clean_target_chw is None:
            return sample_layout_reflow(coords01, t_col, amount)
        return sample_clean_layout_reflow_from(target_chw, clean_target_chw, coords01, t_col, amount)

    def inverse_layout_reflow_coords(coords01: torch.Tensor, t_col: torch.Tensor, amount: float) -> tuple[torch.Tensor, torch.Tensor]:
        source_coords = coords01.clone()
        content_alpha = torch.zeros((coords01.shape[0], 1), device=coords01.device)
        edge = 0.006
        progress = torch.sin(t_col * torch.pi).square().clamp(0.0, 1.0) * amount
        x = coords01[:, 0:1]
        y = coords01[:, 1:2]

        for source_box, target_box in layout_reflow_regions:
            sx0, sy0, sx1, sy1 = source_box
            tx0, ty0, tx1, ty1 = target_box
            dx0 = sx0 + (tx0 - sx0) * progress
            dy0 = sy0 + (ty0 - sy0) * progress
            dx1 = sx1 + (tx1 - sx1) * progress
            dy1 = sy1 + (ty1 - sy1) * progress
            alpha = (
                torch.sigmoid((x - dx0) / edge)
                * torch.sigmoid((dx1 - x) / edge)
                * torch.sigmoid((y - dy0) / edge)
                * torch.sigmoid((dy1 - y) / edge)
            ).clamp(0.0, 1.0)
            source_x = sx0 + (x - dx0) * ((sx1 - sx0) / (dx1 - dx0).clamp_min(1e-6))
            source_y = sy0 + (y - dy0) * ((sy1 - sy0) / (dy1 - dy0).clamp_min(1e-6))
            mapped = torch.cat([source_x, source_y], dim=-1).clamp(0.0, 1.0)
            source_coords = mapped * alpha + source_coords * (1.0 - alpha)
            content_alpha = alpha + content_alpha * (1.0 - alpha)
        return source_coords.clamp(0.0, 1.0), content_alpha.clamp(0.0, 1.0)

    layout_target_mid_prob: torch.Tensor | None = None
    if motion_mode in layout_reflow_motion_modes and layout_target_mid_sampling_ratio > 0.0:
        if motion_mode in clean_layout_motion_modes and clean_glyph_prob is not None:
            layout_target_mid_prob = clean_glyph_prob
        else:
            with torch.no_grad():
                grid_y, grid_x = torch.meshgrid(
                    torch.linspace(0.0, 1.0, train_h, device=device),
                    torch.linspace(0.0, 1.0, train_w, device=device),
                    indexing="ij",
                )
                mid_coords = torch.stack([grid_x.flatten(), grid_y.flatten()], dim=-1)
                mid_t = torch.full((mid_coords.shape[0], 1), 0.5, device=device)
                mid_glyph = sample_layout_reflow_from(glyph_weight_chw, mid_coords, mid_t, motion_strength, 0.0).squeeze(-1)
                mid_text = sample_layout_reflow_from(text_weight_chw, mid_coords, mid_t, motion_strength, 0.0).squeeze(-1)
                mid_score = (mid_glyph + 1.75 * mid_text).clamp_min(1e-6)
                layout_target_mid_prob = mid_score / mid_score.sum().clamp_min(1e-6)

    model = TimeCanvas(
        width=train_w,
        height=train_h,
        channels=int(config["channels"]),
        hidden=int(config["hidden"]),
        freq_bands=int(config["freq_bands"]),
        time_bands=int(config["time_bands"]),
        flow_scale=flow_scale * 1.4,
        detail_channels=detail_channels,
        detail_hidden=detail_hidden,
        detail_scale=detail_scale,
        detail_init_scale=detail_init_scale,
        source_coord_features=source_coord_features,
        latent_neighborhood_mode=latent_neighborhood_mode,
        latent_neighborhood_radius_px=latent_neighborhood_radius_px,
        latent_sample_mode=latent_sample_mode,
        context_channels=context_channels,
        context_scale=context_scale,
        context_init_scale=context_init_scale,
        context_sample_mode=context_sample_mode,
        decoder_mode=decoder_mode,
        target_branch_scale=target_branch_scale,
        target_branch_hidden=target_branch_hidden,
        rgb_skip_scale=rgb_skip_scale,
        rgb_skip_mode=rgb_skip_mode,
        rgb_skip_base_scale=rgb_skip_base_scale,
        rgb_skip_gate_mode=rgb_skip_gate_mode,
        rgb_skip_gate_init=rgb_skip_gate_init,
    ).to(device)
    if model.rgb_canvas is not None:
        with torch.no_grad():
            model.rgb_canvas.copy_(torch.logit(target_chw.clamp(1e-4, 1.0 - 1e-4)))
    if model.rgb_gate_canvas is not None and model.rgb_skip_gate_mode == "edge":
        with torch.no_grad():
            edge_gate = (0.08 + 0.82 * glyph_weight_chw / glyph_weight_chw.max().clamp_min(1e-6)).clamp(0.02, 0.98)
            model.rgb_gate_canvas.copy_(torch.logit(edge_gate))

    optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=0.0)
    compile_start = perf_counter()
    losses = []

    def training_motion_strength(step: int) -> float:
        if motion_mode not in layout_reflow_motion_modes or layout_motion_curriculum_ratio <= 0.0:
            return motion_strength
        ramp_steps = max(1, int(steps * layout_motion_curriculum_ratio))
        progress = min(1.0, step / ramp_steps)
        smooth = progress * progress * (3.0 - 2.0 * progress)
        start = max(0.0, min(1.0, layout_motion_curriculum_start))
        return motion_strength * (start + (1.0 - start) * smooth)

    def truth_for_coords(
        sample_coords: torch.Tensor,
        sample_t: torch.Tensor,
        amount: float,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        sample_target_coords = target_coords_for_motion(sample_coords, sample_t, amount, motion_mode)
        if motion_mode in independent_sprite_motion_modes:
            sample_truth = sample_independent_sprite_translation(sample_coords, sample_t, amount)
        elif motion_mode in clean_layout_motion_modes:
            sample_truth = sample_clean_layout_reflow(sample_coords, sample_t, amount)
        elif motion_mode in layout_reflow_motion_modes:
            sample_truth = sample_layout_reflow(sample_coords, sample_t, amount)
        else:
            sample_truth = sample_target(target_chw, sample_target_coords)
        return sample_truth, sample_target_coords

    for step in range(steps):
        step_motion_strength = training_motion_strength(step)
        if lr_schedule == "cosine":
            progress = min(1.0, step / max(1, steps - 1))
            lr_scale = min_lr_ratio + 0.5 * (1.0 - min_lr_ratio) * (1.0 + float(np.cos(np.pi * progress)))
            for group in optimizer.param_groups:
                group["lr"] = base_lr * lr_scale
        text_count = max(0, min(batch_size, int(batch_size * text_box_sample_ratio))) if text_has_pixels else 0
        remaining = batch_size - text_count
        edge_count = max(0, min(remaining, int(batch_size * edge_sample_ratio)))
        uniform_count = batch_size - text_count - edge_count
        idx_parts = []
        source_focus_parts = []
        if uniform_count:
            idx_parts.append(torch.randint(0, train_w * train_h, (uniform_count,), device=device))
            source_focus_parts.append(torch.zeros((uniform_count,), device=device, dtype=torch.bool))
        if edge_count:
            idx_parts.append(torch.multinomial(glyph_prob, edge_count, replacement=True))
            source_focus_parts.append(torch.ones((edge_count,), device=device, dtype=torch.bool))
        if text_count:
            idx_parts.append(torch.multinomial(text_prob, text_count, replacement=True))
            source_focus_parts.append(torch.ones((text_count,), device=device, dtype=torch.bool))
        idx = torch.cat(idx_parts, dim=0)
        source_focus = torch.cat(source_focus_parts, dim=0)
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
        if motion_mode in layout_reflow_motion_modes and layout_mid_time_ratio > 0.0:
            mid_count = max(0, min(batch_size, int(batch_size * layout_mid_time_ratio)))
            if mid_count:
                mid_idx = torch.randperm(batch_size, device=device)[:mid_count]
                mid_t = 0.5 + (torch.rand((mid_count, 1), device=device) - 0.5) * layout_mid_time_width
                t[mid_idx] = mid_t.clamp(0.0, 1.0)
        if motion_mode in layout_reflow_motion_modes and layout_endpoint_ratio > 0.0:
            endpoint_count = max(0, min(batch_size, int(batch_size * layout_endpoint_ratio)))
            if endpoint_count:
                endpoint_idx = torch.randperm(batch_size, device=device)[:endpoint_count]
                target_count = max(0, min(endpoint_count, int(endpoint_count * layout_endpoint_target_ratio)))
                if target_count:
                    t[endpoint_idx[:target_count]] = 0.5
                if target_count < endpoint_count:
                    t[endpoint_idx[target_count:]] = 0.0
        source_coords_for_pairs = coords
        source_focus_for_pairs = source_focus
        if motion_mode in layout_reflow_motion_modes and layout_target_sampling:
            focus = source_focus
            if layout_target_sampling_ratio < 1.0:
                focus = focus & (torch.rand((batch_size,), device=device) < layout_target_sampling_ratio)
            if motion_mode in clean_layout_motion_modes and clean_glyph_prob is not None:
                focus_idx = torch.nonzero(focus, as_tuple=False).squeeze(-1)
                if focus_idx.numel():
                    target_pixel_idx = torch.multinomial(clean_glyph_prob, int(focus_idx.numel()), replacement=True)
                    target_ys = torch.div(target_pixel_idx, train_w, rounding_mode="floor")
                    target_xs = target_pixel_idx - target_ys * train_w
                    coords[focus_idx] = torch.stack(
                        [
                            target_xs.float() / max(1, train_w - 1),
                            target_ys.float() / max(1, train_h - 1),
                        ],
                        dim=-1,
                    )
            else:
                moved_coords = forward_layout_reflow_coords(coords, t, step_motion_strength)
                coords = torch.where(focus.unsqueeze(-1), moved_coords, coords)
        if (
            motion_mode in layout_reflow_motion_modes
            and layout_target_mid_prob is not None
            and layout_target_mid_sampling_ratio > 0.0
        ):
            mid_count = max(0, min(batch_size, int(batch_size * layout_target_mid_sampling_ratio)))
            if mid_count:
                mid_slot_idx = torch.randperm(batch_size, device=device)[:mid_count]
                mid_pixel_idx = torch.multinomial(layout_target_mid_prob, mid_count, replacement=True)
                mid_ys = torch.div(mid_pixel_idx, train_w, rounding_mode="floor")
                mid_xs = mid_pixel_idx - mid_ys * train_w
                coords[mid_slot_idx] = torch.stack(
                    [
                        mid_xs.float() / max(1, train_w - 1),
                        mid_ys.float() / max(1, train_h - 1),
                    ],
                    dim=-1,
                )
                mid_time = 0.5 + (torch.rand((mid_count, 1), device=device) - 0.5) * layout_target_mid_time_width
                t[mid_slot_idx] = mid_time.clamp(0.0, 1.0)
        truth, target_coords = truth_for_coords(coords, t, step_motion_strength)
        if motion_mode in layout_reflow_motion_modes and layout_oracle_flow:
            oracle_source_coords, _oracle_alpha = inverse_layout_reflow_coords(coords, t, step_motion_strength)
            pred = model.forward_with_source_coords(coords, t, oracle_source_coords)
            pred_source_coords = None
        elif motion_mode in layout_reflow_motion_modes and layout_flow_loss_weight > 0.0:
            pred, pred_source_coords = model.forward_with_warp(coords, t)
        else:
            pred = model(coords, t)
            pred_source_coords = None
        error = pred - truth
        loss_per_sample = error.square().mean(dim=-1)
        if l1_loss_weight > 0.0:
            loss_per_sample = loss_per_sample + l1_loss_weight * error.abs().mean(dim=-1)
        if edge_loss_weight > 0 or text_box_loss_weight > 0:
            if (
                motion_mode in clean_layout_motion_modes
                and layout_target_weighting
                and clean_glyph_weight_chw is not None
            ):
                glyph_weights = sample_clean_layout_reflow_from(
                    glyph_weight_chw, clean_glyph_weight_chw, coords, t, step_motion_strength
                ).squeeze(-1)
                text_weights = torch.zeros_like(glyph_weights)
            elif motion_mode in layout_reflow_motion_modes and layout_target_weighting:
                glyph_weights = sample_layout_reflow_from(glyph_weight_chw, coords, t, step_motion_strength, 0.0).squeeze(-1)
                text_weights = sample_layout_reflow_from(text_weight_chw, coords, t, step_motion_strength, 0.0).squeeze(-1)
            else:
                glyph_weights = sample_target(glyph_weight_chw, target_coords).squeeze(-1)
                text_weights = sample_target(text_weight_chw, target_coords).squeeze(-1)
            weights = 1.0 + edge_loss_weight * glyph_weights + text_box_loss_weight * text_weights
            loss = (loss_per_sample * weights).mean()
        else:
            loss = loss_per_sample.mean()
        if (
            motion_mode in layout_reflow_motion_modes
            and layout_flow_loss_weight > 0.0
            and pred_source_coords is not None
        ):
            desired_source_coords, flow_alpha = inverse_layout_reflow_coords(coords, t, step_motion_strength)
            flow_weights = flow_alpha.squeeze(-1)
            if layout_target_weighting:
                flow_glyph_weights = sample_layout_reflow_from(glyph_weight_chw, coords, t, step_motion_strength, 0.0).squeeze(-1)
                flow_weights = flow_weights * (1.0 + edge_loss_weight * flow_glyph_weights)
            flow_loss_per_sample = (pred_source_coords - desired_source_coords).square().mean(dim=-1)
            flow_loss = (flow_loss_per_sample * flow_weights).sum() / flow_weights.sum().clamp_min(1e-6)
            loss = loss + layout_flow_loss_weight * flow_loss
        if (
            motion_mode in layout_reflow_motion_modes
            and layout_target_pair_ratio > 0.0
            and layout_target_pair_weight > 0.0
        ):
            pair_source_idx = torch.nonzero(source_focus_for_pairs, as_tuple=False).squeeze(-1)
            if pair_source_idx.numel():
                pair_count = max(1, min(pair_source_idx.numel(), int(batch_size * layout_target_pair_ratio)))
                pair_idx = pair_source_idx[torch.randperm(pair_source_idx.numel(), device=device)[:pair_count]]
                pair_t = t[pair_idx]
                pair_coords = forward_layout_reflow_coords(source_coords_for_pairs[pair_idx], pair_t, step_motion_strength)
                pair_truth, pair_target_coords = truth_for_coords(pair_coords, pair_t, step_motion_strength)
                pair_pred = model(pair_coords, pair_t)
                pair_error = pair_pred - pair_truth
                pair_loss_per_sample = pair_error.square().mean(dim=-1)
                if edge_loss_weight > 0 or text_box_loss_weight > 0:
                    if layout_target_weighting:
                        pair_glyph_weights = sample_layout_reflow_from(
                            glyph_weight_chw, pair_coords, pair_t, step_motion_strength, 0.0
                        ).squeeze(-1)
                        pair_text_weights = sample_layout_reflow_from(
                            text_weight_chw, pair_coords, pair_t, step_motion_strength, 0.0
                        ).squeeze(-1)
                    else:
                        pair_glyph_weights = sample_target(glyph_weight_chw, pair_target_coords).squeeze(-1)
                        pair_text_weights = sample_target(text_weight_chw, pair_target_coords).squeeze(-1)
                    pair_weights = 1.0 + edge_loss_weight * pair_glyph_weights + text_box_loss_weight * pair_text_weights
                    pair_loss = (pair_loss_per_sample * pair_weights).mean()
                else:
                    pair_loss = pair_loss_per_sample.mean()
                loss = loss + layout_target_pair_weight * pair_loss
        if gradient_loss_weight > 0.0 and gradient_loss_ratio > 0.0:
            grad_count = max(1, min(batch_size, int(batch_size * gradient_loss_ratio)))
            grad_idx = torch.randperm(batch_size, device=device)[:grad_count]
            grad_coords = coords[grad_idx]
            grad_t = t[grad_idx]
            grad_pred = pred[grad_idx]
            grad_truth = truth[grad_idx]
            dx = torch.tensor(
                [gradient_loss_offset_px / max(1, train_w - 1), 0.0],
                device=device,
            ).view(1, 2)
            dy = torch.tensor(
                [0.0, gradient_loss_offset_px / max(1, train_h - 1)],
                device=device,
            ).view(1, 2)
            coords_x = (grad_coords + dx).clamp(0.0, 1.0)
            coords_y = (grad_coords + dy).clamp(0.0, 1.0)
            truth_x, _ = truth_for_coords(coords_x, grad_t, step_motion_strength)
            truth_y, _ = truth_for_coords(coords_y, grad_t, step_motion_strength)
            pred_x = model(coords_x, grad_t)
            pred_y = model(coords_y, grad_t)
            gradient_loss = F.mse_loss(pred_x - grad_pred, truth_x - grad_truth) + F.mse_loss(
                pred_y - grad_pred, truth_y - grad_truth
            )
            loss = loss + gradient_loss_weight * gradient_loss
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if grad_clip > 0.0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
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
        img_tensor = render_model_frame(width, height, viewport, t_value)
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
    def render_model_frame(width: int, height: int, viewport: tuple[float, float, float, float], t_value: float) -> torch.Tensor:
        x, y, w, h = viewport
        xs = torch.linspace(x, x + w, width, device=device)
        ys = torch.linspace(y, y + h, height, device=device)
        yy, xx = torch.meshgrid(ys, xs, indexing="ij")
        coords = torch.stack([xx.reshape(-1), yy.reshape(-1)], dim=-1).clamp(0.0, 1.0)
        t = torch.full((coords.shape[0], 1), t_value, device=device)
        parts = []
        chunk = 262144
        for start in range(0, coords.shape[0], chunk):
            coord_chunk = coords[start : start + chunk]
            t_chunk = t[start : start + chunk]
            if layout_oracle_flow and motion_mode in layout_reflow_motion_modes:
                source_chunk, _source_alpha = inverse_layout_reflow_coords(coord_chunk, t_chunk, motion_strength)
                parts.append(model.forward_with_source_coords(coord_chunk, t_chunk, source_chunk))
            else:
                parts.append(model.forward(coord_chunk, t_chunk))
        return torch.cat(parts, dim=0).view(height, width, 3)

    @torch.inference_mode()
    def render_layout_frame(width: int, height: int, t_value: float) -> torch.Tensor:
        output_width = width
        output_height = height
        if video_layout_mode == "frame-scale" and layout_supersample > 1.0:
            width = max(width, int(round(width * layout_supersample)))
            height = max(height, int(round(height * layout_supersample)))
        xs = torch.linspace(0.0, 1.0, width, device=device)
        ys = torch.linspace(0.0, 1.0, height, device=device)
        yy, xx = torch.meshgrid(ys, xs, indexing="ij")
        coords = torch.stack([xx.reshape(-1), yy.reshape(-1)], dim=-1)
        valid = torch.ones((coords.shape[0], 1), device=device, dtype=torch.bool)
        if video_layout_mode in independent_field_layout_modes:
            field_strength = 0.0 if video_layout_mode in independent_translate_layout_modes else layout_transform_strength
            coords = apply_independent_region_field(coords, t_value, field_strength, layout_transform_pan)
        if video_layout_mode in independent_hard_layout_modes:
            output_coords = coords.clone()
            output_x = output_coords[:, 0]
            output_y = output_coords[:, 1]
            envelope = float(np.sin(np.pi * t_value) ** 2)
            for x0, y0, x1, y1, pan_x_mul, pan_y_mul, scale_x_mul, scale_y_mul, speed, phase in independent_layout_regions:
                source_mask = (output_x >= x0) & (output_x <= x1) & (output_y >= y0) & (output_y <= y1)
                valid[source_mask] = False

                cx = (x0 + x1) * 0.5
                cy = (y0 + y1) * 0.5
                source_w = x1 - x0
                source_h = y1 - y0
                angle = 2.0 * np.pi * (float(speed) * t_value + phase)
                pan_x = layout_transform_pan * pan_x_mul * envelope * float(np.sin(angle))
                pan_y = layout_transform_pan * pan_y_mul * envelope * float(np.cos(angle + np.pi * 0.23))
                scale_x = min(
                    1.55,
                    max(0.52, 1.0 + layout_transform_strength * scale_x_mul * envelope * float(np.sin(angle + np.pi * 0.31))),
                )
                scale_y = min(
                    1.55,
                    max(0.52, 1.0 + layout_transform_strength * scale_y_mul * envelope * float(np.cos(angle + np.pi * 0.19))),
                )
                out_cx = cx + pan_x
                out_cy = cy + pan_y
                out_w = source_w * scale_x
                out_h = source_h * scale_y
                canonical_x = cx + (output_x - out_cx) / scale_x
                canonical_y = cy + (output_y - out_cy) / scale_y
                moved_mask = (
                    (output_x >= out_cx - out_w * 0.5)
                    & (output_x <= out_cx + out_w * 0.5)
                    & (output_y >= out_cy - out_h * 0.5)
                    & (output_y <= out_cy + out_h * 0.5)
                    & (canonical_x >= x0)
                    & (canonical_x <= x1)
                    & (canonical_y >= y0)
                    & (canonical_y <= y1)
                )
                coords[moved_mask, 0] = canonical_x[moved_mask].clamp(0.0, 1.0)
                coords[moved_mask, 1] = canonical_y[moved_mask].clamp(0.0, 1.0)
                valid[moved_mask] = True
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
            patch_specs = []
            patch_coord_parts = []
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
                patch_specs.append((ox0, oy0, ox1, oy1, patch_h, patch_w, patch_coords.shape[0]))
                patch_coord_parts.append(patch_coords)

            if element_render_mode == "batched" and patch_coord_parts:
                all_patch_coords = torch.cat(patch_coord_parts, dim=0)
                all_patch_t = torch.zeros((all_patch_coords.shape[0], 1), device=device)
                patch_parts = []
                for start in range(0, all_patch_coords.shape[0], chunk):
                    patch_parts.append(model.forward(all_patch_coords[start : start + chunk], all_patch_t[start : start + chunk]))
                all_patch = torch.cat(patch_parts, dim=0)
                all_alpha = None
                if element_mask_mode == "text-alpha":
                    all_alpha = sample_target(element_alpha_chw, all_patch_coords).clamp(0.0, 1.0)
                offset = 0
                for ox0, oy0, ox1, oy1, patch_h, patch_w, count in patch_specs:
                    patch = all_patch[offset : offset + count].view(patch_h, patch_w, 3)
                    if element_mask_mode == "text-alpha" and all_alpha is not None:
                        alpha = all_alpha[offset : offset + count].view(patch_h, patch_w, 1)
                        frame[oy0:oy1, ox0:ox1] = patch * alpha + frame[oy0:oy1, ox0:ox1] * (1.0 - alpha)
                    else:
                        frame[oy0:oy1, ox0:ox1] = patch
                    offset += count
            elif patch_coord_parts:
                for spec, patch_coords in zip(patch_specs, patch_coord_parts):
                    ox0, oy0, ox1, oy1, patch_h, patch_w, _count = spec
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

        if width != output_width or height != output_height:
            frame = (
                F.interpolate(
                    frame.permute(2, 0, 1).unsqueeze(0),
                    size=(output_height, output_width),
                    mode="area",
                )
                .squeeze(0)
                .permute(1, 2, 0)
                .contiguous()
            )
        return frame

    def render_target_frame(width: int, height: int, t_value: float) -> torch.Tensor:
        xs = torch.linspace(0.0, 1.0, width, device=device)
        ys = torch.linspace(0.0, 1.0, height, device=device)
        yy, xx = torch.meshgrid(ys, xs, indexing="ij")
        coords = torch.stack([xx.reshape(-1), yy.reshape(-1)], dim=-1)
        t = torch.full((coords.shape[0], 1), t_value, device=device)
        if motion_mode in clean_layout_motion_modes:
            return sample_clean_layout_reflow(coords, t, motion_strength).view(height, width, 3)
        if motion_mode in layout_reflow_motion_modes:
            return sample_layout_reflow(coords, t, motion_strength).view(height, width, 3)
        if motion_mode in independent_sprite_motion_modes:
            return sample_independent_sprite_translation(coords, t, motion_strength).view(height, width, 3)
        target_coords = target_coords_for_motion(coords, t, motion_strength, motion_mode)
        return sample_target(target_chw, target_coords).view(height, width, 3)

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
    if motion_mode in layout_reflow_motion_modes or motion_mode in independent_sprite_motion_modes:
        artifacts["target-mid.png"] = base64.b64encode(tensor_to_png_bytes(render_target_frame(960, 544, 0.5))).decode("ascii")
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
            video_frames.append(render_model_frame(960, 544, frame_viewport(t_value), t_value))
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    render_33_wall_ms = (perf_counter() - video_start) * 1000
    video_bytes, encode_ms = encode_mp4(video_frames, 960, 544, int(config["fps"]))
    artifacts["output.mp4"] = base64.b64encode(video_bytes).decode("ascii")

    motion_delta = float(torch.mean(torch.abs(first - video_frames[frame_count // 2])).detach().cpu())
    loop_error = float(torch.mean(torch.abs(first - video_frames[-1])).detach().cpu())

    glyph_enabled = edge_sample_ratio > 0 or edge_loss_weight > 0
    text_enabled = text_box_sample_ratio > 0 or text_box_loss_weight > 0
    canvas_type = (
        "stable-latent-feature-grid-element-anchor-layout-text-box-weighted"
        if text_enabled and video_layout_mode == "element-frame-scale"
        else "stable-latent-feature-grid-layout-transform-text-box-weighted"
        if text_enabled and video_layout_mode != "none"
        else "time-conditioned-latent-feature-grid-learned-flow-mlp-text-box-weighted"
        if text_enabled
        else "time-conditioned-latent-feature-grid-learned-flow-mlp-glyph-weighted"
        if glyph_enabled
        else "time-conditioned-latent-feature-grid-learned-flow-mlp"
    )
    if detail_channels > 0 and detail_scale != 0.0:
        canvas_type += "-detail-residual"
    if source_coord_features:
        canvas_type += "-source-coord"
    if layout_flow_loss_weight > 0.0:
        canvas_type += "-flow-supervised"
    if layout_oracle_flow:
        canvas_type += "-oracle-flow"
    if latent_neighborhood_radius_px > 0.0 and latent_neighborhood_mode not in {"none", "center"}:
        canvas_type += f"-latent-{latent_neighborhood_mode}-neighborhood"
    if context_channels > 0:
        canvas_type += "-coarse-context"
    if decoder_mode.lower().replace("_", "-") != "single":
        canvas_type += f"-{decoder_mode.lower().replace('_', '-')}"
    if rgb_skip_scale > 0.0:
        canvas_type += f"-rgb-skip-{model.rgb_skip_mode}"
    if motion_mode in clean_layout_motion_modes:
        canvas_type += "-clean-page-reflow"
    metrics = {
        "canvas_type": canvas_type,
        "train_resolution": config["train_resolution"],
        "steps": steps,
        "batch_size": batch_size,
        "channels": int(config["channels"]),
        "hidden": int(config["hidden"]),
        "detail_channels": detail_channels,
        "detail_hidden": detail_hidden,
        "detail_scale": detail_scale,
        "detail_init_scale": detail_init_scale,
        "source_coord_features": int(source_coord_features),
        "latent_neighborhood_mode": latent_neighborhood_mode,
        "latent_neighborhood_radius_px": latent_neighborhood_radius_px,
        "latent_neighborhood_taps": int(model.latent_offsets.shape[0]),
        "latent_sample_mode": latent_sample_mode,
        "context_channels": context_channels,
        "context_scale": context_scale,
        "context_init_scale": context_init_scale,
        "context_sample_mode": context_sample_mode,
        "context_resolution": list(model.context_canvas.shape[-2:]) if model.context_canvas is not None else [0, 0],
        "decoder_mode": model.decoder_mode,
        "target_branch_scale": target_branch_scale,
        "target_branch_hidden": target_branch_hidden,
        "rgb_skip_scale": rgb_skip_scale,
        "rgb_skip_mode": model.rgb_skip_mode,
        "rgb_skip_base_scale": model.rgb_skip_base_scale,
        "rgb_skip_gate_mode": model.rgb_skip_gate_mode,
        "rgb_skip_gate_init": rgb_skip_gate_init,
        "freq_bands": int(config["freq_bands"]),
        "time_bands": int(config["time_bands"]),
        "lr": base_lr,
        "lr_schedule": lr_schedule,
        "min_lr_ratio": min_lr_ratio,
        "grad_clip": grad_clip,
        "l1_loss_weight": l1_loss_weight,
        "gradient_loss_weight": gradient_loss_weight,
        "gradient_loss_ratio": gradient_loss_ratio,
        "gradient_loss_offset_px": gradient_loss_offset_px,
        "seed": seed,
        "experiment_label": config.get("experiment_label", ""),
        "flow_scale": flow_scale,
        "motion_mode": motion_mode,
        "motion_strength": motion_strength,
        "clean_target_variant": clean_target_variant,
        "video_viewport_mode": video_viewport_mode,
        "viewport_zoom": viewport_zoom,
        "viewport_pan": viewport_pan,
        "video_layout_mode": video_layout_mode,
        "layout_transform_strength": layout_transform_strength,
        "layout_transform_pan": layout_transform_pan,
        "layout_supersample": layout_supersample,
        "layout_region_count": (
            len(independent_layout_regions)
            if video_layout_mode in independent_layout_modes or motion_mode in independent_field_layout_modes
            else 0
        ),
        "element_scale_ratio": element_scale_ratio,
        "element_anchor_padding": element_anchor_padding,
        "element_mask_mode": element_mask_mode,
        "element_anchor_mode": element_anchor_mode,
        "element_render_mode": element_render_mode,
        "element_line_count": len(element_line_boxes),
        "min_ocr_similarity": float(config.get("min_ocr_similarity", 0.5)),
        "min_motion_delta": float(config.get("min_motion_delta", 0.001)),
        "edge_sample_ratio": edge_sample_ratio,
        "edge_loss_weight": edge_loss_weight,
        "text_box_sample_ratio": text_box_sample_ratio,
        "text_box_loss_weight": text_box_loss_weight,
        "text_box_padding": text_box_padding,
        "layout_target_sampling": int(layout_target_sampling),
        "layout_target_weighting": int(layout_target_weighting),
        "layout_target_sampling_ratio": layout_target_sampling_ratio,
        "layout_target_mid_sampling_ratio": layout_target_mid_sampling_ratio,
        "layout_target_mid_time_width": layout_target_mid_time_width,
        "layout_target_pair_ratio": layout_target_pair_ratio,
        "layout_target_pair_weight": layout_target_pair_weight,
        "layout_mid_time_ratio": layout_mid_time_ratio,
        "layout_mid_time_width": layout_mid_time_width,
        "layout_flow_loss_weight": layout_flow_loss_weight,
        "layout_oracle_flow": int(layout_oracle_flow),
        "layout_motion_curriculum_ratio": layout_motion_curriculum_ratio,
        "layout_motion_curriculum_start": layout_motion_curriculum_start,
        "layout_endpoint_ratio": layout_endpoint_ratio,
        "layout_endpoint_target_ratio": layout_endpoint_target_ratio,
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
            "C4.6 neural canvas: stable content with smooth independent region translation field"
            if video_layout_mode in independent_translate_layout_modes
            else "C4.5 neural canvas: stable content with smooth independent region field"
            if video_layout_mode in independent_field_layout_modes
            else f"C4.4 neural canvas: stable content with independent coarse regions moving on separate timelines"
            if video_layout_mode in independent_hard_layout_modes
            else f"C2.6 neural canvas: stable content with OCR {element_anchor_mode} anchors, {element_mask_mode} masks, and {video_layout_mode} layout transform"
            if text_enabled and video_layout_mode == "element-frame-scale"
            else f"C2.3 neural canvas: stable content with {video_layout_mode} layout transform"
            if video_layout_mode != "none"
            else "C8.6 neural canvas: learned clean two-state page reflow from x,y,t"
            if motion_mode in clean_layout_motion_modes
            else "C4.7 neural canvas: learned full page layout reflow from x,y,t"
            if motion_mode in layout_reflow_motion_modes
            else "C4.7 neural canvas: learned independent sprite translation from x,y,t"
            if motion_mode in independent_sprite_motion_modes
            else "C4.6 neural canvas: learned independent region translation from x,y,t"
            if motion_mode in independent_translate_layout_modes
            else "C4.5 neural canvas: learned independent region field from x,y,t"
            if motion_mode in {"independent-field", "region-field"}
            else f"C2.1 neural canvas: learned {motion_mode} motion with OCR text-box-weighted sampling/loss"
            if text_enabled
            else "C2-lite neural canvas: learned time-conditioned motion field with glyph-weighted sampling/loss"
            if glyph_enabled
            else "C2-lite neural canvas: learned time-conditioned motion field sampling a persistent latent canvas"
        ),
    }
    if detail_channels > 0 and detail_scale != 0.0:
        metrics["description"] += " Residual detail canvas/head enabled for high-frequency pixel correction."
    if source_coord_features:
        metrics["description"] += " Learned warped/source coordinate features are included in the renderer MLP."
    if motion_mode in clean_layout_motion_modes:
        metrics["description"] += f" Clean target fixture variant: {clean_target_variant}."
    if layout_flow_loss_weight > 0.0:
        metrics["description"] += " Learned flow is supervised toward the known inverse layout-reflow map."
    if layout_oracle_flow:
        metrics["description"] += " Oracle inverse layout-flow coordinates are used as a diagnostic transport control."
    if latent_neighborhood_radius_px > 0.0 and latent_neighborhood_mode not in {"none", "center"}:
        metrics["description"] += (
            f" Decoder samples a {latent_neighborhood_mode} latent neighborhood "
            f"with {latent_neighborhood_radius_px:g}px radius for local glyph/detail context "
            f"in {latent_sample_mode} mode."
        )
    if context_channels > 0:
        metrics["description"] += (
            f" Decoder also samples a coarse context latent canvas with {context_channels} channels "
            f"at scale {context_scale:g} in {context_sample_mode} mode."
        )
    if model.decoder_mode == "dual-residual":
        metrics["description"] += (
            f" Decoder uses a source branch plus gated target-position residual branch "
            f"(scale {target_branch_scale:g}, target hidden {target_branch_hidden})."
        )
    elif model.decoder_mode == "dual-residual-fused":
        metrics["description"] += (
            f" Decoder uses a source branch plus gated residual branch that sees both source "
            f"and target-position features (scale {target_branch_scale:g}, target hidden {target_branch_hidden})."
        )
    elif model.decoder_mode == "dual-gate":
        metrics["description"] += (
            f" Decoder uses separately gated source and target-position branches "
            f"(target hidden {target_branch_hidden})."
        )
    if rgb_skip_scale > 0.0:
        metrics["description"] += (
            f" Renderer uses a learned RGB neural texture skip sampled in {model.rgb_skip_mode} mode, "
            f"with base scale {model.rgb_skip_base_scale:g} and bounded residual scale {rgb_skip_scale:g}."
        )
        if model.rgb_gate_canvas is not None:
            metrics["description"] += (
                f" RGB skip is modulated by a learned {model.rgb_skip_gate_mode} gate canvas."
            )
    if layout_target_mid_sampling_ratio > 0.0:
        metrics["description"] += (
            f" Training directly samples {layout_target_mid_sampling_ratio:g} of points from "
            f"the reflowed midpoint glyph/text distribution."
        )
    return {"artifacts": artifacts, "metrics": metrics}


@app.local_entrypoint()
def main(
    steps: int = 3000,
    train_resolution: str = "960x544",
    batch_size: int = 131072,
    channels: int = 16,
    hidden: int = 96,
    detail_channels: int = 0,
    detail_hidden: int = 0,
    detail_scale: float = 0.0,
    detail_init_scale: float = 0.01,
    source_coord_features: int = 0,
    latent_neighborhood_mode: str = "none",
    latent_neighborhood_radius_px: float = 0.0,
    latent_sample_mode: str = "source",
    context_channels: int = 0,
    context_scale: float = 0.25,
    context_init_scale: float = 0.02,
    context_sample_mode: str = "source",
    decoder_mode: str = "single",
    target_branch_scale: float = 0.0,
    target_branch_hidden: int = 0,
    rgb_skip_scale: float = 0.0,
    rgb_skip_mode: str = "source",
    rgb_skip_base_scale: float = 1.0,
    rgb_skip_gate_mode: str = "none",
    rgb_skip_gate_init: float = 0.5,
    freq_bands: int = 8,
    time_bands: int = 4,
    lr: float = 0.01,
    lr_schedule: str = "constant",
    min_lr_ratio: float = 0.1,
    grad_clip: float = 0.0,
    l1_loss_weight: float = 0.0,
    gradient_loss_weight: float = 0.0,
    gradient_loss_ratio: float = 0.125,
    gradient_loss_offset_px: float = 1.0,
    flow_scale: float = 0.006,
    motion_mode: str = "jiggle",
    motion_strength: float = -1.0,
    clean_target_variant: str = "diagram-left",
    video_viewport_mode: str = "static",
    viewport_zoom: float = 0.0,
    viewport_pan: float = 0.0,
    video_layout_mode: str = "none",
    layout_transform_strength: float = 0.0,
    layout_transform_pan: float = 0.0,
    layout_supersample: float = 1.0,
    element_scale_ratio: float = 0.25,
    element_anchor_padding: int = 3,
    element_mask_mode: str = "rectangle",
    element_anchor_mode: str = "line",
    element_render_mode: str = "sequential",
    experiment_label: str = "",
    edge_sample_ratio: float = 0.0,
    edge_loss_weight: float = 0.0,
    text_box_sample_ratio: float = 0.0,
    text_box_loss_weight: float = 0.0,
    text_box_padding: int = 3,
    text_box_min_conf: float = 55.0,
    layout_target_sampling: int = 0,
    layout_target_weighting: int = 0,
    layout_target_sampling_ratio: float = 1.0,
    layout_target_mid_sampling_ratio: float = 0.0,
    layout_target_mid_time_width: float = 0.24,
    layout_target_pair_ratio: float = 0.0,
    layout_target_pair_weight: float = 1.0,
    layout_mid_time_ratio: float = 0.0,
    layout_mid_time_width: float = 0.24,
    layout_flow_loss_weight: float = 0.0,
    layout_oracle_flow: int = 0,
    layout_motion_curriculum_ratio: float = 0.0,
    layout_motion_curriculum_start: float = 0.0,
    layout_endpoint_ratio: float = 0.0,
    layout_endpoint_target_ratio: float = 0.5,
    min_ocr_similarity: float = 0.5,
    min_motion_delta: float = 0.001,
    seed: int = 0,
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
        "detail_channels": detail_channels,
        "detail_hidden": detail_hidden if detail_hidden > 0 else hidden,
        "detail_scale": detail_scale,
        "detail_init_scale": detail_init_scale,
        "source_coord_features": source_coord_features,
        "latent_neighborhood_mode": latent_neighborhood_mode,
        "latent_neighborhood_radius_px": latent_neighborhood_radius_px,
        "latent_sample_mode": latent_sample_mode,
        "context_channels": context_channels,
        "context_scale": context_scale,
        "context_init_scale": context_init_scale,
        "context_sample_mode": context_sample_mode,
        "decoder_mode": decoder_mode,
        "target_branch_scale": target_branch_scale,
        "target_branch_hidden": target_branch_hidden if target_branch_hidden > 0 else hidden,
        "rgb_skip_scale": rgb_skip_scale,
        "rgb_skip_mode": rgb_skip_mode,
        "rgb_skip_base_scale": rgb_skip_base_scale,
        "rgb_skip_gate_mode": rgb_skip_gate_mode,
        "rgb_skip_gate_init": rgb_skip_gate_init,
        "freq_bands": freq_bands,
        "time_bands": time_bands,
        "lr": lr,
        "lr_schedule": lr_schedule,
        "min_lr_ratio": min_lr_ratio,
        "grad_clip": grad_clip,
        "l1_loss_weight": l1_loss_weight,
        "gradient_loss_weight": gradient_loss_weight,
        "gradient_loss_ratio": gradient_loss_ratio,
        "gradient_loss_offset_px": gradient_loss_offset_px,
        "seed": seed,
        "flow_scale": flow_scale,
        "motion_mode": motion_mode,
        "motion_strength": motion_strength,
        "clean_target_variant": clean_target_variant,
        "video_viewport_mode": video_viewport_mode,
        "viewport_zoom": viewport_zoom,
        "viewport_pan": viewport_pan,
        "video_layout_mode": video_layout_mode,
        "layout_transform_strength": layout_transform_strength,
        "layout_transform_pan": layout_transform_pan,
        "layout_supersample": layout_supersample,
        "element_scale_ratio": element_scale_ratio,
        "element_anchor_padding": element_anchor_padding,
        "element_mask_mode": element_mask_mode,
        "element_anchor_mode": element_anchor_mode,
        "element_render_mode": element_render_mode,
        "experiment_label": experiment_label,
        "min_ocr_similarity": min_ocr_similarity,
        "min_motion_delta": min_motion_delta,
        "edge_sample_ratio": edge_sample_ratio,
        "edge_loss_weight": edge_loss_weight,
        "text_box_sample_ratio": text_box_sample_ratio,
        "text_box_loss_weight": text_box_loss_weight,
        "text_box_padding": text_box_padding,
        "text_box_min_conf": text_box_min_conf,
        "layout_target_sampling": layout_target_sampling,
        "layout_target_weighting": layout_target_weighting,
        "layout_target_sampling_ratio": layout_target_sampling_ratio,
        "layout_target_mid_sampling_ratio": layout_target_mid_sampling_ratio,
        "layout_target_mid_time_width": layout_target_mid_time_width,
        "layout_target_pair_ratio": layout_target_pair_ratio,
        "layout_target_pair_weight": layout_target_pair_weight,
        "layout_mid_time_ratio": layout_mid_time_ratio,
        "layout_mid_time_width": layout_mid_time_width,
        "layout_flow_loss_weight": layout_flow_loss_weight,
        "layout_oracle_flow": layout_oracle_flow,
        "layout_motion_curriculum_ratio": layout_motion_curriculum_ratio,
        "layout_motion_curriculum_start": layout_motion_curriculum_start,
        "layout_endpoint_ratio": layout_endpoint_ratio,
        "layout_endpoint_target_ratio": layout_endpoint_target_ratio,
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
        "target_mid": str(run_dir / "target-mid.png"),
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
