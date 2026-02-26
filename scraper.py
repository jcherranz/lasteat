"""
Last Eat — Madrid restaurant scraper (Macarfi source).

Scrapes all restaurants from https://macarfi.com/es/mad/restaurantes
and exports them as a CSV ready to import into Google My Maps.

Strategy:
  1. Hit the internal search API which returns all 770 restaurants with
     name, address, coordinates, and rating in a single JSON response.
  2. Parse the HTML fragment in the same response to extract cuisine type,
     individual ratings (food/decor/service), and price per restaurant.
  3. Optionally enrich with detail pages for phone, website, district.
  4. Export Google My Maps-compatible CSV + full JSON.
"""

import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://macarfi.com"
SEARCH_API = f"{BASE_URL}/mad/restaurants/search"
OUTPUT_DIR = Path(__file__).parent / "output"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept": "application/json, text/html, */*",
    "X-Requested-With": "XMLHttpRequest",
}

REQUEST_DELAY = 1.0


def get_client() -> httpx.Client:
    return httpx.Client(
        headers=HEADERS,
        follow_redirects=True,
        timeout=60.0,
    )


# ── Step 1: Fetch all restaurants via the search API ─────────────────────────


def fetch_all_restaurants(client: httpx.Client) -> tuple[list[dict], str]:
    """
    Single API call returns all restaurant map data + HTML cards.
    Returns (mapRestaurants list, html string).
    """
    print("Fetching restaurant data from Macarfi API...")
    resp = client.get(SEARCH_API, params={"location": 2, "page": 1})
    resp.raise_for_status()
    data = resp.json()

    total = data.get("total", 0)
    restaurants = data.get("mapRestaurants", [])
    html = data.get("html", "")

    print(f"API reports {total} restaurants, received {len(restaurants)} entries.")
    return restaurants, html


def parse_html_cards(html: str) -> dict[str, dict]:
    """
    Parse the HTML card grid to extract extra info per restaurant:
    cuisine, individual ratings, price, district.
    Returns a dict keyed by restaurant slug.
    """
    soup = BeautifulSoup(html, "lxml")
    extras = {}

    for card in soup.find_all("div", class_="card"):
        # Find the link to identify the restaurant
        link = card.find("a", href=re.compile(r"/ficha-restaurante/"))
        if not link:
            continue
        href = link.get("href", "")
        slug = href.rstrip("/").split("/")[-1]

        info = {}

        # Cuisine type (e.g., "Creativa, de autor")
        cuisine_el = card.find("p", class_=re.compile(r"text-gray-dark.*uppercase"))
        if cuisine_el:
            info["cuisine"] = cuisine_el.get_text(strip=True)

        # District (near location icon)
        location_div = card.find("div", class_=re.compile(r"flex.*items-center.*text-xs"))
        if location_div:
            info["district"] = location_div.get_text(strip=True)

        # Ratings: look for the rating grid at the bottom
        rating_divs = card.find_all("div", class_="grow")
        for rdiv in rating_divs:
            value_el = rdiv.find("p", class_=re.compile(r"text-xl"))
            label_el = rdiv.find("p", class_=re.compile(r"text-gray-dark.*text-sm"))
            if value_el and label_el:
                label = label_el.get_text(strip=True)
                value = value_el.get_text(strip=True).replace(",", ".")
                if "Comida" in label:
                    info["rating_food"] = value
                elif "Decoración" in label or "Decoracion" in label:
                    info["rating_decor"] = value
                elif "Servicio" in label:
                    info["rating_service"] = value

        # Price
        price_el = card.find(string=re.compile(r"\d+\s*€"))
        if price_el:
            m = re.search(r"(\d+)\s*€", price_el)
            if m:
                info["price_eur"] = m.group(1)

        if info:
            extras[slug] = info

    return extras


# ── Step 2 (optional): Enrich from detail pages ─────────────────────────────


def _fetch_with_retry(client: httpx.Client, url: str, retries: int = 3) -> httpx.Response:
    """Fetch a URL with exponential backoff for transient errors."""
    for attempt in range(retries):
        try:
            resp = client.get(url)
            if resp.status_code >= 500 and attempt < retries - 1:
                wait = 2 ** attempt
                print(f"  Server error {resp.status_code}, retrying in {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except (httpx.TimeoutException, httpx.RequestError) as err:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"  {err.__class__.__name__}, retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Unreachable retry state")


def enrich_from_detail(client: httpx.Client, restaurant: dict) -> dict:
    """Fetch a restaurant detail page to get phone, website, and price."""
    url = f"{BASE_URL}/es/mad/ficha-restaurante/{restaurant['slug']}"
    try:
        resp = _fetch_with_retry(client, url)
    except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as e:
        restaurant["_enrich_error"] = str(e)
        return restaurant

    soup = BeautifulSoup(resp.text, "lxml")

    # Phone
    phone_link = soup.find("a", href=re.compile(r"^tel:"))
    if phone_link:
        restaurant["phone"] = phone_link["href"].replace("tel:", "")

    # Website
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        if ("web" in text or "www" in href) and "macarfi" not in href:
            if href.startswith("http") and "macarfi" not in href:
                restaurant["website"] = href
                break

    # Price — look for "Precio" label near a euro value
    precio_el = soup.find(string=re.compile(r"Precio"))
    if precio_el:
        parent = precio_el.find_parent()
        if parent:
            # The price value is typically in a sibling/adjacent element
            container = parent.find_parent()
            if container:
                price_match = re.search(r"(\d+)\s*€", container.get_text())
                if price_match:
                    restaurant["price_eur"] = price_match.group(1)
    # Fallback: search broader context
    if not restaurant.get("price_eur"):
        price_match = re.search(r"(\d{2,3})\s*€", soup.get_text())
        if price_match:
            restaurant["price_eur"] = price_match.group(1)

    return restaurant


# ── Step 3: Merge and export ─────────────────────────────────────────────────


def merge_data(
    map_restaurants: list[dict], html_extras: dict[str, dict]
) -> list[dict]:
    """Merge API map data with HTML card extras into clean records."""
    merged = []
    skipped_missing_slug = 0
    for r in map_restaurants:
        slug = (r.get("slug") or "").strip()
        if not slug:
            skipped_missing_slug += 1
            continue
        entry = {
            "name": r.get("name", ""),
            "slug": slug,
            "address": r.get("address", ""),
            "latitude": r.get("latitude", ""),
            "longitude": r.get("longitude", ""),
            "rating": r.get("rating", "").replace(",", "."),
            "macarfi_url": f"{BASE_URL}/es/mad/ficha-restaurante/{slug}",
        }
        # Add extras from HTML cards
        extras = html_extras.get(slug, {})
        entry["cuisine"] = extras.get("cuisine", "")
        entry["district"] = extras.get("district", "")
        entry["rating_food"] = extras.get("rating_food", "")
        entry["rating_decor"] = extras.get("rating_decor", "")
        entry["rating_service"] = extras.get("rating_service", "")
        entry["price_eur"] = extras.get("price_eur", "")
        merged.append(entry)
    if skipped_missing_slug:
        print(f"Warning: skipped {skipped_missing_slug} restaurants with missing slug.")
    return merged


def enrich_all_details(client: httpx.Client, restaurants: list[dict]) -> list[dict]:
    """Enrich all restaurants with phone/website from detail pages."""
    print(f"\nEnriching {len(restaurants)} restaurants with detail pages...")
    print(f"Estimated time: ~{len(restaurants) * REQUEST_DELAY / 60:.0f} minutes")
    enriched = []
    errors = 0
    for r in tqdm(restaurants, desc="Enriching details"):
        time.sleep(REQUEST_DELAY)
        r = enrich_from_detail(client, r)
        if "_enrich_error" in r:
            errors += 1
        enriched.append(r)
    if errors:
        print(f"  {errors} enrichment errors (restaurants still included with basic data).")
    return enriched


def export_google_maps_csv(restaurants: list[dict], path: Path):
    """
    Export to CSV compatible with Google My Maps import.

    Google My Maps accepts CSV with columns:
    - Name (required)
    - Address OR (Latitude + Longitude)
    - Plus any extra columns shown as info in the map
    """
    fieldnames = [
        "Name",
        "Address",
        "Latitude",
        "Longitude",
        "Cuisine",
        "District",
        "Rating",
        "Rating (Food)",
        "Rating (Decor)",
        "Rating (Service)",
        "Price (EUR)",
        "Phone",
        "Website",
        "Macarfi URL",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in restaurants:
            writer.writerow({
                "Name": r.get("name", ""),
                "Address": r.get("address", ""),
                "Latitude": r.get("latitude", ""),
                "Longitude": r.get("longitude", ""),
                "Cuisine": r.get("cuisine", ""),
                "District": r.get("district", ""),
                "Rating": r.get("rating", ""),
                "Rating (Food)": r.get("rating_food", ""),
                "Rating (Decor)": r.get("rating_decor", ""),
                "Rating (Service)": r.get("rating_service", ""),
                "Price (EUR)": r.get("price_eur", ""),
                "Phone": r.get("phone", ""),
                "Website": r.get("website", ""),
                "Macarfi URL": r.get("macarfi_url", ""),
            })

    print(f"Google Maps CSV saved to: {path}")


def export_json(restaurants: list[dict], path: Path):
    """Export full scraped data as JSON."""
    clean = []
    for r in restaurants:
        entry = {k: v for k, v in r.items() if not k.startswith("_")}
        clean.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    print(f"Full JSON data saved to: {path}")


# ── Step 4 (extra pages): The API HTML only includes page 1 cards ────────────


def fetch_all_html_cards(client: httpx.Client, total_pages: int) -> str:
    """Fetch HTML cards from all pages to get cuisine/ratings/price for all restaurants."""
    all_html = ""
    for page in tqdm(range(1, total_pages + 1), desc="Fetching card pages"):
        if page > 1:
            time.sleep(REQUEST_DELAY)
        resp = client.get(SEARCH_API, params={"location": 2, "page": page})
        resp.raise_for_status()
        data = resp.json()
        all_html += data.get("html", "")
    return all_html


# ── Validation ───────────────────────────────────────────────────────────────

MIN_RESTAURANTS = 700
MIN_CUISINE_PCT = 0.90
STRICT_MIN_FIELD_PCT = 0.80


def validate_data(restaurants: list[dict[str, Any]]) -> list[str]:
    """Check scraped data meets quality thresholds. Returns list of errors."""
    errors = []
    total = len(restaurants)

    if total < MIN_RESTAURANTS:
        errors.append(f"Only {total} restaurants (minimum: {MIN_RESTAURANTS})")

    if total > 0:
        with_cuisine = sum(1 for r in restaurants if r.get("cuisine"))
        cuisine_pct = with_cuisine / total
        if cuisine_pct < MIN_CUISINE_PCT:
            errors.append(
                f"Only {cuisine_pct:.0%} have cuisine data (minimum: {MIN_CUISINE_PCT:.0%})"
            )

        with_coords = sum(1 for r in restaurants if r.get("latitude"))
        if with_coords < total * 0.95:
            errors.append(f"Only {with_coords}/{total} have coordinates")

    return errors


def strict_coverage_errors(restaurants: list[dict[str, Any]]) -> list[str]:
    """Return strict-mode errors when key fields drop below minimum coverage."""
    errors = []
    total = len(restaurants)
    if total == 0:
        return ["No restaurants found for strict validation"]

    fields = {
        "cuisine": lambda r: bool(r.get("cuisine")),
        "district": lambda r: bool(r.get("district")),
        "rating": lambda r: bool(r.get("rating")) and r.get("rating") != "-",
        "rating_food": lambda r: bool(r.get("rating_food")),
        "rating_decor": lambda r: bool(r.get("rating_decor")),
        "rating_service": lambda r: bool(r.get("rating_service")),
        "price_eur": lambda r: bool(r.get("price_eur")),
    }
    for field_name, predicate in fields.items():
        count = sum(1 for r in restaurants if predicate(r))
        pct = count / total
        if pct < STRICT_MIN_FIELD_PCT:
            errors.append(
                f"{field_name} coverage {pct:.0%} below {STRICT_MIN_FIELD_PCT:.0%} "
                f"({count}/{total})"
            )

    return errors


def log_missing_field_warnings(restaurants: list[dict[str, Any]], sample_limit: int = 10):
    """Print per-field warnings (with sample slugs) for key parsed fields."""
    checks = {
        "cuisine": lambda r: bool(r.get("cuisine")),
        "district": lambda r: bool(r.get("district")),
        "rating": lambda r: bool(r.get("rating")) and r.get("rating") != "-",
    }
    for field_name, predicate in checks.items():
        missing_slugs = [r.get("slug", "<missing-slug>") for r in restaurants if not predicate(r)]
        if not missing_slugs:
            continue
        print(f"Warning: missing {field_name} for {len(missing_slugs)} restaurants.")
        for slug in missing_slugs[:sample_limit]:
            print(f"  - No {field_name} found for {slug}")
        if len(missing_slugs) > sample_limit:
            print(f"  - ... and {len(missing_slugs) - sample_limit} more")


def build_quality_report(restaurants: list[dict[str, Any]]) -> dict[str, Any]:
    """Build per-field coverage report for scraper quality monitoring."""
    total = len(restaurants)
    fields = {
        "slug": lambda r: bool(r.get("slug")),
        "name": lambda r: bool(r.get("name")),
        "address": lambda r: bool(r.get("address")),
        "latitude": lambda r: bool(r.get("latitude")),
        "longitude": lambda r: bool(r.get("longitude")),
        "cuisine": lambda r: bool(r.get("cuisine")),
        "district": lambda r: bool(r.get("district")),
        "rating": lambda r: bool(r.get("rating")) and r.get("rating") != "-",
        "rating_food": lambda r: bool(r.get("rating_food")),
        "rating_decor": lambda r: bool(r.get("rating_decor")),
        "rating_service": lambda r: bool(r.get("rating_service")),
        "price_eur": lambda r: bool(r.get("price_eur")),
        "phone": lambda r: bool(r.get("phone")),
        "website": lambda r: bool(r.get("website")),
    }

    coverage: dict[str, dict[str, Any]] = {}
    for field_name, predicate in fields.items():
        count = sum(1 for r in restaurants if predicate(r))
        pct = (count / total) if total else 0.0
        coverage[field_name] = {"count": count, "pct": round(pct, 4)}

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": total,
        "fields": coverage,
    }


def export_quality_report(report: dict[str, Any], path: Path):
    """Write quality report JSON for CI trend checks."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Quality report saved to: {path}")


def compare_restaurant_sets(previous: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare previous vs current datasets by slug and report added/removed/changed."""
    old_by_slug = {r.get("slug"): r for r in previous if r.get("slug")}
    new_by_slug = {r.get("slug"): r for r in current if r.get("slug")}

    old_slugs = set(old_by_slug)
    new_slugs = set(new_by_slug)
    added = sorted(new_slugs - old_slugs)
    removed = sorted(old_slugs - new_slugs)

    compare_fields = [
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
    ]
    changed: list[dict[str, Any]] = []
    for slug in sorted(old_slugs & new_slugs):
        old = old_by_slug[slug]
        new = new_by_slug[slug]
        changed_fields = [
            field
            for field in compare_fields
            if str(old.get(field, "")) != str(new.get(field, ""))
        ]
        if changed_fields:
            changed.append({"slug": slug, "fields": changed_fields})

    return {
        "old_count": len(previous),
        "new_count": len(current),
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def _flag_value(flag: str) -> str | None:
    """Return value passed after a flag, if present and not another flag."""
    if flag not in sys.argv:
        return None
    idx = sys.argv.index(flag)
    if idx + 1 >= len(sys.argv):
        return None
    value = sys.argv[idx + 1]
    if value.startswith("--"):
        return None
    return value


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    enrich = "--enrich" in sys.argv
    fresh = "--fresh" in sys.argv
    strict = "--strict" in sys.argv
    compare = "--compare" in sys.argv
    compare_path_value = _flag_value("--compare")
    compare_path = Path(compare_path_value) if compare_path_value else OUTPUT_DIR / "madrid_restaurants.json"

    client = get_client()
    cache_path = OUTPUT_DIR / "api_data.json"
    previous_for_compare: list[dict[str, Any]] | None = None

    if compare:
        if compare_path.exists():
            try:
                with open(compare_path, encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, list):
                    previous_for_compare = loaded
                    print(f"Loaded comparison baseline from {compare_path} ({len(loaded)} records).")
                else:
                    print(f"Warning: compare baseline is not a list: {compare_path}")
            except json.JSONDecodeError as err:
                print(f"Warning: could not parse compare baseline {compare_path}: {err}")
        else:
            print(f"Warning: compare baseline not found: {compare_path}")

    if cache_path.exists() and not fresh:
        print(f"Loading cached data from {cache_path}")
        with open(cache_path, encoding="utf-8") as f:
            restaurants = json.load(f)
        print(f"Loaded {len(restaurants)} restaurants from cache.")
    else:
        # Step 1: Get all restaurant coordinates + basic data (single request)
        map_restaurants, html_page1 = fetch_all_restaurants(client)

        # The API gives all 770 map entries but HTML only shows ~15 per page.
        # Calculate how many pages we need for full HTML card data.
        total_restaurants = len(map_restaurants)
        restaurants_per_page = len(
            BeautifulSoup(html_page1, "lxml").find_all("div", class_="card")
        )
        if restaurants_per_page > 0:
            total_pages = (total_restaurants + restaurants_per_page - 1) // restaurants_per_page
        else:
            total_pages = 52  # fallback

        print(f"\n{restaurants_per_page} cards per page, {total_pages} pages to fetch for full data.")

        # Step 2: Fetch all HTML pages for cuisine/ratings/price
        all_html = fetch_all_html_cards(client, total_pages)
        html_extras = parse_html_cards(all_html)
        print(f"Parsed card data for {len(html_extras)} restaurants.")

        # Step 3: Merge
        restaurants = merge_data(map_restaurants, html_extras)

        # Cache
        export_json(restaurants, cache_path)

    log_missing_field_warnings(restaurants)

    # Optional: enrich with phone/website from detail pages
    if enrich:
        restaurants = enrich_all_details(client, restaurants)
        export_json(restaurants, OUTPUT_DIR / "enriched_details.json")

    # Export
    csv_path = OUTPUT_DIR / "madrid_restaurants.csv"
    export_google_maps_csv(restaurants, csv_path)

    json_path = OUTPUT_DIR / "madrid_restaurants.json"
    export_json(restaurants, json_path)

    quality_report_path = OUTPUT_DIR / "quality_report.json"
    quality_report = build_quality_report(restaurants)
    export_quality_report(quality_report, quality_report_path)

    if compare:
        if previous_for_compare is None:
            print("Compare requested but no valid baseline was available.")
        else:
            diff = compare_restaurant_sets(previous_for_compare, restaurants)
            print("\nCOMPARE REPORT")
            print(
                f"  old={diff['old_count']} new={diff['new_count']} "
                f"added={diff['added_count']} removed={diff['removed_count']} "
                f"changed={diff['changed_count']}"
            )
            if diff["added"]:
                print(f"  Added sample: {', '.join(diff['added'][:10])}")
            if diff["removed"]:
                print(f"  Removed sample: {', '.join(diff['removed'][:10])}")
            if diff["changed"]:
                for item in diff["changed"][:10]:
                    print(f"  Changed {item['slug']}: {', '.join(item['fields'])}")

    # Stats & warnings
    total = len(restaurants)
    fields = {
        "coordinates": sum(1 for r in restaurants if r.get("latitude")),
        "address": sum(1 for r in restaurants if r.get("address")),
        "cuisine": sum(1 for r in restaurants if r.get("cuisine")),
        "rating": sum(1 for r in restaurants if r.get("rating") and r["rating"] != "-"),
        "phone": sum(1 for r in restaurants if r.get("phone")),
    }
    print(f"\n{'='*50}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*50}")
    print(f"Total restaurants: {total}")
    for field, count in fields.items():
        pct = count / total * 100 if total else 0
        marker = " ⚠" if pct < 95 else ""
        print(f"  {field:15s} {count:>4d}/{total}  ({pct:.0f}%){marker}")
    print(f"\nOutput files:")
    print(f"  CSV (Google Maps): {csv_path}")
    print(f"  JSON (full data):  {json_path}")
    if not enrich:
        print(f"\nTip: Run with --enrich to also fetch phone/website (takes ~13 min)")

    # Validate data quality
    errors = validate_data(restaurants)
    if errors:
        print(f"\nVALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"\nValidation passed.")

    if strict:
        strict_errors = strict_coverage_errors(restaurants)
        if strict_errors:
            print(f"\nSTRICT VALIDATION FAILED:")
            for e in strict_errors:
                print(f"  - {e}")
            sys.exit(1)
        print("Strict validation passed.")


if __name__ == "__main__":
    main()
