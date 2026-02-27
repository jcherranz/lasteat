from pathlib import Path

import scripts.generate_og_image as generate_og_image


def test_build_image_dimensions():
    img = generate_og_image.build_image(width=120, height=63)
    assert img.size == (120, 63)
    assert img.mode == "RGB"


def test_generates_valid_png(tmp_path: Path):
    out = tmp_path / "og.png"
    img = generate_og_image.build_image(width=120, height=63)
    img.save(str(out), optimize=True)

    data = out.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert out.stat().st_size > 100
