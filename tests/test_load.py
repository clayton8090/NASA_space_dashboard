"""Phase 3: tests for loading into SQLite."""
import pandas as pd

from src.load import connect, connect_readonly, load_all, read_db_path, write_db_path
from src.transform import NEO_COLUMNS, transform_apod, transform_flares


def neo_frame(velocity=12.5):
    return pd.DataFrame(
        [{
            "asteroid_id": "1",
            "name": "(2020 AA)",
            "approach_date": "2026-10-03",
            "diameter_min_m": 10.0,
            "diameter_max_m": 20.0,
            "velocity_kps": velocity,
            "miss_distance_km": 1000000.5,
            "miss_distance_lunar": 2.6,
            "is_hazardous": True,
        }],
        columns=NEO_COLUMNS,
    )


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_loading_twice_does_not_create_duplicates():
    conn = connect(":memory:")
    load_all(conn, neo=neo_frame())
    load_all(conn, neo=neo_frame())
    assert count(conn, "asteroid_approaches") == 1


def test_rerun_updates_changed_values_instead_of_duplicating():
    conn = connect(":memory:")
    load_all(conn, neo=neo_frame(12.5))
    load_all(conn, neo=neo_frame(13.0))
    assert count(conn, "asteroid_approaches") == 1
    assert conn.execute("SELECT velocity_kps FROM asteroid_approaches").fetchone()[0] == 13.0


def test_missing_values_are_stored_as_null():
    conn = connect(":memory:")
    flares = transform_flares([{
        "flrID": "X",
        "classType": "C1.0",
        "beginTime": "2026-10-01T10:00Z",
        "peakTime": "2026-10-01T10:05Z",
        "endTime": None,
    }])
    load_all(conn, flares=flares)
    assert conn.execute("SELECT duration_min FROM solar_flares").fetchone()[0] is None


def test_apod_row_is_loaded():
    conn = connect(":memory:")
    apod = transform_apod({"date": "2026-10-05", "title": "Test", "media_type": "image"})
    load_all(conn, apod=apod)
    assert count(conn, "apod") == 1


def test_nothing_to_load_is_fine():
    conn = connect(":memory:")
    counts = load_all(conn, neo=None, flares=pd.DataFrame(), apod=None)
    assert counts == {"asteroid_approaches": 0, "solar_flares": 0, "apod": 0}


def test_readonly_connection_cannot_write(seeded_db_path):
    conn = connect_readonly(seeded_db_path)
    try:
        conn.execute("DELETE FROM apod")
        assert False, "write should have been refused"
    except Exception as exc:
        assert "readonly" in str(exc).lower()


def test_readonly_connection_returns_none_for_missing_file(tmp_path):
    assert connect_readonly(tmp_path / "nope.db") is None


def test_db_paths_follow_environment_variable(monkeypatch, tmp_path):
    monkeypatch.setenv("SPACE_DB_PATH", str(tmp_path / "x.db"))
    assert write_db_path() == tmp_path / "x.db"
    assert read_db_path() == tmp_path / "x.db"
