"""Shared test data: a small, fake but realistic database."""
import pandas as pd
import pytest

from src.load import connect, load_all
from src.transform import NEO_COLUMNS, transform_apod, transform_flares


def seed(conn):
    neo = pd.DataFrame(
        [
            ("1", "(2020 AA)", "2026-10-03", 10.0, 20.0, 12.5, 1_000_000.0, 2.6, True),
            ("2", "(2021 BB)", "2026-10-03", 100.0, 200.0, 7.0, 5_000_000.0, 13.0, False),
            ("3", "(2022 CC)", "2026-10-05", 50.0, 90.0, 20.1, 300_000.0, 0.8, True),
        ],
        columns=NEO_COLUMNS,
    )
    flares = transform_flares([
        {"flrID": "F1", "classType": "B3.2", "beginTime": "2026-10-03T01:00Z",
         "peakTime": "2026-10-03T01:10Z", "endTime": "2026-10-03T01:20Z"},
        {"flrID": "F2", "classType": "C8.6", "beginTime": "2026-10-04T02:30Z",
         "peakTime": "2026-10-04T02:46Z", "endTime": "2026-10-04T03:05Z"},
        {"flrID": "F3", "classType": "M1.0", "beginTime": "2026-10-05T18:36Z",
         "peakTime": "2026-10-05T18:50Z", "endTime": "2026-10-05T18:57Z"},
    ])
    apod = transform_apod({
        "date": "2026-10-05",
        "title": "Test Galaxy",
        "media_type": "image",
        "explanation": "<strong>Explanation: </strong>A test galaxy.",
        "copyright": '<a href="https://example.com/u/test">Test Photographer</a>',
        "hdurl": "https://example.com/galaxy.jpg",
        "url": "https://example.com/page",
    })
    load_all(conn, neo=neo, flares=flares, apod=apod)


@pytest.fixture
def seeded_conn():
    conn = connect(":memory:")
    seed(conn)
    return conn


@pytest.fixture
def seeded_db_path(tmp_path):
    path = tmp_path / "seeded.db"
    conn = connect(path)
    seed(conn)
    conn.close()
    return path
