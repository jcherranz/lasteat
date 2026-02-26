from pathlib import Path

import httpx
import pytest

import scraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fixture_html() -> str:
    return (FIXTURES_DIR / "macarfi_cards.html").read_text(encoding="utf-8")


def _valid_restaurant(i: int) -> dict:
    return {
        "name": f"Rest {i}",
        "slug": f"rest-{i}",
        "address": "Calle Test 1, Madrid",
        "latitude": "40.4",
        "longitude": "-3.7",
        "rating": "8.0",
        "cuisine": "Mediterránea",
        "district": "Centro",
        "rating_food": "8.1",
        "rating_decor": "7.9",
        "rating_service": "8.0",
        "price_eur": "45",
    }


def _response(status_code: int) -> httpx.Response:
    request = httpx.Request("GET", "https://example.com")
    return httpx.Response(status_code, request=request, text="ok")


class SequenceClient:
    def __init__(self, outcomes):
        self._outcomes = iter(outcomes)
        self.calls = 0

    def get(self, _url):
        self.calls += 1
        outcome = next(self._outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_parse_html_cards_extracts_expected_fields():
    extras = scraper.parse_html_cards(_fixture_html())

    assert "la-tasca" in extras
    assert extras["la-tasca"]["cuisine"] == "Mediterránea, de mercado"
    assert extras["la-tasca"]["district"] == "Chamberí"
    assert extras["la-tasca"]["rating_food"] == "8.6"
    assert extras["la-tasca"]["rating_decor"] == "8.2"
    assert extras["la-tasca"]["rating_service"] == "8.4"
    assert extras["la-tasca"]["price_eur"] == "65"


def test_parse_html_cards_ignores_cards_without_extractable_info():
    extras = scraper.parse_html_cards(_fixture_html())

    assert "sin-detalle" not in extras
    assert len(extras) == 1


def test_merge_data_combines_map_and_html_extras():
    merged = scraper.merge_data(
        [
            {
                "name": "La Tasca",
                "slug": "la-tasca",
                "address": "Calle Mayor 1",
                "latitude": "40.4",
                "longitude": "-3.7",
                "rating": "8,9",
            }
        ],
        {"la-tasca": {"cuisine": "Mediterránea", "district": "Centro", "price_eur": "65"}},
    )

    assert len(merged) == 1
    assert merged[0]["slug"] == "la-tasca"
    assert merged[0]["rating"] == "8.9"
    assert merged[0]["cuisine"] == "Mediterránea"
    assert merged[0]["district"] == "Centro"
    assert merged[0]["price_eur"] == "65"
    assert merged[0]["macarfi_url"].endswith("/la-tasca")


def test_merge_data_skips_entries_with_missing_slug_and_logs(capsys):
    merged = scraper.merge_data(
        [
            {
                "name": "Sin slug",
                "slug": "",
                "address": "Test",
                "latitude": "40.4",
                "longitude": "-3.7",
                "rating": "8.0",
            }
        ],
        {},
    )

    out = capsys.readouterr().out
    assert merged == []
    assert "missing slug" in out


def test_validate_data_accepts_valid_dataset():
    restaurants = [_valid_restaurant(i) for i in range(scraper.MIN_RESTAURANTS)]
    assert scraper.validate_data(restaurants) == []


def test_validate_data_rejects_low_restaurant_count():
    restaurants = [_valid_restaurant(i) for i in range(scraper.MIN_RESTAURANTS - 1)]

    errors = scraper.validate_data(restaurants)

    assert any("minimum" in err for err in errors)


def test_validate_data_rejects_low_cuisine_coverage():
    restaurants = [_valid_restaurant(i) for i in range(scraper.MIN_RESTAURANTS)]
    for i in range(200):
        restaurants[i]["cuisine"] = ""

    errors = scraper.validate_data(restaurants)

    assert any("cuisine data" in err for err in errors)


def test_validate_data_rejects_low_coordinate_coverage():
    restaurants = [_valid_restaurant(i) for i in range(scraper.MIN_RESTAURANTS)]
    for i in range(80):
        restaurants[i]["latitude"] = ""

    errors = scraper.validate_data(restaurants)

    assert any("coordinates" in err for err in errors)


def test_strict_coverage_errors_flags_low_field_coverage():
    restaurants = [_valid_restaurant(i) for i in range(100)]
    for i in range(25):
        restaurants[i]["rating_service"] = ""

    errors = scraper.strict_coverage_errors(restaurants)

    assert any(err.startswith("rating_service coverage") for err in errors)


def test_strict_coverage_errors_for_empty_input():
    assert scraper.strict_coverage_errors([]) == ["No restaurants found for strict validation"]


def test_fetch_with_retry_retries_on_server_error_then_succeeds(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda _s: None)
    client = SequenceClient([_response(500), _response(200)])

    resp = scraper._fetch_with_retry(client, "https://example.com", retries=3)

    assert resp.status_code == 200
    assert client.calls == 2


def test_fetch_with_retry_retries_on_timeout_then_succeeds(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda _s: None)
    timeout = httpx.TimeoutException("timeout", request=httpx.Request("GET", "https://example.com"))
    client = SequenceClient([timeout, _response(200)])

    resp = scraper._fetch_with_retry(client, "https://example.com", retries=3)

    assert resp.status_code == 200
    assert client.calls == 2


def test_fetch_with_retry_raises_after_exhausting_timeouts(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda _s: None)
    timeout = httpx.TimeoutException("timeout", request=httpx.Request("GET", "https://example.com"))
    client = SequenceClient([timeout, timeout, timeout])

    with pytest.raises(httpx.TimeoutException):
        scraper._fetch_with_retry(client, "https://example.com", retries=3)

    assert client.calls == 3


def test_fetch_with_retry_raises_http_status_on_final_500(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda _s: None)
    client = SequenceClient([_response(500), _response(500), _response(500)])

    with pytest.raises(httpx.HTTPStatusError):
        scraper._fetch_with_retry(client, "https://example.com", retries=3)

    assert client.calls == 3
