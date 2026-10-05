import json
import os
from datetime import date, timedelta
from pathlib import Path

import keyring
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.nasa.gov"
RAW_DIR = Path("data/raw")
LOOKBACK_DAYS = 6  # NeoWs allows at most a 7-day window


def get_api_key():
    """Read the key from the environment, then fall back to the system keychain."""
    key = os.getenv("NASA_API_KEY") or keyring.get_password(
        "nasa-space-dashboard", "NASA_API_KEY"
    )
    if not key:
        raise RuntimeError("NASA API key not found in environment or keychain")
    return key


def _get(path, params=None):
    """Shared request helper: auth header, timeout, error check, quota logging."""
    response = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        headers={"X-Api-Key": get_api_key()},
        timeout=30,
    )
    response.raise_for_status()
    print(f"{path} -> requests remaining:", response.headers.get("X-RateLimit-Remaining"))
    if not response.content.strip():
        return None  # some endpoints (DONKI) send an empty body when there is no data
    return response.json()


def fetch_apod():
    """Today's Astronomy Picture of the Day."""
    return _get("/planetary/apod")


def fetch_neo_feed(start_date, end_date):
    """Near-Earth objects (asteroids) approaching between two dates."""
    return _get(
        "/neo/rest/v1/feed",
        {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
    )


def fetch_donki_flares(start_date, end_date):
    """Solar flare events between two dates."""
    data = _get(
        "/DONKI/FLR",
        {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()},
    )
    return data or []  # empty response means no flares in this window


def save_raw(name, data):
    """Keep an untouched copy of each response so we can reprocess without re-calling the API."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}_{date.today().isoformat()}.json"
    path.write_text(json.dumps(data, indent=2))
    return path


def fetch_all():
    """Fetch every source independently so one failure doesn't stop the rest."""
    end = date.today()
    start = end - timedelta(days=LOOKBACK_DAYS)
    sources = {
        "apod": lambda: fetch_apod(),
        "neo": lambda: fetch_neo_feed(start, end),
        "donki_flares": lambda: fetch_donki_flares(start, end),
    }
    results, failures = {}, {}
    for name, fetch in sources.items():
        try:
            data = fetch()
        except requests.exceptions.RequestException as exc:
            failures[name] = str(exc)
            print(f"{name}: FAILED ({exc})")
            continue
        save_raw(name, data)
        results[name] = data
    return results, failures


if __name__ == "__main__":
    results, failures = fetch_all()
    print()
    if "apod" in results:
        print("APOD title:    ", results["apod"].get("title"))
    if "neo" in results:
        print("Asteroids:     ", results["neo"].get("element_count"))
    if "donki_flares" in results:
        print("Solar flares:  ", len(results["donki_flares"]))
    if failures:
        print("Failed sources:", ", ".join(failures))
