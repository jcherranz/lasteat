import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

import scripts.generate_data_js as generate_data_js

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _sample_restaurants() -> list[dict]:
    return json.loads((FIXTURES_DIR / "sample_restaurants.json").read_text(encoding="utf-8"))


class FixedDatetime:
    @classmethod
    def now(cls, tz=None):
        return datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def _parse_data_js(content: str) -> tuple[list[dict], dict]:
    lines = content.strip().splitlines()
    restaurants = json.loads(lines[0].removeprefix("const RESTAURANTS=").removesuffix(";"))
    meta = json.loads(lines[1].removeprefix("const META=").removesuffix(";"))
    return restaurants, meta


def test_abbreviate_maps_expected_keys():
    row = _sample_restaurants()[0]

    out = generate_data_js.abbreviate(row)

    assert out == {
        "n": "La Tasca",
        "s": "la-tasca",
        "a": "Calle Mayor 1, Madrid",
        "lat": "40.4167",
        "lng": "-3.70325",
        "c": "Mediterránea, de mercado",
        "d": "Centro",
        "r": "8.7",
        "rf": "8.8",
        "rd": "8.4",
        "rs": "8.6",
        "p": "55",
        "ph": "+34 910 000 000",
        "w": "https://latasca.example.com",
    }


def test_abbreviate_omits_empty_string_and_none_values():
    row = {
        "name": "Demo",
        "slug": "demo",
        "address": "",
        "latitude": "",
        "longitude": "",
        "cuisine": "Fusión",
        "district": "",
        "rating": "8.0",
        "rating_food": "",
        "rating_decor": None,
        "rating_service": "",
        "price_eur": "",
        "phone": "",
        "website": "",
        "macarfi_url": "https://macarfi.example.com/demo",
    }

    out = generate_data_js.abbreviate(row)

    assert out == {
        "n": "Demo",
        "s": "demo",
        "c": "Fusión",
        "r": "8.0",
        "u": "https://macarfi.example.com/demo",
    }


def test_abbreviate_omits_canonical_macarfi_url_but_keeps_non_canonical():
    row = _sample_restaurants()[0].copy()
    out = generate_data_js.abbreviate(row)
    assert "u" not in out

    row["macarfi_url"] = "https://macarfi.com/es/mad/ficha-restaurante/la-tasca?ref=abc"
    out_non_canonical = generate_data_js.abbreviate(row)
    assert out_non_canonical["u"] == row["macarfi_url"]


def test_generate_writes_expected_output_format(tmp_path, monkeypatch):
    input_path = tmp_path / "restaurants.json"
    output_path = tmp_path / "data.js"
    input_path.write_text(json.dumps(_sample_restaurants(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(generate_data_js, "datetime", FixedDatetime)

    count = generate_data_js.generate(input_path, output_path)

    assert count == 2
    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("const RESTAURANTS=")
    assert "\nconst META=" in content
    assert content.endswith(";\n")

    restaurants, meta = _parse_data_js(content)
    assert len(restaurants) == 2
    assert restaurants[0]["n"] == "La Tasca"
    assert meta == {"updated": "2024-01-02T03:04:05Z", "count": 2}


def test_generate_handles_empty_input(tmp_path, monkeypatch):
    input_path = tmp_path / "empty.json"
    output_path = tmp_path / "data.js"
    input_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(generate_data_js, "datetime", FixedDatetime)

    count = generate_data_js.generate(input_path, output_path)

    assert count == 0
    restaurants, meta = _parse_data_js(output_path.read_text(encoding="utf-8"))
    assert restaurants == []
    assert meta["count"] == 0


def test_main_uses_fallback_input_when_default_missing(tmp_path, monkeypatch):
    default_input = tmp_path / "missing-enriched.json"
    fallback_input = tmp_path / "fallback.json"
    output_path = tmp_path / "data.js"
    fallback_input.write_text(json.dumps(_sample_restaurants(), ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(generate_data_js, "DEFAULT_INPUT", default_input)
    monkeypatch.setattr(generate_data_js, "FALLBACK_INPUT", fallback_input)
    monkeypatch.setattr(generate_data_js, "OUTPUT_PATH", output_path)
    monkeypatch.setattr(generate_data_js, "datetime", FixedDatetime)
    monkeypatch.setattr(sys, "argv", ["generate_data_js.py"])

    generate_data_js.main()

    assert output_path.exists()
    restaurants, meta = _parse_data_js(output_path.read_text(encoding="utf-8"))
    assert len(restaurants) == 2
    assert meta["count"] == 2


def test_main_exits_when_input_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_data_js, "DEFAULT_INPUT", tmp_path / "missing-default.json")
    monkeypatch.setattr(generate_data_js, "FALLBACK_INPUT", tmp_path / "missing-fallback.json")
    monkeypatch.setattr(sys, "argv", ["generate_data_js.py"])

    with pytest.raises(SystemExit) as exc:
        generate_data_js.main()

    assert exc.value.code == 1


def test_main_exits_nonzero_when_generated_count_is_zero(tmp_path, monkeypatch):
    default_input = tmp_path / "default.json"
    fallback_input = tmp_path / "fallback.json"
    output_path = tmp_path / "data.js"
    default_input.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(generate_data_js, "DEFAULT_INPUT", default_input)
    monkeypatch.setattr(generate_data_js, "FALLBACK_INPUT", fallback_input)
    monkeypatch.setattr(generate_data_js, "OUTPUT_PATH", output_path)
    monkeypatch.setattr(generate_data_js, "datetime", FixedDatetime)
    monkeypatch.setattr(sys, "argv", ["generate_data_js.py"])

    with pytest.raises(SystemExit) as exc:
        generate_data_js.main()

    assert exc.value.code == 1
