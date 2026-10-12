"""Merge per-process AI reports into one run report.

``pabot`` gives each worker its own output directory, so each writes its own
``ai_triage.json`` / ``healing_report.json``. After the run:

    python -m libraries.ai_assist.reports results

writes the combined ``results/ai_triage.md`` and ``results/healing_report.json``.
With plain ``robot`` the reports are already complete and this is a no-op.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from libraries.ai_assist.failure_analyzer import Triage, render_markdown
from libraries.utils.config import load_config

TRIAGE_JSON = "ai_triage.json"
TRIAGE_MD = "ai_triage.md"
HEALING_JSON = "healing_report.json"


def _collect(results_dir: Path, name: str) -> list[dict] | None:
    """Entries from ``name`` files in worker subdirectories; ``None`` if there are none."""
    files = sorted(p for p in results_dir.rglob(name) if p.parent != results_dir)
    if not files:
        return None
    return [entry for path in files for entry in json.loads(path.read_text(encoding="utf-8"))]


def merge(results_dir: Path) -> None:
    triages = _collect(results_dir, TRIAGE_JSON)
    if triages is not None:
        (results_dir / TRIAGE_JSON).write_text(json.dumps(triages, indent=2), encoding="utf-8")
        report = render_markdown([Triage(**t) for t in triages], load_config().ai_provider, results_dir)
        (results_dir / TRIAGE_MD).write_text(report, encoding="utf-8")
    healings = _collect(results_dir, HEALING_JSON)
    if healings is not None:
        (results_dir / HEALING_JSON).write_text(json.dumps(healings, indent=2), encoding="utf-8")


if __name__ == "__main__":
    merge(Path(sys.argv[1] if len(sys.argv) > 1 else "results"))
