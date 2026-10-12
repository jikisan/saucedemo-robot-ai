import json
from pathlib import Path

from libraries.ai_assist.reports import merge


def test_merge_combines_worker_reports(tmp_path: Path) -> None:
    triage = {"test": "T", "suite": "S", "category": "app-defect", "summary": "s",
              "suggested_fix": "f", "message": "m", "known_bug": True}
    for worker in ("0", "1"):
        folder = tmp_path / "pabot_results" / worker
        folder.mkdir(parents=True)
        shot = str(folder / f"triage-{worker}.png")
        (folder / "ai_triage.json").write_text(json.dumps([{**triage, "test": f"T{worker}", "screenshot": shot}]))
    (tmp_path / "pabot_results" / "1" / "healing_report.json").write_text(json.dumps([{"key": "k"}]))

    merge(tmp_path)

    report = (tmp_path / "ai_triage.md").read_text()
    assert "**2 failure(s)**" in report
    assert "(pabot_results/1/triage-1.png)" in report
    assert json.loads((tmp_path / "healing_report.json").read_text()) == [{"key": "k"}]


def test_merge_leaves_single_run_reports_alone(tmp_path: Path) -> None:
    (tmp_path / "ai_triage.md").write_text("original")
    merge(tmp_path)
    assert (tmp_path / "ai_triage.md").read_text() == "original"
