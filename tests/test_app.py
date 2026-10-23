"""Phase 4: smoke tests that run the real dashboard script with Streamlit's test harness."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def metric_values(at):
    return {m.label: m.value for m in at.metric}


def test_dashboard_renders_with_data(seeded_db_path, monkeypatch):
    monkeypatch.setenv("SPACE_DB_PATH", str(seeded_db_path))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    values = metric_values(at)
    assert values["Approaches"] == "3"
    assert values["Flares"] == "3"
    assert values["Strongest"] == "M1.0"


def test_hazardous_toggle_changes_what_is_shown(seeded_db_path, monkeypatch):
    monkeypatch.setenv("SPACE_DB_PATH", str(seeded_db_path))
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.toggle[0].set_value(True).run()
    assert not at.exception
    assert metric_values(at)["Approaches"] == "2"


def test_dashboard_tells_you_when_no_database_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_DB_PATH", str(tmp_path / "missing.db"))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("No database found" in w.value for w in at.warning)
