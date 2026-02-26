import json
import sys
from pathlib import Path

import pytest

import scripts.compare_data as compare_data

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _sample_full_records() -> list[dict]:
    return json.loads((FIXTURES_DIR / "sample_restaurants.json").read_text(encoding="utf-8"))


def test_load_records_reads_full_json(tmp_path):
    input_path = tmp_path / "restaurants.json"
    input_path.write_text(json.dumps(_sample_full_records(), ensure_ascii=False), encoding="utf-8")

    loaded = compare_data.load_records(input_path)

    assert len(loaded) == 2
    assert loaded[0]["slug"] == "la-tasca"
    assert loaded[0]["name"] == "La Tasca"


def test_load_records_reads_data_js_format(tmp_path):
    data_js = tmp_path / "data.js"
    data_js.write_text(
        'const RESTAURANTS=[{"n":"La Tasca","s":"la-tasca","r":"8.7"}];\nconst META={"count":1};\n',
        encoding="utf-8",
    )

    loaded = compare_data.load_records(data_js)

    assert len(loaded) == 1
    assert loaded[0]["slug"] == "la-tasca"
    assert loaded[0]["rating"] == "8.7"


def test_compare_records_detects_added_removed_changed():
    old = [
        {"slug": "a", "name": "A", "rating": "8.0"},
        {"slug": "b", "name": "B", "rating": "7.5"},
    ]
    new = [
        {"slug": "a", "name": "A updated", "rating": "8.0"},
        {"slug": "c", "name": "C", "rating": "9.1"},
    ]

    summary = compare_data.compare_records(old, new)

    assert summary["added"] == ["c"]
    assert summary["removed"] == ["b"]
    assert summary["added_count"] == 1
    assert summary["removed_count"] == 1
    assert summary["changed_count"] == 1
    assert summary["changed"][0]["slug"] == "a"
    assert "name" in summary["changed"][0]["fields"]


def test_main_writes_json_report_and_succeeds(tmp_path, monkeypatch):
    old_path = tmp_path / "old.json"
    new_path = tmp_path / "new.json"
    out_path = tmp_path / "diff.json"
    old_path.write_text('[{"slug":"a","name":"A"}]', encoding="utf-8")
    new_path.write_text('[{"slug":"a","name":"A"},{"slug":"b","name":"B"}]', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "compare_data.py",
        str(old_path),
        str(new_path),
        "--json-out",
        str(out_path),
    ])

    exit_code = compare_data.main()

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["added_count"] == 1
    assert payload["removed_count"] == 0


def test_main_fails_when_removed_pct_exceeds_threshold(tmp_path, monkeypatch):
    old_path = tmp_path / "old.json"
    new_path = tmp_path / "new.json"
    old_path.write_text('[{"slug":"a"},{"slug":"b"}]', encoding="utf-8")
    new_path.write_text('[{"slug":"a"}]', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "compare_data.py",
        str(old_path),
        str(new_path),
        "--max-removed-pct",
        "40",
    ])

    exit_code = compare_data.main()

    assert exit_code == 2
