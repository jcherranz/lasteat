"""Smoke checks for generated static site assets and React entry wiring.

Usage:
    python scripts/smoke_site.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
INDEX_PATH = DOCS_DIR / "index.html"
SW_PATH = DOCS_DIR / "sw.js"
DETAILS_DIR = DOCS_DIR / "r"


REQUIRED_DOC_FILES = [
    DOCS_DIR / "react-app.js",
    DOCS_DIR / "react-app.css",
    DOCS_DIR / "restaurant-app.js",
    DOCS_DIR / "restaurant-app.css",
    DOCS_DIR / "app.js",
    DOCS_DIR / "data.js",
    DOCS_DIR / "districts.geojson",
    DOCS_DIR / "sw.js",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_required_files() -> None:
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in REQUIRED_DOC_FILES if not path.exists()]
    if missing:
        fail(f"Missing required docs assets: {', '.join(missing)}")


def check_home_entry() -> None:
    text = INDEX_PATH.read_text(encoding="utf-8")
    required_snippets = [
        '<div id="root"></div>',
        '<link rel="stylesheet" href="react-app.css">',
        '<script type="module" src="react-app.js"></script>',
        '<script src="data.js"></script>',
    ]
    for snippet in required_snippets:
        if snippet not in text:
            fail(f"Homepage missing required snippet: {snippet}")


def extract_static_assets() -> list[str]:
    text = SW_PATH.read_text(encoding="utf-8")
    match = re.search(r"var\s+STATIC_ASSETS\s*=\s*(\[[\s\S]*?\]);", text)
    if not match:
        fail("Could not parse STATIC_ASSETS in docs/sw.js")
    try:
        return ast.literal_eval(match.group(1))
    except (SyntaxError, ValueError) as exc:
        fail(f"Invalid STATIC_ASSETS array in docs/sw.js: {exc}")
    return []


def check_service_worker_assets() -> None:
    assets = extract_static_assets()
    required = {
        "/react-app.js",
        "/react-app.css",
        "/restaurant-app.js",
        "/restaurant-app.css",
        "/data.js",
        "/districts.geojson",
    }
    missing = sorted(required - set(assets))
    if missing:
        fail(f"docs/sw.js STATIC_ASSETS missing: {', '.join(missing)}")


def check_detail_pages() -> None:
    pages = sorted(DETAILS_DIR.glob("*.html"))
    if not pages:
        fail("No generated detail pages found in docs/r/")

    checked = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        if '<div id="restaurant-root">' not in text:
            fail(f"Detail page missing restaurant root container: {page}")
        if '<script id="restaurant-data" type="application/json">' not in text:
            fail(f"Detail page missing embedded restaurant JSON: {page}")
        if '<script type="module" src="/restaurant-app.js"></script>' not in text:
            fail(f"Detail page missing React module script: {page}")
        if '<link rel="stylesheet" href="/restaurant-app.css">' not in text:
            fail(f"Detail page missing React stylesheet: {page}")
        checked += 1

    print(f"Checked {checked} detail pages")


def check_no_framer_references() -> None:
    targets = [
        DOCS_DIR / "react-app.js",
        DOCS_DIR / "restaurant-app.js",
        PROJECT_ROOT / "CLAUDE.md",
    ]
    patterns = ["framer-motion", "AnimatePresence", "motion.", "Framer Motion"]

    for path in targets:
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            if pattern in text:
                fail(f"Unexpected Framer reference '{pattern}' found in {path.relative_to(PROJECT_ROOT)}")


def main() -> int:
    check_required_files()
    check_home_entry()
    check_service_worker_assets()
    check_detail_pages()
    check_no_framer_references()
    print("Smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
