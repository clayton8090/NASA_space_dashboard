"""Run the whole pipeline: extract -> transform -> load."""
import logging

from src.extract import fetch_all
from src.load import connect, load_all
from src.transform import transform_apod, transform_flares, transform_neo

TOTAL_SOURCES = 3
log = logging.getLogger(__name__)


def run():
    results, failures = fetch_all()

    # A source that failed to download is skipped; the others still load.
    neo = transform_neo(results["neo"]) if "neo" in results else None
    flares = transform_flares(results["donki_flares"]) if "donki_flares" in results else None
    apod = transform_apod(results["apod"]) if "apod" in results else None

    conn = connect()
    try:
        counts = load_all(conn, neo=neo, flares=flares, apod=apod)
    finally:
        conn.close()

    log.info("Rows written: %s", counts)
    if failures:
        log.warning("Failed sources: %s", ", ".join(failures))
    return counts, failures


def main():
    """Exit code 1 only if every source failed, so a scheduled job shows red when nothing was updated."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _, failures = run()
    return 1 if len(failures) >= TOTAL_SOURCES else 0


if __name__ == "__main__":
    raise SystemExit(main())
