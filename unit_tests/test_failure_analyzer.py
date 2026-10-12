from libraries.ai_assist.failure_analyzer import (
    FailureContext,
    analyze,
    classify,
    render_markdown,
    strip_skip_prefix,
    trim_page_source,
)
from libraries.ai_assist.providers import GuardedProvider, NullProvider
from unit_tests.fakes import FakeProvider

NO_AI = GuardedProvider(NullProvider(), max_calls=5)


def ctx(message: str, **kwargs: object) -> FailureContext:
    return FailureContext(test="T", suite="S", message=message, **kwargs)


def test_rules_classify_common_failures() -> None:
    assert classify(ctx("WebDriverException: chrome not reachable")).category == "environment"
    assert classify(ctx("Locator 'x' (css:#a) not found after 10s and could not be healed.")).category == "locator"
    assert classify(ctx("Element 'css:#a' not visible after 10 seconds.")).category == "timeout"
    assert classify(ctx("3 != 6")).category == "assertion"
    assert "race" in classify(ctx("StaleElementReferenceException: Message: stale element")).summary


def test_visible_app_error_means_app_defect() -> None:
    triage = classify(ctx("Element 'css:[data-test=\"finish\"]' not visible after 10 seconds.",
                          visible_error="Error: Last Name is required"))
    assert triage.category == "app-defect"
    assert "Last Name is required" in triage.summary


def test_expected_error_text_is_not_an_app_defect() -> None:
    triage = classify(ctx("'Error: A' != 'Error: B'", visible_error="Error: A"))
    assert triage.category == "assertion"


def test_known_bug_assertion_is_app_defect() -> None:
    triage = classify(ctx("Failed test skipped using 'known-bug' tag.\n\nOriginal failure:\n3 != 6",
                          tags=("known-bug",)))
    assert triage.category == "app-defect"
    assert triage.known_bug and triage.message == "3 != 6"


def test_strip_skip_prefix() -> None:
    assert strip_skip_prefix("Skipped.\n\nOriginal failure:\nboom") == "boom"
    assert strip_skip_prefix("boom") == "boom"


def test_analyze_without_ai_is_heuristic() -> None:
    assert analyze(ctx("3 != 6"), NO_AI).source == "heuristic"


def test_analyze_adds_ai_hypothesis_and_keeps_valid_category() -> None:
    fake = FakeProvider('{"category": "app-defect", "hypothesis": "Add button broken for some items.",'
                        ' "suggested_fix": "File a bug."}')
    triage = analyze(ctx("3 != 6"), GuardedProvider(fake, 5))
    assert (triage.source, triage.category, triage.suggested_fix) == ("ai", "app-defect", "File a bug.")
    assert "3 != 6" in fake.prompts[0]


def test_analyze_ignores_invalid_ai_category_and_ai_errors() -> None:
    fake = FakeProvider('{"category": "cosmic-rays", "hypothesis": "h"}', RuntimeError("down"))
    ai = GuardedProvider(fake, 5)
    assert analyze(ctx("3 != 6"), ai).category == "assertion"
    assert analyze(ctx("3 != 6"), ai).source == "heuristic"


def test_trim_page_source_drops_scripts() -> None:
    assert trim_page_source("<div>a</div><script>var x = 1;</script>\n\n<p>b</p>") == "<div>a</div> <p>b</p>"


def test_render_markdown() -> None:
    assert "No failures" in render_markdown([], "none")
    report = render_markdown([classify(ctx("3 != 6", tags=("known-bug",)))], "none")
    assert "| app-defect | 1 |" in report and "## S / T" in report


def test_known_bug_missing_element_is_app_defect() -> None:
    triage = classify(ctx("Locator 'k' (css:#a) not found after 10s and could not be healed.", tags=("known-bug",)))
    assert triage.category == "app-defect"
