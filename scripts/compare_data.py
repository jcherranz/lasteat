"""Compare two restaurant datasets and report added/removed/changed entries.

Supports:
- JSON array files with full keys (e.g. output/madrid_restaurants.json)
- docs/data.js-style files containing `const RESTAURANTS=[...]`
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

KEY_MAP = {
    "name": "n",
    "slug": "s",
    "address": "a",
    "latitude": "lat",
    "longitude": "lng",
    "cuisine": "c",
    "district": "d",
    "rating": "r",
    "rating_food": "rf",
    "rating_decor": "rd",
    "rating_service": "rs",
    "price_eur": "p",
    "phone": "ph",
    "website": "w",
    "macarfi_url": "u",
}

COMPARE_FIELDS = [
    "name",
    "address",
    "latitude",
    "longitude",
    "cuisine",
    "district",
    "rating",
    "rating_food",
    "rating_decor",
    "rating_service",
    "price_eur",
    "phone",
    "website",
    "macarfi_url",
]


def _extract_data_js_array(text: str) -> list[dict[str, Any]]:
    match = re.search(r"const\s+RESTAURANTS\s*=\s*(\[.*?\])\s*;", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Could not find RESTAURANTS array in data.js file")
    payload = match.group(1)
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("RESTAURANTS payload is not a list")
    return data


def _normalize_record(record: dict[str, Any]) -> dict[str, Any] | None:
    slug = record.get("slug") or record.get("s") or ""
    slug = str(slug).strip()
    if not slug:
        return None

    normalized: dict[str, Any] = {"slug": slug}
    for full, short in KEY_MAP.items():
        if full == "slug":
            continue
        value = record.get(full, record.get(short, ""))
        normalized[full] = "" if value is None else value
    return normalized


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")

    rows: Any
    if path.suffix.lower() == ".js" or "const RESTAURANTS" in text:
        rows = _extract_data_js_array(text)
    else:
        rows = json.loads(text)

    if not isinstance(rows, list):
        raise ValueError(f"Input file {path} does not contain a JSON array")

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = _normalize_record(row)
        if item:
            normalized_rows.append(item)
    return normalized_rows


def compare_records(
    old_records: list[dict[str, Any]], new_records: list[dict[str, Any]]
) -> dict[str, Any]:
    old_by_slug = {r["slug"]: r for r in old_records if r.get("slug")}
    new_by_slug = {r["slug"]: r for r in new_records if r.get("slug")}

    old_slugs = set(old_by_slug)
    new_slugs = set(new_by_slug)

    added = sorted(new_slugs - old_slugs)
    removed = sorted(old_slugs - new_slugs)

    changed: list[dict[str, Any]] = []
    for slug in sorted(old_slugs & new_slugs):
        old = old_by_slug[slug]
        new = new_by_slug[slug]
        fields_changed = [
            field
            for field in COMPARE_FIELDS
            if str(old.get(field, "")) != str(new.get(field, ""))
        ]
        if fields_changed:
            changed.append({"slug": slug, "fields": fields_changed})

    old_count = len(old_records)
    removed_pct = (len(removed) / old_count * 100.0) if old_count else 0.0

    return {
        "old_count": old_count,
        "new_count": len(new_records),
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "removed_pct": removed_pct,
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def _print_summary(summary: dict[str, Any], sample_size: int = 10):
    print(
        "Dataset diff: "
        f"old={summary['old_count']} new={summary['new_count']} "
        f"added={summary['added_count']} removed={summary['removed_count']} "
        f"changed={summary['changed_count']}"
    )

    if summary["added_count"]:
        print("Added slugs (sample):", ", ".join(summary["added"][:sample_size]))
    if summary["removed_count"]:
        print("Removed slugs (sample):", ", ".join(summary["removed"][:sample_size]))
    if summary["changed_count"]:
        sample_changed = summary["changed"][:sample_size]
        for item in sample_changed:
            print(f"Changed {item['slug']}: {', '.join(item['fields'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two restaurant datasets by slug")
    parser.add_argument("old", type=Path, help="Path to old dataset (.json or docs/data.js)")
    parser.add_argument("new", type=Path, help="Path to new dataset (.json or docs/data.js)")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write a JSON diff summary",
    )
    parser.add_argument(
        "--max-removed-pct",
        type=float,
        default=None,
        help="Fail with exit code 2 if removed percentage exceeds this threshold",
    )

    args = parser.parse_args()

    old_records = load_records(args.old)
    new_records = load_records(args.new)
    summary = compare_records(old_records, new_records)

    _print_summary(summary)

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote diff report: {args.json_out}")

    if args.max_removed_pct is not None and summary["removed_pct"] > args.max_removed_pct:
        print(
            "Error: removed percentage exceeds threshold "
            f"({summary['removed_pct']:.2f}% > {args.max_removed_pct:.2f}%)",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
