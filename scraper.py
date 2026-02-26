"""
Macarfi Madrid restaurant scraper.

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
from pathlib import Path

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
        timeout=30.0,
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


def enrich_from_detail(client: httpx.Client, restaurant: dict) -> dict:
    """Fetch a restaurant detail page to get phone, website, and price."""
    url = f"{BASE_URL}/es/mad/ficha-restaurante/{restaurant['slug']}"
    try:
        resp = client.get(url)
        resp.raise_for_status()
    except Exception as e:
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
    for r in map_restaurants:
        slug = r.get("slug", "")
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


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    enrich = "--enrich" in sys.argv
    fresh = "--fresh" in sys.argv

    client = get_client()
    cache_path = OUTPUT_DIR / "api_data.json"

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

    # Optional: enrich with phone/website from detail pages
    if enrich:
        restaurants = enrich_all_details(client, restaurants)
        export_json(restaurants, OUTPUT_DIR / "enriched_details.json")

    # Export
    csv_path = OUTPUT_DIR / "macarfi_madrid_restaurants.csv"
    export_google_maps_csv(restaurants, csv_path)

    json_path = OUTPUT_DIR / "macarfi_madrid_restaurants.json"
    export_json(restaurants, json_path)

    # Stats
    with_coords = sum(1 for r in restaurants if r.get("latitude"))
    with_address = sum(1 for r in restaurants if r.get("address"))
    with_cuisine = sum(1 for r in restaurants if r.get("cuisine"))
    with_phone = sum(1 for r in restaurants if r.get("phone"))
    print(f"\n{'='*50}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*50}")
    print(f"Total restaurants: {len(restaurants)}")
    print(f"With coordinates:  {with_coords}")
    print(f"With address:      {with_address}")
    print(f"With cuisine:      {with_cuisine}")
    print(f"With phone:        {with_phone}")
    print(f"\nOutput files:")
    print(f"  CSV (Google Maps): {csv_path}")
    print(f"  JSON (full data):  {json_path}")
    print(f"\nTo import into Google My Maps:")
    print(f"  1. Go to https://www.google.com/maps/d/")
    print(f"  2. Create a new map")
    print(f"  3. Click 'Import' and upload the CSV file")
    print(f"  4. Select 'Latitude' and 'Longitude' as position columns")
    print(f"     (or 'Address' if coordinates are missing)")
    print(f"  5. Select 'Name' as the title column")
    if not enrich:
        print(f"\nTip: Run with --enrich to also fetch phone/website (takes ~13 min)")


if __name__ == "__main__":
    main()
