"""
Generate branded OG image (1200x630).

Uses the project's Cormorant Garamond and DM Sans fonts for proper
editorial typography. Requires: Pillow, fonttools, brotli.

Usage:
    python scripts/generate_og_image.py
"""

import os
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "docs" / "og.png"
FONTS_DIR = PROJECT_ROOT / "docs" / "fonts"
WIDTH = 1200
HEIGHT = 630

# Project palette
TEAL = (46, 96, 88)  # #2E6058
WHITE = (255, 255, 255)


def _blend(alpha: float) -> tuple[int, int, int]:
    """Pre-blend white over teal at given opacity."""
    return tuple(int(TEAL[i] + (WHITE[i] - TEAL[i]) * alpha) for i in range(3))


def _load_font(woff2_name: str, size: int) -> tuple[ImageFont.FreeTypeFont, str]:
    """Decompress woff2 to temp TTF and load with Pillow.

    Returns (font, tmp_path) so caller can clean up.
    """
    woff2_path = FONTS_DIR / woff2_name
    font_tt = TTFont(str(woff2_path))
    fd, tmp_path = tempfile.mkstemp(suffix=".ttf")
    os.close(fd)
    font_tt.save(tmp_path)
    font_tt.close()
    return ImageFont.truetype(tmp_path, size), tmp_path


def _draw_tracked(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_x: float,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    tracking: float = 0,
) -> None:
    """Draw text centered horizontally with letter-spacing."""
    total = sum(font.getlength(ch) for ch in text)
    total += tracking * max(0, len(text) - 1)

    x = center_x - total / 2
    for i, ch in enumerate(text):
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch)
        if i < len(text) - 1:
            x += tracking


def build_image(width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    """Build the OG image and return a PIL Image."""
    tmp_files = []
    try:
        # Scale fonts and positions when rendering at non-standard sizes
        scale = min(width / WIDTH, height / HEIGHT)
        heading_size = max(1, int(96 * scale))
        body_size = max(1, int(24 * scale))
        small_size = max(1, int(17 * scale))

        heading, t1 = _load_font("cormorant-garamond-300-latin.woff2", heading_size)
        tmp_files.append(t1)
        body, t2 = _load_font("dm-sans-400-latin.woff2", body_size)
        tmp_files.append(t2)
        small, t3 = _load_font("dm-sans-300-latin.woff2", small_size)
        tmp_files.append(t3)

        img = Image.new("RGB", (width, height), TEAL)
        draw = ImageDraw.Draw(img)
        cx = width / 2

        # "Last Eat" — Cormorant Garamond 300, generous tracking (~0.22em)
        _draw_tracked(
            draw, "Last Eat", cx, int(195 * scale),
            heading, WHITE, tracking=22 * scale,
        )

        # Thin horizontal rule
        rule_y = int(310 * scale)
        rule_half = int(40 * scale)
        draw.line(
            [(cx - rule_half, rule_y), (cx + rule_half, rule_y)],
            fill=_blend(0.25),
            width=1,
        )

        # "Restaurantes en Madrid" — DM Sans 400
        _draw_tracked(
            draw, "Restaurantes en Madrid", cx, int(340 * scale),
            body, _blend(0.78), tracking=1 * scale,
        )

        # "lasteat.es" — DM Sans 300, subtle
        _draw_tracked(
            draw, "lasteat.es", cx, int(555 * scale),
            small, _blend(0.35), tracking=2 * scale,
        )

        return img
    finally:
        for f in tmp_files:
            try:
                os.unlink(f)
            except OSError:
                pass


def generate_image(output_path: Path = OUTPUT_PATH) -> None:
    img = build_image()
    img.save(str(output_path), optimize=True)
    size_kb = output_path.stat().st_size / 1024
    print(f"Generated {output_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    generate_image()
