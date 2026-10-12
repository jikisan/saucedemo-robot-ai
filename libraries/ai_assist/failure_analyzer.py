"""Failure triage: classify a failed test and explain the likely root cause.

Categories: ``locator | timeout | assertion | app-defect | environment``.

``analyze()`` always produces a heuristic triage from the failure message, the visible app
error and the test's tags. When AI is configured it adds a root-cause hypothesis and a
suggested fix. The AI is advisory: it can refine the category but never changes a test's
status, and any AI failure leaves the heuristic triage as is.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path

from libraries.ai_assist.providers import GuardedProvider

CATEGORIES = ("locator", "timeout", "assertion", "app-defect", "environment")
PAGE_SOURCE_LIMIT = 4000

# Ordered: first match wins.
RULES: tuple[tuple[str, re.Pattern[str], str, str], ...] = (
    ("environment",
     re.compile(r"WebDriverException|session not created|chrome not reachable|ERR_NAME_NOT_RESOLVED|"
                r"ERR_CONNECTION|ERR_INTERNET|Connection refused|No browser is open", re.I),
     "Browser or network problem, not an application failure.",
     "Check browser/driver install, network access to BASE_URL, and re-run."),
    ("locator",
     re.compile(r"could not be healed|did not match any elements|Unknown locator key|no such element", re.I),
     "Element could not be located on the page.",
     "Compare the locator in locators.yaml with the current DOM; check healing_report.json."),
    ("timeout",
     re.compile(r"StaleElementReference", re.I),
     "The page re-rendered while the step was reading it (timing race).",
     "Re-locate the element after the action, or wait for the re-render to finish before reading."),
    ("timeout",
     re.compile(r"not visible after|timed out|timeout|did not (appear|disappear)|still visible after", re.I),
     "Expected element or page state did not appear in time.",
     "Check whether the previous step really succeeded (screenshot), or if the app is slow."),
    ("assertion",
     re.compile(r"!=|should (be|contain|have)|does not contain|are different|not equal|expected", re.I),
     "The app responded, but with a different value than the test expects.",
     "Compare expected vs actual in the message; decide whether the app or the test is wrong."),
)


@dataclass(frozen=True)
class FailureContext:
    """What the listener captured when a test failed."""

    test: str
    suite: str
    message: str
    tags: tuple[str, ...] = ()
    url: str = ""
    visible_error: str = ""
    page_source: str = ""
    screenshot: str = ""


@dataclass(frozen=True)
class Triage:
    """Result of analysing one failure."""

    test: str
    suite: str
    category: str
    summary: str
    suggested_fix: str
    message: str
    source: str = "heuristic"  # "heuristic" | "ai"
    hypothesis: str = ""
    known_bug: bool = False
    url: str = ""
    screenshot: str = ""


def strip_skip_prefix(message: str) -> str:
    """Remove Robot's ``--skiponfailure`` preamble so only the original failure is analysed."""
    marker = "Original failure:"
    return message.split(marker, 1)[1].strip() if marker in message else message.strip()


def classify(context: FailureContext) -> Triage:
    """Rule-based triage. Deterministic, no network."""
    message = strip_skip_prefix(context.message)
    category, summary, fix = "assertion", "Test failed for an unrecognised reason.", "Read the log and screenshot."
    for rule_category, pattern, rule_summary, rule_fix in RULES:
        if pattern.search(message):
            category, summary, fix = rule_category, rule_summary, rule_fix
            break
    known_bug = "known-bug" in context.tags
    if category != "environment" and context.visible_error and context.visible_error not in message:
        category = "app-defect"
        summary = f'App showed an unexpected error: "{context.visible_error}". The test step after it then failed.'
        fix = "Reproduce manually with the same user and data; file it as an application bug."
    elif known_bug and category in ("locator", "timeout", "assertion"):
        category = "app-defect"
        summary = f"Known application defect reproduced. {summary}"
        fix = "No test change needed; track the defect. The test asserts correct behaviour."
    return Triage(
        test=context.test, suite=context.suite, category=category, summary=summary,
        suggested_fix=fix, message=message, known_bug=known_bug, url=context.url,
        screenshot=context.screenshot,
    )


def trim_page_source(html: str, limit: int = PAGE_SOURCE_LIMIT) -> str:
    """Drop scripts, styles and SVG noise; collapse whitespace; cap length."""
    html = re.sub(r"<(script|style|svg)\b.*?</\1>", "", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html)[:limit]


def build_prompt(context: FailureContext, triage: Triage) -> str:
    return (
        "You are a senior SDET triaging an automated UI test failure for https://www.saucedemo.com.\n"
        f"Test: {context.suite} / {context.test}\nTags: {', '.join(context.tags) or 'none'}\n"
        f"Failure message: {triage.message}\nURL at failure: {context.url}\n"
        f"Error banner visible in app: {context.visible_error or 'none'}\n"
        f"Heuristic category: {triage.category}\n"
        f"Trimmed page HTML: {trim_page_source(context.page_source)}\n\n"
        "The screenshot (if attached) shows the page at the moment of failure.\n"
        f"Choose a category from {list(CATEGORIES)}. Reply with JSON only: "
        '{"category": "...", "hypothesis": "<likely root cause, 1-2 sentences>", '
        '"suggested_fix": "<concrete next step>"}'
    )


def parse_ai_triage(answer: str) -> dict[str, str] | None:
    match = re.search(r"\{.*\}", answer, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(data, dict) or not data.get("hypothesis"):
        return None
    return {k: str(v) for k, v in data.items()}


def analyze(context: FailureContext, ai: GuardedProvider) -> Triage:
    """Heuristic triage, enriched by AI when available."""
    triage = classify(context)
    if not ai.available:
        return triage
    prompt = build_prompt(context, triage)
    if context.screenshot:
        answer = ai.complete_with_image(prompt, context.screenshot)
    else:
        answer = ai.complete(prompt)
    parsed = parse_ai_triage(answer or "")
    if not parsed:
        return triage
    category = parsed.get("category", triage.category)
    return replace(
        triage,
        source="ai",
        category=category if category in CATEGORIES else triage.category,
        hypothesis=parsed["hypothesis"],
        suggested_fix=parsed.get("suggested_fix") or triage.suggested_fix,
    )


def render_markdown(triages: list[Triage], ai_provider: str, base_dir: Path | None = None) -> str:
    """Run summary for ``ai_triage.md``; screenshot links are relative to ``base_dir``."""

    def link(path: str) -> str:
        return Path(os.path.relpath(path, base_dir)).as_posix() if base_dir else Path(path).name

    lines = ["# AI Test Assistant: failure triage", ""]
    if not triages:
        return "\n".join(lines + ["No failures in this run.", ""])
    counts = {c: sum(t.category == c for t in triages) for c in CATEGORIES}
    known = sum(t.known_bug for t in triages)
    lines += [
        f"**{len(triages)} failure(s)**, {known} of them tagged `known-bug`. AI provider: `{ai_provider}`.",
        "",
        "| Category | Count |", "|---|---|",
        *[f"| {c} | {n} |" for c, n in counts.items() if n],
        "",
        "| Test | Category | Known bug | Source |", "|---|---|---|---|",
        *[f"| {t.suite} / {t.test} | {t.category} | {'yes' if t.known_bug else 'no'} | {t.source} |"
          for t in triages],
        "",
    ]
    for t in triages:
        lines += [
            f"## {t.suite} / {t.test}",
            "",
            f"- **Category:** {t.category} ({t.source})",
            f"- **Summary:** {t.summary}",
            *([f"- **AI hypothesis:** {t.hypothesis}"] if t.hypothesis else []),
            f"- **Suggested fix:** {t.suggested_fix}",
            *([f"- **URL:** {t.url}"] if t.url else []),
            *([f"- **Screenshot:** [{Path(t.screenshot).name}]({link(t.screenshot)})"] if t.screenshot else []),
            "",
            "```",
            t.message,
            "```",
            "",
        ]
    return "\n".join(lines)
