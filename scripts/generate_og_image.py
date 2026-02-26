"""
Generate branded OG image (1200x630) without external dependencies.

Usage:
    python scripts/generate_og_image.py
"""

import struct
import zlib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "docs" / "og.png"
WIDTH = 1200
HEIGHT = 630

# 5x7 bitmap font for required uppercase chars.
GLYPHS = {
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
}


def blend_rect(img: dict, x: int, y: int, w: int, h: int, color, alpha: float) -> None:
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(img["width"], x + w)
    y1 = min(img["height"], y + h)
    if x0 >= x1 or y0 >= y1:
        return
    pixels = img["pixels"]
    width = img["width"]
    inv_alpha = 1.0 - alpha
    sr, sg, sb = color

    for yy in range(y0, y1):
        base = (yy * width + x0) * 3
        for _xx in range(x0, x1):
            dr = pixels[base]
            dg = pixels[base + 1]
            db = pixels[base + 2]
            pixels[base] = int((dr * inv_alpha) + (sr * alpha) + 0.5)
            pixels[base + 1] = int((dg * inv_alpha) + (sg * alpha) + 0.5)
            pixels[base + 2] = int((db * inv_alpha) + (sb * alpha) + 0.5)
            base += 3


def draw_text(img: dict, text: str, y: int, scale: int, color, alpha: float = 1.0) -> None:
    text = text.upper()
    glyph_w = 5
    spacing = 1
    total = 0
    for ch in text:
        total += (glyph_w + spacing) * scale
    if total > 0:
        total -= spacing * scale

    x = (img["width"] - total) // 2
    for ch in text:
        glyph = GLYPHS.get(ch, GLYPHS[" "])
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    blend_rect(
                        img,
                        x + col * scale,
                        y + row * scale,
                        scale,
                        scale,
                        color=color,
                        alpha=alpha,
                    )
        x += (glyph_w + spacing) * scale


def build_image(width: int = WIDTH, height: int = HEIGHT) -> dict:
    top = (62, 137, 127)
    bottom = (27, 83, 76)
    pixels = bytearray(width * height * 3)
    img = {"width": width, "height": height, "pixels": pixels}

    for y in range(height):
        t = y / (height - 1)
        r = int((top[0] * (1.0 - t)) + (bottom[0] * t))
        g = int((top[1] * (1.0 - t)) + (bottom[1] * t))
        b = int((top[2] * (1.0 - t)) + (bottom[2] * t))
        row = bytes((r, g, b)) * width
        start = y * width * 3
        pixels[start : start + width * 3] = row

    blend_rect(img, -100, -60, 720, 320, color=(255, 255, 255), alpha=0.09)
    blend_rect(img, 620, 260, 720, 420, color=(14, 52, 47), alpha=0.35)
    blend_rect(img, 120, 510, 960, 2, color=(255, 255, 255), alpha=0.3)

    draw_text(img, "LAST EAT", y=150, scale=18, color=(255, 255, 255), alpha=1.0)
    draw_text(img, "RESTAURANTES EN MADRID", y=320, scale=7, color=(255, 255, 255), alpha=0.95)
    draw_text(img, "GUIA CURADA DE 770+ RESTAURANTES", y=400, scale=5, color=(255, 255, 255), alpha=0.82)

    return img


def png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path: Path, img: dict) -> None:
    width = img["width"]
    height = img["height"]
    pixels = img["pixels"]
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = bytearray()
    row_len = width * 3
    for y in range(height):
        start = y * row_len
        raw.append(0)  # filter type 0 (None)
        raw.extend(pixels[start : start + row_len])
    compressed = zlib.compress(raw, level=9)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", compressed)
        + png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def generate_image(output_path: Path = OUTPUT_PATH) -> None:
    image = build_image()
    write_png(output_path, image)
    size_kb = output_path.stat().st_size / 1024
    print(f"Generated {output_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    generate_image()
