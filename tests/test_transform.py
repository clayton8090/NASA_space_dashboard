"""Phase 2: tests for the transform functions."""
from src.transform import NEO_COLUMNS, transform_neo

SAMPLE = {
    "near_earth_objects": {
        "2026-10-03": [
            {
                "id": "1",
                "name": "(2020 AA)",
                "estimated_diameter": {
                    "meters": {"estimated_diameter_min": 10.0, "estimated_diameter_max": 20.0}
                },
                "is_potentially_hazardous_asteroid": True,
                "close_approach_data": [
                    {
                        "close_approach_date": "2026-10-03",
                        "relative_velocity": {"kilometers_per_second": "12.5"},
                        "miss_distance": {"kilometers": "1000000.5", "lunar": "2.6"},
                    },
                    {
                        "close_approach_date": "2030-01-01",
                        "relative_velocity": {"kilometers_per_second": "99.9"},
                        "miss_distance": {"kilometers": "5.0", "lunar": "0.1"},
                    },
                ],
            }
        ],
        "2026-10-04": [
            {
                "id": "2",
                "name": "(2021 BB)",
                "estimated_diameter": {
                    "meters": {"estimated_diameter_min": 1.0, "estimated_diameter_max": 2.0}
                },
                "is_potentially_hazardous_asteroid": False,
                "close_approach_data": [
                    {
                        "close_approach_date": "2031-05-05",
                        "relative_velocity": {"kilometers_per_second": "7.0"},
                        "miss_distance": {"kilometers": "9.0", "lunar": "0.2"},
                    }
                ],
            }
        ],
    }
}


def test_keeps_only_the_approach_matching_the_feed_date():
    df = transform_neo(SAMPLE)
    assert len(df) == 1  # asteroid 2 has no approach on its feed date
    assert df.loc[0, "velocity_kps"] == 12.5


def test_text_numbers_become_floats_and_flag_is_bool():
    df = transform_neo(SAMPLE)
    assert df["miss_distance_km"].dtype == "float64"
    assert bool(df.loc[0, "is_hazardous"]) is True


def test_empty_response_gives_empty_table_with_columns():
    df = transform_neo({})
    assert df.empty
    assert list(df.columns) == NEO_COLUMNS
