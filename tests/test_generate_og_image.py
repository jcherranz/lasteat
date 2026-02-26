from pathlib import Path

import scripts.generate_og_image as generate_og_image


def test_build_image_dimensions_and_buffer_size():
    img = generate_og_image.build_image(width=120, height=63)
    assert img["width"] == 120
    assert img["height"] == 63
    assert len(img["pixels"]) == 120 * 63 * 3


def test_write_png_creates_valid_png(tmp_path: Path):
    out = tmp_path / "og.png"
    img = generate_og_image.build_image(width=120, height=63)
    generate_og_image.write_png(out, img)

    data = out.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert out.stat().st_size > 100
