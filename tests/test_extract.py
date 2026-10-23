"""Phase 5: tests for extraction behavior that doesn't need the network."""
from types import SimpleNamespace

import pytest
import requests

from src import extract


def test_parse_json_returns_data():
    response = SimpleNamespace(json=lambda: {"ok": True}, headers={})
    assert extract._parse_json(response, "https://example.com") == {"ok": True}


def test_parse_json_gives_a_clear_error_for_web_pages():
    def not_json():
        raise ValueError("no json here")

    response = SimpleNamespace(json=not_json, headers={"Content-Type": "text/html"})
    with pytest.raises(ValueError, match="did not return JSON"):
        extract._parse_json(response, "https://example.com/x")


def test_api_key_comes_from_environment_first(monkeypatch):
    monkeypatch.setenv("NASA_API_KEY", "from-env")
    assert extract.get_api_key() == "from-env"


def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("NASA_API_KEY", raising=False)
    monkeypatch.setattr(extract.keyring, "get_password", lambda *a, **k: None)
    with pytest.raises(RuntimeError, match="not found"):
        extract.get_api_key()


def test_one_failing_source_does_not_stop_the_others(monkeypatch, tmp_path):
    monkeypatch.setattr(extract, "RAW_DIR", tmp_path)

    def broken():
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr(extract, "fetch_apod", broken)
    monkeypatch.setattr(extract, "fetch_neo_feed", lambda s, e: {"near_earth_objects": {}})
    monkeypatch.setattr(extract, "fetch_donki_flares", lambda s, e: [])

    results, failures = extract.fetch_all()
    assert set(results) == {"neo", "donki_flares"}
    assert list(failures) == ["apod"]
    assert list(tmp_path.glob("neo_*.json"))  # raw copy was still saved
