"""Phase 3/5: tests for the pipeline runner."""
from src import pipeline
from src.load import connect

NEO_RAW = {
    "near_earth_objects": {
        "2026-10-03": [{
            "id": "1",
            "name": "(2020 AA)",
            "estimated_diameter": {"meters": {"estimated_diameter_min": 1.0, "estimated_diameter_max": 2.0}},
            "is_potentially_hazardous_asteroid": False,
            "close_approach_data": [{
                "close_approach_date": "2026-10-03",
                "relative_velocity": {"kilometers_per_second": "5.0"},
                "miss_distance": {"kilometers": "100.0", "lunar": "1.0"},
            }],
        }]
    }
}


def test_pipeline_loads_available_sources_and_reports_failures(monkeypatch, tmp_path):
    db = tmp_path / "t.db"
    monkeypatch.setenv("SPACE_DB_PATH", str(db))
    monkeypatch.setattr(
        pipeline, "fetch_all",
        lambda: ({"neo": NEO_RAW, "donki_flares": []}, {"apod": "down"}),
    )
    counts, failures = pipeline.run()
    assert counts["asteroid_approaches"] == 1
    assert counts["apod"] == 0
    assert failures == {"apod": "down"}
    assert connect(db).execute("SELECT COUNT(*) FROM asteroid_approaches").fetchone()[0] == 1


def test_exit_code_is_failure_only_when_every_source_failed(monkeypatch):
    monkeypatch.setattr(pipeline, "run", lambda: ({}, {"a": 1, "b": 2, "c": 3}))
    assert pipeline.main() == 1
    monkeypatch.setattr(pipeline, "run", lambda: ({}, {"a": 1}))
    assert pipeline.main() == 0
