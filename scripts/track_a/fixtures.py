from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
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


def create_text_heavy_fixture(path: str | Path, width: int = 1280, height: int = 736) -> Path:
    """Create a deterministic text-heavy page image for Track A benchmarks."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (width, height), "#f6f4ef")
    draw = ImageDraw.Draw(img)

    margin = int(width * 0.055)
    top = int(height * 0.07)
    ink = "#171717"
    muted = "#5f6368"
    line = "#c8c1b4"
    accent = "#146c94"
    green = "#557a46"

    draw.rounded_rectangle(
        [margin, top, width - margin, height - top],
        radius=14,
        fill="#fffdf8",
        outline=line,
        width=2,
    )

    title_font = _font(max(30, width // 26), bold=True)
    sub_font = _font(max(15, width // 70))
    h_font = _font(max(18, width // 58), bold=True)
    body_font = _font(max(14, width // 76))
    tiny_font = _font(max(11, width // 98))

    x = margin + 42
    y = top + 36
    draw.text((x, y), "Sketchapedia: Roman Colosseum", fill=ink, font=title_font)
    y += int(height * 0.07)
    draw.text(
        (x, y),
        "A structured visual page with labels, diagrams, and dense text for stability checks.",
        fill=muted,
        font=sub_font,
    )

    y += int(height * 0.06)
    col_w = (width - 2 * margin - 110) // 2
    left = x
    right = x + col_w + 54

    sections = [
        ("Arena Floor", "Trapdoors, lifts, and service passages created sudden reveals during public spectacles."),
        ("Velarium", "A retractable awning system shaded spectators and required coordinated rope handling."),
        ("Seating", "Social order was encoded into the architecture through tiered, separated seating bands."),
        ("Materials", "Travertine, tuff, brick, and concrete carried both structure and ornament."),
    ]
    for i, (heading, body) in enumerate(sections):
        sx = left if i % 2 == 0 else right
        sy = y + (i // 2) * int(height * 0.15)
        draw.text((sx, sy), heading, fill=ink, font=h_font)
        draw.line((sx, sy + 30, sx + col_w, sy + 30), fill=line, width=1)
        draw.multiline_text(
            (sx, sy + 42),
            body,
            fill="#2d2d2d",
            font=body_font,
            spacing=5,
        )

    chart_top = int(height * 0.48)
    chart_left = left
    chart_right = width - margin - 42
    chart_bottom = height - top - 50
    draw.rounded_rectangle(
        [chart_left, chart_top, chart_right, chart_bottom],
        radius=10,
        fill="#f1f7f6",
        outline="#b7cdc8",
        width=2,
    )
    draw.text((chart_left + 26, chart_top + 22), "Annotated Section Diagram", fill=ink, font=h_font)

    cx = chart_left + int((chart_right - chart_left) * 0.36)
    cy = chart_top + int((chart_bottom - chart_top) * 0.58)
    rx = int((chart_right - chart_left) * 0.24)
    ry = int((chart_bottom - chart_top) * 0.22)
    for offset, color in [(0, accent), (18, "#6aa6b8"), (36, green), (54, "#8d7a4f")]:
        draw.ellipse([cx - rx + offset, cy - ry + offset // 3, cx + rx - offset, cy + ry - offset // 3], outline=color, width=3)
    draw.rectangle([cx - 20, cy - 58, cx + 20, cy + 58], fill="#fffdf8", outline=line)

    labels = [
        ("upper seating", cx + rx + 30, cy - ry - 4),
        ("awnings", cx - rx - 120, cy - ry + 38),
        ("arena floor", cx + rx + 36, cy + 10),
        ("service level", cx - rx - 132, cy + ry - 28),
    ]
    for text, lx, ly in labels:
        draw.text((lx, ly), text, fill=ink, font=tiny_font)
        draw.line((lx - 10, ly + 9, cx, cy), fill="#8aa4a1", width=1)

    notes_x = chart_left + int((chart_right - chart_left) * 0.64)
    notes_y = chart_top + 76
    notes = [
        "1. Text must remain readable across all frames.",
        "2. Diagram geometry should not wobble or melt.",
        "3. Motion may appear in sky, cloth, crowds, or light.",
        "4. Page layout is treated as the canonical first frame.",
        "5. Loop boundary should be visually quiet.",
    ]
    for note in notes:
        draw.text((notes_x, notes_y), note, fill="#263238", font=body_font)
        notes_y += int(height * 0.045)

    img.save(output, "PNG")
    return output
