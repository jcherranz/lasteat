"""
Generate docs/data.js from scraper output JSON.

Reads the enriched (or base) restaurant JSON and produces a compact
JavaScript file with abbreviated keys for the frontend.

Usage:
    python scripts/generate_data_js.py                          # default paths
    python scripts/generate_data_js.py --input path/to/data.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "output" / "enriched_details.json"
FALLBACK_INPUT = PROJECT_ROOT / "output" / "madrid_restaurants.json"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "data.js"

# Full key → abbreviated key mapping (must match frontend expectations)
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


def abbreviate(record: dict) -> dict:
    """Convert a full-key restaurant record to abbreviated keys."""
    return {short: record.get(full, "") for full, short in KEY_MAP.items()}


def generate(input_path: Path, output_path: Path) -> int:
    """Read input JSON, write docs/data.js. Returns restaurant count."""
    with open(input_path, encoding="utf-8") as f:
        restaurants = json.load(f)

    abbreviated = [abbreviate(r) for r in restaurants]

    now = datetime.now(timezone.utc)
    meta = {
        "updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(abbreviated),
    }

    # Single-line JSON array (matches original data.js format)
    json_str = json.dumps(abbreviated, ensure_ascii=False, separators=(",", ":"))
    meta_str = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))

    content = f"const RESTAURANTS={json_str};\nconst META={meta_str};\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated {output_path} — {len(abbreviated)} restaurants, updated {meta['updated']}")
    return len(abbreviated)


def main():
    # Parse --input flag
    input_path = DEFAULT_INPUT
    if "--input" in sys.argv:
        idx = sys.argv.index("--input")
        if idx + 1 < len(sys.argv):
            input_path = Path(sys.argv[idx + 1])

    # Fall back to non-enriched if enriched doesn't exist
    if not input_path.exists() and input_path == DEFAULT_INPUT:
        input_path = FALLBACK_INPUT

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    count = generate(input_path, OUTPUT_PATH)
    if count == 0:
        print("Warning: generated data.js with 0 restaurants", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
