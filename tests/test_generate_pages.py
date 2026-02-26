import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import scripts.generate_pages as generate_pages

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _sample_restaurants() -> list[dict]:
    return json.loads((FIXTURES_DIR / "sample_restaurants.json").read_text(encoding="utf-8"))


def test_sanitize_external_url_allows_only_http_schemes():
    assert generate_pages.sanitize_external_url("https://example.com") == "https://example.com"
    assert generate_pages.sanitize_external_url("http://example.com/path") == "http://example.com/path"
    assert generate_pages.sanitize_external_url("javascript:alert(1)") == ""
    assert generate_pages.sanitize_external_url("/relative/path") == ""


def test_build_meta_description_includes_main_fields():
    desc = generate_pages.build_meta_description(_sample_restaurants()[0])

    assert "La Tasca" in desc
    assert "Mediterránea, de mercado" in desc
    assert "Centro" in desc
    assert "8.7/10" in desc
    assert "~55 €" in desc


def test_build_jsonld_outputs_valid_restaurant_schema():
    ld = json.loads(generate_pages.build_jsonld(_sample_restaurants()[0]))

    assert ld["@context"] == "https://schema.org"
    assert ld["@type"] == "Restaurant"
    assert ld["name"] == "La Tasca"
    assert ld["servesCuisine"] == ["Mediterránea", "de mercado"]
    assert ld["aggregateRating"]["ratingValue"] == 8.7
    assert ld["aggregateRating"]["bestRating"] == 10
    assert ld["aggregateRating"]["worstRating"] == 0
    assert ld["aggregateRating"]["ratingCount"] == 1
    assert ld["sameAs"] == "https://latasca.example.com"
    assert ld["geo"] == {"@type": "GeoCoordinates", "latitude": 40.4167, "longitude": -3.70325}


def test_build_page_contains_required_metadata_and_links():
    html = generate_pages.build_page(_sample_restaurants()[0])

    assert "<meta property=\"og:type\" content=\"restaurant\">" in html
    assert "<meta property=\"og:image:width\" content=\"1200\">" in html
    assert "<meta property=\"og:image:height\" content=\"630\">" in html
    assert "<meta name=\"twitter:card\" content=\"summary_large_image\">" in html
    assert "<script type=\"application/ld+json\">" in html
    assert "rel=\"noopener noreferrer\"" in html
    assert "Ver en Google Maps" in html
    assert "<a href=\"/\" class=\"back\">" in html


def test_build_page_omits_links_for_unsafe_external_urls():
    row = _sample_restaurants()[0].copy()
    row["website"] = "javascript:alert(1)"
    row["macarfi_url"] = "ftp://macarfi.example.com"

    html = generate_pages.build_page(row)

    assert ">Web<" not in html
    assert ">Fuente<" not in html


def test_build_page_without_coordinates_omits_map_button():
    row = _sample_restaurants()[0].copy()
    row["latitude"] = ""
    row["longitude"] = ""

    html = generate_pages.build_page(row)

    assert "Ver en Google Maps" not in html


def test_build_sitemap_contains_home_and_restaurant_urls():
    restaurants = _sample_restaurants()

    xml_text = generate_pages.build_sitemap(restaurants, "2026-02-26")
    root = ET.fromstring(xml_text)
    locs = [n.text for n in root.findall("sm:url/sm:loc", SITEMAP_NS)]

    assert f"{generate_pages.BASE_URL}/" in locs
    assert f"{generate_pages.BASE_URL}/r/la-tasca.html" in locs
    assert f"{generate_pages.BASE_URL}/r/casa-norte.html" in locs
    assert len(locs) == 3


def test_main_generates_pages_and_sitemap(tmp_path, monkeypatch):
    restaurants = _sample_restaurants()
    input_path = tmp_path / "restaurants.json"
    pages_dir = tmp_path / "r"
    sitemap_path = tmp_path / "sitemap.xml"
    input_path.write_text(json.dumps(restaurants, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(generate_pages, "PAGES_DIR", pages_dir)
    monkeypatch.setattr(generate_pages, "SITEMAP_PATH", sitemap_path)
    monkeypatch.setattr(sys, "argv", ["generate_pages.py", "--input", str(input_path)])

    generate_pages.main()

    assert (pages_dir / "la-tasca.html").exists()
    assert (pages_dir / "casa-norte.html").exists()
    assert sitemap_path.exists()

    sitemap = ET.fromstring(sitemap_path.read_text(encoding="utf-8"))
    locs = [n.text for n in sitemap.findall("sm:url/sm:loc", SITEMAP_NS)]
    assert len(locs) == 3
