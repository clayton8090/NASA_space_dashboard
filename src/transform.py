"""Phase 2: clean raw API responses into tidy pandas tables."""
import html
import re

import pandas as pd

NEO_COLUMNS = [
    "asteroid_id",
    "name",
    "approach_date",
    "diameter_min_m",
    "diameter_max_m",
    "velocity_kps",
    "miss_distance_km",
    "miss_distance_lunar",
    "is_hazardous",
]

FLARE_COLUMNS = [
    "flare_id",
    "begin_time",
    "peak_time",
    "end_time",
    "duration_min",
    "class_type",
    "class_letter",
    "class_magnitude",
    "source_location",
    "active_region",
]

APOD_COLUMNS = [
    "apod_date",
    "title",
    "media_type",
    "explanation",
    "credit",
    "credit_url",
    "image_url",
    "page_url",
]


# ---------- shared helpers ----------

def clean_html(text):
    """Strip tags, decode entities, collapse whitespace. Returns None if nothing is left."""
    if not text:
        return None
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def first_link(text):
    """Return the first href found in an HTML snippet, or None."""
    match = re.search(r'href="([^"]+)"', text or "")
    return match.group(1) if match else None


def _to_utc(value):
    """Parse a timestamp string into a UTC datetime, or None if missing/invalid."""
    if not value:
        return None
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    return None if pd.isna(ts) else ts


# ---------- NeoWs (asteroids) ----------

def transform_neo(raw):
    """Flatten a NeoWs feed response into one row per asteroid approach."""
    rows = []
    for feed_date, objects in raw.get("near_earth_objects", {}).items():
        for obj in objects:
            # An asteroid can list several approaches; keep the one on this feed date.
            approach = next(
                (a for a in obj.get("close_approach_data", [])
                 if a.get("close_approach_date") == feed_date),
                None,
            )
            if approach is None:
                continue
            diameter = obj["estimated_diameter"]["meters"]
            rows.append({
                "asteroid_id": obj["id"],
                "name": obj["name"],
                "approach_date": feed_date,
                "diameter_min_m": diameter["estimated_diameter_min"],
                "diameter_max_m": diameter["estimated_diameter_max"],
                # The API sends these numbers as strings, so convert them.
                "velocity_kps": float(approach["relative_velocity"]["kilometers_per_second"]),
                "miss_distance_km": float(approach["miss_distance"]["kilometers"]),
                "miss_distance_lunar": float(approach["miss_distance"]["lunar"]),
                "is_hazardous": bool(obj["is_potentially_hazardous_asteroid"]),
            })
    df = pd.DataFrame(rows, columns=NEO_COLUMNS)
    return df.drop_duplicates(subset=["asteroid_id", "approach_date"]).reset_index(drop=True)


# ---------- DONKI (solar flares) ----------

def parse_flare_class(class_type):
    """Split a flare class like 'C8.6' into ('C', 8.6). Missing or odd values give None."""
    if not class_type:
        return None, None
    letter = class_type[0].upper()
    try:
        magnitude = float(class_type[1:])
    except ValueError:
        magnitude = None
    return letter, magnitude


def transform_flares(raw):
    """Turn a list of DONKI flare events into one tidy row per flare."""
    if not isinstance(raw, list):  # an error body or None is treated as "no data"
        raw = []
    rows = []
    for flare in raw:
        letter, magnitude = parse_flare_class(flare.get("classType"))
        begin = _to_utc(flare.get("beginTime"))
        peak = _to_utc(flare.get("peakTime"))
        end = _to_utc(flare.get("endTime"))
        duration = (end - begin).total_seconds() / 60 if begin is not None and end is not None else None
        rows.append({
            "flare_id": flare.get("flrID"),
            "begin_time": begin.isoformat() if begin is not None else None,
            "peak_time": peak.isoformat() if peak is not None else None,
            "end_time": end.isoformat() if end is not None else None,
            "duration_min": duration,
            "class_type": flare.get("classType"),
            "class_letter": letter,
            "class_magnitude": magnitude,
            "source_location": flare.get("sourceLocation"),
            "active_region": flare.get("activeRegionNum"),
        })
    df = pd.DataFrame(rows, columns=FLARE_COLUMNS)
    return df.drop_duplicates(subset=["flare_id"]).reset_index(drop=True)


# ---------- APOD (picture of the day) ----------

def transform_apod(raw):
    """Turn one APOD record into a one-row table with HTML removed from text fields."""
    if not raw:
        return pd.DataFrame(columns=APOD_COLUMNS)
    credit_html = raw.get("copyright") or raw.get("credit")
    explanation = clean_html(raw.get("explanation"))
    if explanation:
        explanation = re.sub(r"^Explanation:\s*", "", explanation)
    row = {
        "apod_date": raw.get("date"),
        "title": clean_html(raw.get("title")),
        "media_type": raw.get("media_type"),
        "explanation": explanation,
        "credit": clean_html(credit_html),
        "credit_url": first_link(credit_html),
        "image_url": raw.get("hdurl"),
        "page_url": raw.get("url"),
    }
    return pd.DataFrame([row], columns=APOD_COLUMNS)
