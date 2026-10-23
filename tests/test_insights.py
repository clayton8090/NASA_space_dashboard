"""Tests for the dashboard's plain-language summaries."""
import pandas as pd

from src.insights import asteroid_summary, display_name, flare_summary, fmt_date, strongest_flare
from src.transform import transform_flares


def asteroids(rows):
    return pd.DataFrame(rows, columns=["name", "approach_date", "miss_distance_lunar", "is_hazardous"])


def test_fmt_date_with_and_without_year():
    assert fmt_date("2026-10-23") == "Oct 23, 2026"
    assert fmt_date("2026-10-03T01:00:00+00:00", with_year=False) == "Oct 3"


def test_display_name_drops_wrapping_parentheses_only():
    assert display_name("(2020 AA)") == "2020 AA"
    assert display_name("433 Eros (A898 PA)") == "433 Eros (A898 PA)"


def test_asteroid_summary_names_the_closest_and_explains_hazard_label():
    df = asteroids([
        ("(2020 AA)", "2026-10-03", 2.6, True),
        ("(2022 CC)", "2026-10-05", 0.8, False),
    ])
    text = asteroid_summary(df, "2026-10-01", "2026-10-07")
    assert text.startswith("2 asteroid close approaches between Oct 1 and Oct 7, 2026.")
    assert "The closest was 2022 CC" in text
    assert "0.8 times the Earth-Moon distance" in text
    assert "1 is labeled potentially hazardous" in text
    assert "not a predicted impact" in text


def test_asteroid_summary_singular_and_no_hazard_sentence():
    df = asteroids([("(2020 AA)", "2026-10-03", 2.6, False)])
    text = asteroid_summary(df, "2026-10-01", "2026-10-07")
    assert text.startswith("1 asteroid close approach between")
    assert "hazardous" not in text


def test_asteroid_summary_when_nothing_matches():
    assert asteroid_summary(asteroids([]), "2026-10-01", "2026-10-07").startswith("No asteroid close approaches")


def flares(*classes):
    return transform_flares([
        {"flrID": str(i), "classType": c, "beginTime": f"2026-10-0{i + 1}T01:00Z"}
        for i, c in enumerate(classes)
    ])


def test_strongest_flare_compares_letter_before_number():
    assert strongest_flare(flares("C9.9", "M1.0", "B5.0"))["class_type"] == "M1.0"
    assert strongest_flare(flares("M1.0", "M2.3"))["class_type"] == "M2.3"


def test_flare_summary_mentions_strength_and_radio_blackouts():
    text = flare_summary(flares("B3.2", "C8.6", "M1.0"))
    assert text.startswith("3 solar flares in this date range.")
    assert "The strongest was M1.0 (moderate)" in text
    assert "1 reached M or X class" in text


def test_flare_summary_without_big_flares():
    text = flare_summary(flares("B3.2"))
    assert text.startswith("1 solar flare in")
    assert "None reached M or X class" in text


def test_flare_summary_when_nothing_matches():
    assert flare_summary(flares()).startswith("No solar flares")


def test_safe_url_allows_web_links_only():
    from src.insights import safe_url
    assert safe_url("https://apod.nasa.gov/x") == "https://apod.nasa.gov/x"
    assert safe_url("http://example.com") == "http://example.com"
    assert safe_url("javascript:alert(1)") is None
    assert safe_url("") is None
    assert safe_url(None) is None
