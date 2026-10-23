"""Phase 4: smoke tests that run the real dashboard script with Streamlit's test harness."""
from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def run_app(db_path, monkeypatch):
    monkeypatch.setenv("SPACE_DB_PATH", str(db_path))
    return AppTest.from_file(APP, default_timeout=30).run()


def metric_values(at):
    return {m.label: m.value for m in at.metric}


def page_text(at):
    return " ".join(md.value for md in at.markdown)


def test_title_and_key_numbers(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    assert not at.exception
    assert at.title[0].value == "Clayton's Astronomical Dashboard"
    assert metric_values(at) == {
        "Asteroid approaches": "3",
        "Potentially hazardous": "2",
        "Closest pass (Moon distances)": "0.8",
        "Solar flares": "3",
    }


def test_picture_of_the_day_comes_first_with_full_description(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    assert at.subheader[0].value == "Test Galaxy"  # first heading under the title is the picture
    assert "A test galaxy." in page_text(at)       # description shown directly, not hidden


def test_guide_is_always_visible_and_nothing_is_collapsible(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    assert "How to read this dashboard" in page_text(at)
    assert len(at.expander) == 0


def test_two_tabs_and_no_flare_class_filter(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    assert [t.label for t in at.tabs] == ["Asteroids", "Solar flares"]
    assert [s.label for s in at.sidebar.select_slider] == ["Closer than", "Minimum size"]


def test_every_key_number_and_filter_has_a_tooltip(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    assert all(m.help for m in at.metric)
    assert at.sidebar.radio[0].help
    assert at.sidebar.toggle[0].help
    assert all(s.help for s in at.sidebar.select_slider)


def test_summaries_are_shown(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    text = page_text(at)
    assert "3 asteroid close approaches" in text
    assert "The strongest was M1.0 (moderate)" in text


def test_hazardous_toggle(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    at.sidebar.toggle[0].set_value(True).run()
    assert not at.exception
    assert metric_values(at)["Asteroid approaches"] == "2"


def test_closer_than_filter(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    at.sidebar.select_slider[0].set_value("1 Moon distance").run()
    assert not at.exception
    assert metric_values(at)["Asteroid approaches"] == "1"
    assert metric_values(at)["Solar flares"] == "3"  # asteroid filters never touch flares


def test_minimum_size_filter(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    at.sidebar.select_slider[1].set_value("140 m (hazard-size)").run()
    assert not at.exception
    assert metric_values(at)["Asteroid approaches"] == "1"


def test_custom_date_range_applies_to_every_section(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    at.sidebar.radio[0].set_value("Custom").run()
    at.sidebar.date_input[0].set_value((date(2026, 10, 5), date(2026, 10, 5))).run()
    assert not at.exception
    assert metric_values(at)["Asteroid approaches"] == "1"
    assert metric_values(at)["Solar flares"] == "1"


def test_reset_button_restores_default_filters(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    at.sidebar.toggle[0].set_value(True).run()
    at.sidebar.select_slider[0].set_value("1 Moon distance").run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert metric_values(at)["Asteroid approaches"] == "3"


def test_dashboard_tells_you_when_no_database_exists(tmp_path, monkeypatch):
    at = run_app(tmp_path / "missing.db", monkeypatch)
    assert not at.exception
    assert any("No database found" in w.value for w in at.warning)


def test_description_and_status_line(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    text = page_text(at)
    assert "Every day, this dashboard collects fresh data from NASA" in text
    assert "Logged through Oct 5, 2026 · 3 asteroid passes · 3 solar flares" in text


def test_picture_is_framed_as_a_plate_with_credit(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    text = page_text(at)
    assert "Plate · Oct 5, 2026" in text
    assert '<a href="https://example.com/u/test">Test Photographer</a>' in text


def test_closest_pass_ruler_follows_the_filters(seeded_db_path, monkeypatch):
    at = run_app(seeded_db_path, monkeypatch)
    assert "2022 CC · Oct 5 · 0.8 Moon distances" in page_text(at)
    at.sidebar.select_slider[1].set_value("140 m (hazard-size)").run()
    assert "2021 BB · Oct 3 · 13.0 Moon distances" in page_text(at)


def test_outside_credit_text_and_links_are_made_safe(tmp_path, monkeypatch):
    from src.load import connect, load_all
    from src.transform import transform_apod
    db = tmp_path / "evil.db"
    conn = connect(db)
    load_all(conn, apod=transform_apod({
        "date": "2026-10-05", "title": "T", "media_type": "image",
        "copyright": '<a href="javascript:alert(1)">&lt;b&gt;Bad&lt;/b&gt;</a>',
    }))
    conn.execute("INSERT INTO asteroid_approaches (asteroid_id, approach_date, miss_distance_lunar, is_hazardous) "
                 "VALUES ('1', '2026-10-05', 1.0, 0)")
    conn.commit(); conn.close()
    at = run_app(db, monkeypatch)
    assert not at.exception
    text = page_text(at)
    assert "javascript:" not in text
    assert "<b>Bad</b>" not in text and "&lt;b&gt;Bad&lt;/b&gt;" in text
