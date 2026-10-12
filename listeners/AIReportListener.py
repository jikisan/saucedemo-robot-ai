"""Robot Framework listener that triages every failed test with the AI Test Assistant.

Enable with ``--listener listeners/AIReportListener.py`` (already in ``robot.args``).

For each failed test (including ``known-bug`` failures turned into SKIP by
``--skiponfailure``) it captures the URL, any visible app error banner, the page source and
a screenshot, runs ``failure_analyzer.analyze`` and:

- appends the triage to the test's message, so it shows in log.html and report.html,
- writes a run summary to ``ai_triage.md`` (and ``ai_triage.json``) in the output directory
  when the run ends.

The listener never changes a test's status, and its own errors are logged as warnings.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from libraries.ai_assist.failure_analyzer import FailureContext, Triage, analyze, render_markdown
from libraries.ai_assist.providers import get_provider

logger = logging.getLogger(__name__)

SKIPPED_FAILURE_MARKER = "Original failure:"
ERROR_BANNER = 'css:[data-test="error"]'
REPORT_NAME = "ai_triage.md"
REPORT_DATA_NAME = "ai_triage.json"  # merged across pabot workers by libraries/ai_assist/reports.py


class AIReportListener:
    """Listener API v3: triage on ``end_test``, summary report on ``close``."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self) -> None:
        self.triages: list[Triage] = []
        self.output_dir: Path | None = None

    def start_suite(self, data: Any, result: Any) -> None:
        if self.output_dir is None:
            from robot.libraries.BuiltIn import BuiltIn

            self.output_dir = Path(BuiltIn().get_variable_value("${OUTPUT DIR}"))

    def end_test(self, data: Any, result: Any) -> None:
        failed_known_bug = result.skipped and SKIPPED_FAILURE_MARKER in result.message
        if not (result.failed or failed_known_bug):
            return
        try:
            triage = analyze(self._capture(result), get_provider())
        except Exception as error:  # noqa: BLE001 - triage must never break the run
            logger.warning("AI triage failed for '%s': %s", result.name, error)
            return
        self.triages.append(triage)
        note = f"\n\n[AI triage: {triage.category} via {triage.source}] {triage.summary}"
        if triage.hypothesis:
            note += f"\nHypothesis: {triage.hypothesis}"
        result.message += f"{note}\nSuggested fix: {triage.suggested_fix}"

    def close(self) -> None:
        if self.output_dir is None:
            return
        report = self.output_dir / REPORT_NAME
        report.write_text(render_markdown(self.triages, get_provider().provider.name, self.output_dir), encoding="utf-8")
        data = self.output_dir / REPORT_DATA_NAME
        data.write_text(json.dumps([asdict(t) for t in self.triages], indent=2), encoding="utf-8")

    def _capture(self, result: Any) -> FailureContext:
        """Collect page state; each piece is optional because the browser may be gone."""
        url = error = source = screenshot = ""
        try:
            from robot.libraries.BuiltIn import BuiltIn

            selenium = BuiltIn().get_library_instance("SeleniumLibrary")
            driver = selenium.driver
            url, source = driver.current_url, driver.page_source
            banners = selenium.find_elements(ERROR_BANNER)
            error = banners[0].text.strip() if banners else ""
            if self.output_dir:
                name = re.sub(r"[^A-Za-z0-9]+", "-", f"{result.parent.name}-{result.name}").strip("-")
                path = self.output_dir / f"triage-{name}.png"
                driver.save_screenshot(str(path))
                screenshot = str(path)
        except Exception as error_:  # noqa: BLE001 - no browser is a valid state
            logger.info("Triage capture incomplete: %s", error_)
        return FailureContext(
            test=result.name, suite=result.parent.name, message=result.message,
            tags=tuple(str(tag) for tag in result.tags), url=url, visible_error=error,
            page_source=source, screenshot=screenshot,
        )
