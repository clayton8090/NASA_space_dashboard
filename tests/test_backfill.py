"""Tests for the one-time history loader. No network: the fetch functions are replaced with fakes."""
from datetime import date, timedelta

import pytest
import requests

from src import backfill as bf
from src import extract
from src.load import connect


def test_windows_cover_every_day_once_without_gaps():
    start, end = date(2026, 7, 26), date(2026, 10, 23)  # 90 days
    wins = bf.windows(start, end, 7)
    assert len(wins) == 13
    assert wins[0][0] == start and wins[-1][1] == end
    for (_, prev_end), (next_start, _) in zip(wins, wins[1:]):
        assert next_start == prev_end + timedelta(days=1)
    assert all((e - s).days <= 6 for s, e in wins)


def fake_neo(start, end):
    day = start.isoformat()
    return {"near_earth_objects": {day: [{
        "id": f"neo-{day}",
        "name": f"({day})",
        "estimated_diameter": {"meters": {"estimated_diameter_min": 10.0, "estimated_diameter_max": 20.0}},
        "is_potentially_hazardous_asteroid": False,
        "close_approach_data": [{
            "close_approach_date": day,
            "relative_velocity": {"kilometers_per_second": "5.0"},
            "miss_distance": {"kilometers": "1000.0", "lunar": "3.0"},
        }],
    }]}}


def fake_flares(start, end):
    return [{"flrID": f"flr-{start}", "classType": "C1.0", "beginTime": f"{start}T01:00Z"}]


def test_backfill_loads_90_days_in_api_sized_windows(monkeypatch):
    calls = {"neo": 0, "flares": 0, "apod": 0}

    def neo(s, e):
        calls["neo"] += 1
        return fake_neo(s, e)

    def flr(s, e):
        calls["flares"] += 1
        return fake_flares(s, e)

    def apod():
        calls["apod"] += 1
        return {"date": "2026-10-23", "title": "Test", "media_type": "image"}

    monkeypatch.setattr(extract, "fetch_neo_feed", neo)
    monkeypatch.setattr(extract, "fetch_donki_flares", flr)
    monkeypatch.setattr(extract, "fetch_apod", apod)

    conn = connect(":memory:")
    totals, failures, attempts = bf.backfill(90, today=date(2026, 10, 23), pause=0, conn=conn)
    assert calls == {"neo": 13, "flares": 3, "apod": 1}
    assert attempts == 17 and failures == []
    assert totals == {"asteroid_approaches": 13, "solar_flares": 3, "apod": 1}
    assert conn.execute("SELECT MIN(approach_date) FROM asteroid_approaches").fetchone()[0] == "2026-07-26"


def test_rerunning_backfill_does_not_duplicate(monkeypatch):
    monkeypatch.setattr(extract, "fetch_neo_feed", fake_neo)
    monkeypatch.setattr(extract, "fetch_donki_flares", fake_flares)
    monkeypatch.setattr(extract, "fetch_apod", lambda: {"date": "2026-10-23", "title": "T"})
    conn = connect(":memory:")
    for _ in range(2):
        bf.backfill(30, today=date(2026, 10, 23), pause=0, conn=conn)
    assert conn.execute("SELECT COUNT(*) FROM asteroid_approaches").fetchone()[0] == 5
    assert conn.execute("SELECT COUNT(*) FROM solar_flares").fetchone()[0] == 1


def test_one_failed_window_does_not_stop_the_rest(monkeypatch):
    def flaky_neo(s, e):
        if s == date(2026, 10, 17):
            raise requests.exceptions.ConnectionError("down")
        return fake_neo(s, e)

    monkeypatch.setattr(extract, "fetch_neo_feed", flaky_neo)
    monkeypatch.setattr(extract, "fetch_donki_flares", fake_flares)
    monkeypatch.setattr(extract, "fetch_apod", lambda: {"date": "2026-10-23", "title": "T"})
    conn = connect(":memory:")
    totals, failures, _ = bf.backfill(14, today=date(2026, 10, 23), pause=0, conn=conn)
    assert len(failures) == 1 and "2026-10-17" in failures[0]
    assert totals["asteroid_approaches"] == 1


@pytest.mark.parametrize("days", ["0", "400"])
def test_days_outside_the_allowed_range_are_rejected(days):
    with pytest.raises(SystemExit) as exc:
        bf.main(["--days", days])
    assert exc.value.code == 2
