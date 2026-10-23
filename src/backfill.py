"""One-time history loader: walks back N days in API-sized windows and loads through the normal transform and load code."""
import argparse
import logging
import time
from datetime import date, timedelta

import requests

from src import extract
from src.load import connect, load_all
from src.transform import transform_apod, transform_flares, transform_neo

NEO_WINDOW_DAYS = 7      # NeoWs allows at most a 7-day window per request
DONKI_WINDOW_DAYS = 30   # DONKI accepts longer ranges; 30 days keeps each request small
MAX_DAYS = 365
PAUSE_SECONDS = 1.0      # be polite to NASA's servers between requests

log = logging.getLogger(__name__)


def windows(start, end, size):
    """Split the dates from start to end (inclusive) into consecutive windows of at most `size` days."""
    result = []
    current = start
    while current <= end:
        stop = min(current + timedelta(days=size - 1), end)
        result.append((current, stop))
        current = stop + timedelta(days=1)
    return result


def backfill(days, today=None, pause=PAUSE_SECONDS, conn=None):
    """Load the last `days` days of asteroids and flares, plus today's picture. Safe to rerun (upserts)."""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    jobs = [("asteroids", s, e) for s, e in windows(start, today, NEO_WINDOW_DAYS)]
    jobs += [("flares", s, e) for s, e in windows(start, today, DONKI_WINDOW_DAYS)]

    owns_connection = conn is None
    conn = conn or connect()
    totals = {"asteroid_approaches": 0, "solar_flares": 0, "apod": 0}
    failures = []

    def add(counts):
        for key in totals:
            totals[key] += counts[key]

    try:
        for i, (kind, s, e) in enumerate(jobs):
            if i and pause:
                time.sleep(pause)
            try:
                if kind == "asteroids":
                    add(load_all(conn, neo=transform_neo(extract.fetch_neo_feed(s, e))))
                else:
                    add(load_all(conn, flares=transform_flares(extract.fetch_donki_flares(s, e))))
                log.info("Loaded %s for %s to %s", kind, s, e)
            except (requests.exceptions.RequestException, ValueError) as exc:
                failures.append(f"{kind} {s} to {e}: {exc}")
                log.error("FAILED %s for %s to %s (%s)", kind, s, e, exc)
        try:
            add(load_all(conn, apod=transform_apod(extract.fetch_apod())))
        except (requests.exceptions.RequestException, ValueError) as exc:
            failures.append(f"picture of the day: {exc}")
            log.error("FAILED picture of the day (%s)", exc)
    finally:
        if owns_connection:
            conn.close()
    return totals, failures, len(jobs) + 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Load past NASA data into the database.")
    parser.add_argument("--days", type=int, default=90, help=f"how many days back to load (1 to {MAX_DAYS})")
    args = parser.parse_args(argv)
    if not 1 <= args.days <= MAX_DAYS:
        parser.error(f"--days must be between 1 and {MAX_DAYS}")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    totals, failures, attempts = backfill(args.days)
    log.info("Backfill finished. Rows written: %s", totals)
    if failures:
        log.warning("%d of %d requests failed; rerun to fill the gaps (it's safe to repeat).", len(failures), attempts)
    return 1 if len(failures) == attempts else 0


if __name__ == "__main__":
    raise SystemExit(main())
