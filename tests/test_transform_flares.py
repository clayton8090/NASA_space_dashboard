"""Tests for the DONKI flare transform."""
import pandas as pd

from src.transform import FLARE_COLUMNS, parse_flare_class, transform_flares

SAMPLE = [
    {
        "flrID": "A",
        "classType": "C8.6",
        "beginTime": "2026-09-30T02:30Z",
        "peakTime": "2026-09-30T02:46Z",
        "endTime": "2026-09-30T03:05Z",
        "sourceLocation": "N11W48",
        "activeRegionNum": 4321,
    },
    {
        "flrID": "B",
        "classType": "M1.2",
        "beginTime": "2026-10-01T10:00Z",
        "peakTime": "2026-10-01T10:10Z",
        "endTime": None,
        "sourceLocation": "",
        "activeRegionNum": None,
    },
]


def test_parse_flare_class_splits_letter_and_number():
    assert parse_flare_class("C8.6") == ("C", 8.6)
    assert parse_flare_class("x1.0") == ("X", 1.0)


def test_parse_flare_class_handles_missing_or_odd_values():
    assert parse_flare_class(None) == (None, None)
    assert parse_flare_class("") == (None, None)
    assert parse_flare_class("Xabc") == ("X", None)


def test_flare_columns_and_duration():
    df = transform_flares(SAMPLE)
    assert list(df.columns) == FLARE_COLUMNS
    assert df.loc[0, "class_letter"] == "C"
    assert df.loc[0, "class_magnitude"] == 8.6
    assert df.loc[0, "duration_min"] == 35.0
    assert df.loc[0, "begin_time"].startswith("2026-09-30T02:30")


def test_missing_end_time_gives_no_duration_and_no_crash():
    df = transform_flares(SAMPLE)
    assert pd.isna(df.loc[1, "duration_min"])
    assert pd.isna(df.loc[1, "end_time"])


def test_duplicate_flares_are_removed():
    df = transform_flares(SAMPLE + [SAMPLE[0]])
    assert len(df) == 2


def test_empty_or_bad_response_gives_empty_table():
    for bad in (None, [], {"error": "something went wrong"}):
        df = transform_flares(bad)
        assert df.empty
        assert list(df.columns) == FLARE_COLUMNS
