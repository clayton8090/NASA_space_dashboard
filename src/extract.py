import json
import os

import keyring
import requests
from dotenv import load_dotenv

load_dotenv()


def get_api_key():
    """Read the key from the environment, then fall back to the system keychain."""
    key = os.getenv("NASA_API_KEY") or keyring.get_password(
        "nasa-space-dashboard", "NASA_API_KEY"
    )
    if not key:
        raise RuntimeError("NASA API key not found in environment or keychain")
    return key


def fetch_apod():
    """Fetch today's Astronomy Picture of the Day."""
    response = requests.get(
        "https://api.nasa.gov/planetary/apod",
        headers={"X-Api-Key": get_api_key()},
        timeout=30,
    )
    response.raise_for_status()
    print("Requests remaining:", response.headers.get("X-RateLimit-Remaining"))
    return response.json()


if __name__ == "__main__":
    print(json.dumps(fetch_apod(), indent=2))
