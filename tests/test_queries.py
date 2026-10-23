"""Phase 4: tests for the dashboard's read-only queries."""
from datetime import date

from src.load import connect
from src.queries import date_bounds, latest_apod, load_asteroids, load_flares


def test_date_bounds_span_asteroids_and_flares(seeded_conn):
    assert date_bounds(seeded_conn) == (date(2026, 10, 3), date(2026, 10, 5))


def test_date_bounds_on_empty_database():
    assert date_bounds(connect(":memory:")) == (None, None)


def test_asteroids_filtered_by_date_range(seeded_conn):
    df = load_asteroids(seeded_conn, date(2026, 10, 3), date(2026, 10, 3))
    assert list(df["asteroid_id"]) == ["1", "2"]


def test_hazardous_only_filter_and_bool_type(seeded_conn):
    df = load_asteroids(seeded_conn, "2026-10-01", "2026-10-31", hazardous_only=True)
    assert list(df["asteroid_id"]) == ["1", "3"]
    assert df["is_hazardous"].dtype == bool


def test_flares_filtered_by_minimum_class(seeded_conn):
    everything = load_flares(seeded_conn, "2026-10-01", "2026-10-31", "A")
    c_and_up = load_flares(seeded_conn, "2026-10-01", "2026-10-31", "C")
    m_and_up = load_flares(seeded_conn, "2026-10-01", "2026-10-31", "M")
    assert len(everything) == 3
    assert list(c_and_up["class_letter"]) == ["C", "M"]
    assert list(m_and_up["class_letter"]) == ["M"]


def test_flares_filtered_by_date_range(seeded_conn):
    df = load_flares(seeded_conn, "2026-10-04", "2026-10-05")
    assert list(df["flare_id"]) == ["F2", "F3"]


def test_latest_apod_returns_dict_with_credit(seeded_conn):
    apod = latest_apod(seeded_conn)
    assert apod["title"] == "Test Galaxy"
    assert apod["credit"] == "Test Photographer"


def test_latest_apod_on_empty_database_is_none():
    assert latest_apod(connect(":memory:")) is None
