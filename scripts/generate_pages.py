"""
Generate individual restaurant HTML pages and sitemap.xml.

Reads the enriched (or base) restaurant JSON and produces:
  - docs/r/{slug}.html per restaurant (with OG tags, JSON-LD, map link)
  - docs/sitemap.xml listing all pages + homepage

Usage:
    python scripts/generate_pages.py
    python scripts/generate_pages.py --input path/to/data.json
"""

import json
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "output" / "enriched_details.json"
FALLBACK_INPUT = PROJECT_ROOT / "output" / "madrid_restaurants.json"
PAGES_DIR = PROJECT_ROOT / "docs" / "r"
SITEMAP_PATH = PROJECT_ROOT / "docs" / "sitemap.xml"
BASE_URL = "https://lasteat.es"


def sanitize_external_url(url: str) -> str:
    """Allow only absolute http(s) external URLs."""
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme.lower() in {"http", "https"} and parsed.netloc:
        return url
    return ""


def parse_float(value):
    """Parse numeric-like strings to float, returning None when invalid."""
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def build_meta_description(r: dict) -> str:
    """Build a concise meta description from restaurant data."""
    parts = [r.get("name", "")]
    if r.get("cuisine"):
        parts.append(r["cuisine"].replace("\u2022", ","))
    if r.get("district"):
        parts.append(r["district"])
    if r.get("rating") and r["rating"] != "-":
        parts.append(f'{r["rating"]}/10')
    if r.get("price_eur"):
        parts.append(f'~{r["price_eur"]} \u20ac')
    return " \u2014 ".join(parts)


def build_jsonld(r: dict) -> str:
    """Build schema.org/Restaurant JSON-LD structured data."""
    ld = {
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "name": r.get("name", ""),
        "url": f'{BASE_URL}/r/{r.get("slug", "")}.html',
    }
    if r.get("address"):
        ld["address"] = {
            "@type": "PostalAddress",
            "streetAddress": r["address"],
            "addressLocality": "Madrid",
            "addressCountry": "ES",
        }
    if r.get("cuisine"):
        ld["servesCuisine"] = [c.strip() for c in r["cuisine"].split(",") if c.strip()]

    rating_value = parse_float(r.get("rating"))
    if rating_value is not None:
        ld["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": rating_value,
            "bestRating": 10,
            "worstRating": 0,
            "ratingCount": 1,
        }
    if r.get("phone"):
        ld["telephone"] = r["phone"]
    if r.get("website"):
        ld["sameAs"] = r["website"]
    latitude = parse_float(r.get("latitude"))
    longitude = parse_float(r.get("longitude"))
    if latitude is not None and longitude is not None:
        ld["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": latitude,
            "longitude": longitude,
        }
    if r.get("price_eur"):
        ld["priceRange"] = f'{r["price_eur"]} \u20ac'
    return json.dumps(ld, ensure_ascii=False, indent=2)


def build_page(r: dict) -> str:
    """Build the full HTML page for a single restaurant."""
    name = escape(r.get("name", ""))
    slug = r.get("slug", "")
    address = escape(r.get("address", ""))
    district = escape(r.get("district", ""))
    cuisine = r.get("cuisine", "")
    rating = r.get("rating", "")
    rating_food = r.get("rating_food", "")
    rating_decor = r.get("rating_decor", "")
    rating_service = r.get("rating_service", "")
    price = r.get("price_eur", "")
    phone = r.get("phone", "")
    website = sanitize_external_url(r.get("website", ""))
    macarfi_url = sanitize_external_url(r.get("macarfi_url", ""))
    lat = r.get("latitude", "")
    lng = r.get("longitude", "")

    meta_desc = escape(build_meta_description(r))
    canonical = f"{BASE_URL}/r/{slug}.html"
    gmaps_url = f"https://www.google.com/maps/search/?api=1&query={quote(r.get('name', '') + ', ' + r.get('address', ''))}"
    jsonld = build_jsonld(r)

    # Cuisine tags
    cuisine_tags = ""
    if cuisine:
        tags = [c.strip() for c in cuisine.replace("\u2022", ",").split(",") if c.strip()]
        cuisine_tags = "".join(f'<span class="tag">{escape(t)}</span>' for t in tags)

    # Ratings breakdown
    ratings_html = ""
    rating_items = []
    if rating_food:
        rating_items.append(f'Comida <strong>{rating_food}</strong>')
    if rating_decor:
        rating_items.append(f'Decor <strong>{rating_decor}</strong>')
    if rating_service:
        rating_items.append(f'Servicio <strong>{rating_service}</strong>')
    if rating_items:
        ratings_html = f'<div class="ratings">{" &middot; ".join(rating_items)}</div>'

    # Contact links
    contact_parts = []
    if phone:
        contact_parts.append(f'<a href="tel:{phone.replace(" ", "")}">{escape(phone)}</a>')
    if website:
        contact_parts.append(f'<a href="{escape(website)}" target="_blank" rel="noopener noreferrer">Web</a>')
    if macarfi_url:
        contact_parts.append(f'<a href="{escape(macarfi_url)}" target="_blank" rel="noopener noreferrer">Fuente</a>')
    contact_html = ""
    if contact_parts:
        contact_html = f'<div class="contact">{" &middot; ".join(contact_parts)}</div>'

    rating_display = rating if rating and rating != "-" else "\u2014"
    price_display = f"{price} \u20ac" if price else ""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Last Eat</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical}">

<!-- Open Graph -->
<meta property="og:type" content="restaurant">
<meta property="og:title" content="{name} — Last Eat">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Last Eat">
<meta property="og:image" content="{BASE_URL}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{name} — Last Eat">
<meta name="twitter:description" content="{meta_desc}">
<meta name="twitter:image" content="{BASE_URL}/og.png">

<!-- Structured Data -->
<script type="application/ld+json">
{jsonld}
</script>

<style>
  :root {{
    --bg: #F5F4F1;
    --surface: #FFFFFF;
    --text: #1C1F1E;
    --secondary: #545957;
    --muted: #6E7472;
    --accent: #376660;
    --accent-soft: rgba(55, 102, 96, 0.06);
    --border: #E2E0DC;
    --radius: 5px;
  }}
  [data-theme="dark"] {{
    --bg: #131615;
    --surface: #1C201E;
    --text: #E4E6E4;
    --secondary: #9DA2A0;
    --muted: #7E8482;
    --accent: #45A194;
    --accent-soft: rgba(69, 161, 148, 0.09);
    --border: #292D2B;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'DM Sans', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }}
  .container {{
    max-width: 640px;
    margin: 0 auto;
    padding: 3rem 2rem;
  }}
  .back {{
    font-size: 0.78rem;
    color: var(--muted);
    text-decoration: none;
    letter-spacing: 0.04em;
    transition: color 0.2s;
  }}
  .back:hover {{ color: var(--accent); }}
  h1 {{
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 2.2rem;
    font-weight: 300;
    line-height: 1.2;
    margin: 1.5rem 0 0.5rem;
  }}
  .meta {{
    font-size: 0.78rem;
    color: var(--muted);
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 0;
  }}
  .meta span + span::before {{
    content: '\\00b7';
    margin: 0 0.35rem;
    color: var(--border);
  }}
  .score {{
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 3rem;
    font-weight: 500;
    color: var(--text);
    margin: 1.25rem 0 0.25rem;
    line-height: 1;
  }}
  .ratings {{
    font-size: 0.78rem;
    color: var(--muted);
    margin-bottom: 1rem;
  }}
  .ratings strong {{ color: var(--secondary); font-weight: 500; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 0.3rem; margin: 0.75rem 0; }}
  .tag {{
    font-size: 0.72rem;
    padding: 0.15rem 0.5rem;
    background: var(--accent-soft);
    color: var(--accent);
    border-radius: 3px;
  }}
  .card {{
    background: var(--surface);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    margin: 1.25rem 0;
    box-shadow: 0 0 0 1px rgba(0,0,0,0.03);
  }}
  .card-label {{
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 0.25rem;
  }}
  .card-value {{
    font-size: 0.88rem;
    color: var(--text);
    line-height: 1.5;
  }}
  .card-value a {{
    color: var(--accent);
    text-decoration: none;
  }}
  .card-value a:hover {{ text-decoration: underline; }}
  .contact {{
    font-size: 0.82rem;
    color: var(--muted);
    margin: 1rem 0;
  }}
  .contact a {{
    color: var(--accent);
    text-decoration: none;
  }}
  .contact a:hover {{ text-decoration: underline; }}
  .maps-btn {{
    display: inline-block;
    margin: 1rem 0;
    padding: 0.55rem 1.2rem;
    background: var(--accent);
    color: #fff;
    border-radius: var(--radius);
    font-size: 0.82rem;
    font-family: inherit;
    text-decoration: none;
    transition: opacity 0.2s;
  }}
  .maps-btn:hover {{ opacity: 0.85; }}
  footer {{
    text-align: center;
    padding: 2rem 1.5rem;
    font-size: 0.72rem;
    color: var(--muted);
  }}
  footer a {{
    color: var(--secondary);
    text-decoration: none;
    border-bottom: 1px solid var(--border);
    transition: border-color 0.2s, color 0.2s;
  }}
  footer a:hover {{ border-bottom-color: var(--accent); color: var(--accent); }}
  .theme-toggle {{
    position: fixed;
    top: 1.25rem;
    right: 1.5rem;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.1rem;
    color: var(--muted);
    padding: 0.25rem;
    transition: color 0.2s;
    line-height: 1;
  }}
  .theme-toggle::before {{ content: '\\263D'; }}
  [data-theme="dark"] .theme-toggle::before {{ content: '\\2600'; }}
  .theme-toggle:hover {{ color: var(--accent); }}
  @media (max-width: 640px) {{
    .container {{ padding: 2rem 1.25rem; }}
    h1 {{ font-size: 1.7rem; }}
    .score {{ font-size: 2.4rem; }}
  }}
</style>
</head>
<body>
<button class="theme-toggle" id="theme-toggle" aria-label="Cambiar tema"></button>
<div class="container">
  <a href="/" class="back">&larr; Last Eat</a>
  <h1>{name}</h1>
  <div class="meta">
    {f'<span>{district}</span>' if district else ''}
    {f'<span>{price_display}</span>' if price_display else ''}
  </div>
  {f'<div class="tags">{cuisine_tags}</div>' if cuisine_tags else ''}

  <div class="score">{rating_display}</div>
  {ratings_html}

  <div class="card">
    <div class="card-label">Direcci&oacute;n</div>
    <div class="card-value">{address if address else '&mdash;'}</div>
  </div>

  {contact_html}

  {f'<a href="{gmaps_url}" class="maps-btn" target="_blank" rel="noopener noreferrer">Ver en Google Maps</a>' if lat and lng else ''}
</div>

<footer>
  <a href="/">Last Eat</a> &mdash; Restaurantes en Madrid
</footer>

<script>
(function() {{
  var saved = null;
  try {{ saved = localStorage.getItem('mf-theme'); }} catch (_err) {{}}
  if (saved) document.documentElement.dataset.theme = saved;
  else if (window.matchMedia('(prefers-color-scheme: dark)').matches) document.documentElement.dataset.theme = 'dark';
  document.getElementById('theme-toggle').addEventListener('click', function() {{
    var t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = t;
    try {{ localStorage.setItem('mf-theme', t); }} catch (_err) {{}}
  }});
}})();
</script>
</body>
</html>"""


def build_sitemap(restaurants: list[dict], updated: str) -> str:
    """Build sitemap.xml with all restaurant pages and homepage."""
    urls = [f"""  <url>
    <loc>{BASE_URL}/</loc>
    <lastmod>{updated}</lastmod>
    <priority>1.0</priority>
  </url>"""]

    for r in restaurants:
        slug = r.get("slug", "")
        if slug:
            urls.append(f"""  <url>
    <loc>{BASE_URL}/r/{slug}.html</loc>
    <lastmod>{updated}</lastmod>
    <priority>0.7</priority>
  </url>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
"""


def main():
    # Parse --input flag
    input_path = DEFAULT_INPUT
    if "--input" in sys.argv:
        idx = sys.argv.index("--input")
        if idx + 1 < len(sys.argv):
            input_path = Path(sys.argv[idx + 1])

    if not input_path.exists() and input_path == DEFAULT_INPUT:
        input_path = FALLBACK_INPUT

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        restaurants = json.load(f)

    # Generate individual pages
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0
    for r in restaurants:
        slug = r.get("slug", "")
        if not slug:
            continue
        page_path = PAGES_DIR / f"{slug}.html"
        page_path.write_text(build_page(r), encoding="utf-8")
        generated += 1

    print(f"Generated {generated} restaurant pages in {PAGES_DIR}/")

    # Generate sitemap
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sitemap = build_sitemap(restaurants, now)
    SITEMAP_PATH.write_text(sitemap, encoding="utf-8")
    print(f"Generated {SITEMAP_PATH} with {generated + 1} URLs")


if __name__ == "__main__":
    main()
