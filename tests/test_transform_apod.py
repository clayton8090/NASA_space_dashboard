"""Tests for the APOD transform."""
from src.transform import APOD_COLUMNS, transform_apod

SAMPLE = {
    "date": "2026-10-05",
    "title": "M104: The Sombrero Galaxy&#8217;s Tidal Streams",
    "media_type": "image",
    "explanation": (
        '<strong>Explanation: </strong>A deep image of '
        '<a href="https://en.wikipedia.org/wiki/Sombrero_Galaxy">M104</a> &amp; more.'
    ),
    "copyright": '<a href="https://app.astrobin.com/u/Fox368">Engelbert Vollmer</a>',
    "credit": '<a href="https://app.astrobin.com/u/Fox368">Engelbert Vollmer</a>',
    "hdurl": "https://example.com/image.jpg",
    "url": "https://science.nasa.gov/image-article/apod-example/",
}


def test_html_is_removed_from_title_and_explanation():
    df = transform_apod(SAMPLE)
    assert list(df.columns) == APOD_COLUMNS
    assert df.loc[0, "explanation"] == "A deep image of M104 & more."
    assert "&#" not in df.loc[0, "title"]


def test_credit_text_and_link_are_kept_separately():
    df = transform_apod(SAMPLE)
    assert df.loc[0, "credit"] == "Engelbert Vollmer"
    assert df.loc[0, "credit_url"] == "https://app.astrobin.com/u/Fox368"


def test_missing_credit_stays_empty_instead_of_being_invented():
    sample = {k: v for k, v in SAMPLE.items() if k not in ("copyright", "credit")}
    df = transform_apod(sample)
    assert df.loc[0, "credit"] is None
    assert df.loc[0, "credit_url"] is None


def test_empty_response_gives_empty_table():
    for bad in (None, {}):
        df = transform_apod(bad)
        assert df.empty
        assert list(df.columns) == APOD_COLUMNS
