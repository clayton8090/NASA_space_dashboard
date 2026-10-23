"""Phase 1 and 5: fetch raw data from NASA's APIs, with retries and clear errors."""
import json
import logging
import os
from datetime import date, timedelta
from pathlib import Path

import keyring
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()
log = logging.getLogger(__name__)

NASA_URL = "https://api.nasa.gov"
APOD_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"
DONKI_URL = "https://ccmc.gsfc.nasa.gov/DONKI-API/get"
RAW_DIR = Path("data/raw")
LOOKBACK_DAYS = 6  # NeoWs allows at most a 7-day window
LOW_QUOTA_WARNING = 100


def get_api_key():
    """Read the key from the environment, then fall back to the system keychain."""
    key = os.getenv("NASA_API_KEY") or keyring.get_password(
        "nasa-space-dashboard", "NASA_API_KEY"
    )
    if not key:
        raise RuntimeError("NASA API key not found in environment or keychain")
    return key


def _session():
    """A requests session that retries temporary failures (429 and 5xx) with growing waits."""
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
        raise_on_status=False,  # hand back the last response so we raise one clear error ourselves
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _parse_json(response, url):
    """Return the JSON body, or raise a clear error if the server sent something else (a web page)."""
    try:
        return response.json()
    except ValueError:
        kind = response.headers.get("Content-Type", "unknown type")
        raise ValueError(f"{url} did not return JSON (got {kind})") from None


def _get(path, params=None):
    """Keyed request to api.nasa.gov (NeoWs). The key goes in a header, not the URL."""
    url = f"{NASA_URL}{path}"
    response = _session().get(
        url, params=params, headers={"X-Api-Key": get_api_key()}, timeout=30
    )
    response.raise_for_status()
    remaining = response.headers.get("X-RateLimit-Remaining")
    log.info("%s -> ok, requests remaining: %s", path, remaining)
    if remaining is not None and remaining.isdigit() and int(remaining) < LOW_QUOTA_WARNING:
        log.warning("NASA API quota is low: %s requests remaining", remaining)
    return _parse_json(response, url)


def _get_public(url, params=None):
    """Keyless request. Never sends our NASA key to other hosts."""
    response = _session().get(url, params=params, timeout=30)
    response.raise_for_status()
    log.info("%s -> ok", url)
    return _parse_json(response, url)


def fetch_apod():
    """Newest Astronomy Picture of the Day, from NASA Science's endpoint."""
    data = _get_public(APOD_URL, {"per_page": 1})
    return data[0] if isinstance(data, list) and data else data


def fetch_neo_feed(start_date, end_date):
    """Near-Earth objects (asteroids) approaching between two dates."""
    return _get(
        "/neo/rest/v1/feed",
        {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
    )


def fetch_donki_flares(start_date, end_date):
    """Solar flare events between two dates, from CCMC's DONKI API."""
    return _get_public(
        f"{DONKI_URL}/FLR",
        {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()},
    )


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
        except (requests.exceptions.RequestException, ValueError) as exc:
            failures[name] = str(exc)
            log.error("%s: FAILED (%s)", name, exc)
            continue
        save_raw(name, data)
        results[name] = data
    return results, failures


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    fetched, failed = fetch_all()
    print("Fetched:", ", ".join(fetched) or "nothing")
    if failed:
        print("Failed sources:", ", ".join(failed))
