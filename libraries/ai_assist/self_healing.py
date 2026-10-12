"""Self-healing locators for Robot Framework + SeleniumLibrary.

``Resolve Locator`` turns a locator key from ``locators/locators.yaml`` into a working
SeleniumLibrary locator:

1. Wait (explicitly, up to the Selenium timeout) for the ``primary`` locator.
2. If it never appears, score every visible element on the page against the key's
   human ``description`` (text, id, name, data-test, aria-label, placeholder, tag).
   A clear winner is used directly.
3. If no clear winner and AI is configured, the model picks among the top candidates.
4. A healed locator is cached for the run, logged as WARN, written to
   ``healing_report.json`` in the output directory, and the test gets the ``healed`` tag.

``locators.yaml`` is never rewritten: the report is a suggestion for a human to accept.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from libraries.ai_assist.providers import GuardedProvider, get_provider
from libraries.utils.data_loader import get_locator, get_locator_entry

HEURISTIC_MIN_SCORE = 0.6
HEURISTIC_MIN_MARGIN = 0.15
AI_MIN_CONFIDENCE = 0.5
AI_MAX_CANDIDATES = 15
REPORT_NAME = "healing_report.json"

STOPWORDS = {
    "a", "an", "the", "on", "of", "in", "to", "for", "with", "and", "or", "e.g", "eg",
    "shown", "that", "this", "is", "it", "by", "at", "from", "named", "single",
}
ROLE_TAGS = {
    "button": {"button"}, "link": {"a"}, "input": {"input", "textarea"},
    "image": {"img"}, "thumbnail": {"img"}, "dropdown": {"select"}, "select": {"select"},
    "heading": {"h1", "h2", "h3"},
}
FEATURE_KEYS = ("text", "data_test", "id", "name", "aria_label", "placeholder", "value", "type")

# Collects visible, plausibly-targetable elements with the attributes used for scoring.
COLLECT_CANDIDATES_JS = r"""
const xpathOf = (el) => {
  const parts = [];
  for (; el && el.nodeType === 1; el = el.parentNode) {
    let i = 1;
    for (let s = el.previousElementSibling; s; s = s.previousElementSibling) if (s.tagName === el.tagName) i++;
    parts.unshift(`${el.tagName.toLowerCase()}[${i}]`);
  }
  return '/' + parts.join('/');
};
const ownText = (el) => Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join(' ').trim();
const selector = 'button,input,select,textarea,a,img,h1,h2,h3,label,[role],[data-test],[id]';
return Array.from(document.querySelectorAll(selector))
  .filter(el => el.getClientRects().length > 0)
  .slice(0, 300)
  .map(el => ({
    tag: el.tagName.toLowerCase(),
    text: (ownText(el) || el.innerText || el.value || '').trim().slice(0, 80),
    data_test: el.getAttribute('data-test') || '',
    id: el.id || '',
    name: el.getAttribute('name') || '',
    aria_label: el.getAttribute('aria-label') || '',
    placeholder: el.getAttribute('placeholder') || '',
    value: el.tagName === 'INPUT' && el.type === 'submit' ? el.value : '',
    type: el.getAttribute('type') || '',
    xpath: xpathOf(el),
  }));
"""


@dataclass(frozen=True)
class Healing:
    """One healed locator, as written to the report."""

    key: str
    old: str
    new: str
    source: str  # "heuristic" | "ai"
    confidence: float
    reason: str
    test: str = ""
    url: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


# --- pure logic (unit tested) ----------------------------------------------

def tokenize(text: str) -> list[str]:
    """Lowercase word tokens; splits camelCase, kebab-case and snake_case."""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def description_tokens(description: str) -> list[str]:
    return [t for t in dict.fromkeys(tokenize(description)) if t not in STOPWORDS and len(t) > 1]


def _haystack(candidate: dict[str, str]) -> str:
    """All candidate attributes as tokens, plus each attribute collapsed (``user-name`` -> ``username``)."""
    values = [candidate.get(k, "") for k in FEATURE_KEYS]
    tokens = [t for v in values for t in tokenize(v)]
    collapsed = ["".join(tokenize(v)) for v in values if v]
    return " ".join(tokens + collapsed)


def score_candidate(description: str, candidate: dict[str, str]) -> float:
    """Share of description words found on the candidate, plus a bonus for a matching element role."""
    words = description_tokens(description)
    if not words:
        return 0.0
    haystack = _haystack(candidate)
    hay_words = set(haystack.split())
    matched = sum(1 for w in words if w in hay_words or (len(w) > 3 and w in haystack))
    score = matched / len(words)
    tag = candidate.get("tag", "")
    if any(tag in tags for role, tags in ROLE_TAGS.items() if role in words):
        score += 0.2
    return min(score, 1.0)


def rank_candidates(description: str, candidates: list[dict[str, str]]) -> list[tuple[float, dict[str, str]]]:
    scored = [(score_candidate(description, c), c) for c in candidates]
    return sorted(scored, key=lambda pair: pair[0], reverse=True)


def pick_heuristic(ranked: list[tuple[float, dict[str, str]]]) -> tuple[float, dict[str, str]] | None:
    """The top candidate if it scores high enough and clearly beats the runner-up."""
    if not ranked or ranked[0][0] < HEURISTIC_MIN_SCORE:
        return None
    runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
    return ranked[0] if ranked[0][0] - runner_up >= HEURISTIC_MIN_MARGIN else None


def build_locator(candidate: dict[str, str]) -> str:
    """Most stable SeleniumLibrary locator for a candidate: data-test, id, name, then XPath."""
    if candidate.get("data_test"):
        return f'css:[data-test="{candidate["data_test"]}"]'
    if candidate.get("id"):
        return f'id:{candidate["id"]}'
    if candidate.get("name"):
        return f'css:{candidate["tag"]}[name="{candidate["name"]}"]'
    return f'xpath:{candidate["xpath"]}'


def build_ai_prompt(key: str, description: str, candidates: list[dict[str, str]]) -> str:
    listing = [
        {"index": i, **{k: c[k] for k in ("tag", *FEATURE_KEYS) if c.get(k)}}
        for i, c in enumerate(candidates)
    ]
    return (
        "You help a UI test recover from a broken locator.\n"
        f"Locator key: {key}\nThe test wants: {description}\n"
        "Candidate elements currently visible on the page:\n"
        f"{json.dumps(listing, ensure_ascii=False)}\n\n"
        "Pick the single element the test wants, or null if none fits. Reply with JSON only: "
        '{"index": <int or null>, "confidence": <0..1>, "reason": "<one sentence>"}'
    )


def parse_ai_choice(answer: str, candidate_count: int) -> tuple[int, float, str] | None:
    """Parse the model's JSON reply; ``None`` if unusable or not confident enough."""
    match = re.search(r"\{.*\}", answer, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        index, confidence = data.get("index"), float(data.get("confidence", 0))
    except (ValueError, TypeError, AttributeError):
        return None
    if not isinstance(index, int) or not 0 <= index < candidate_count or confidence < AI_MIN_CONFIDENCE:
        return None
    return index, confidence, str(data.get("reason", ""))


def heal(
    key: str,
    old: str,
    description: str,
    candidates: list[dict[str, str]],
    ai: GuardedProvider,
) -> Healing | None:
    """Choose a replacement locator: heuristic first, AI only when the heuristic is unsure."""
    ranked = rank_candidates(description, candidates)
    choice = pick_heuristic(ranked)
    if choice:
        score, candidate = choice
        return Healing(key, old, build_locator(candidate), "heuristic", round(score, 2),
                       f"Best match for '{description}' by element attributes and text.")
    if not ai.available:
        return None
    shortlist = [c for _, c in ranked[:AI_MAX_CANDIDATES]]
    answer = ai.complete(build_ai_prompt(key, description, shortlist))
    parsed = parse_ai_choice(answer or "", len(shortlist))
    if not parsed:
        return None
    index, confidence, reason = parsed
    return Healing(key, old, build_locator(shortlist[index]), "ai", round(confidence, 2), reason)


def describe_closest(description: str, candidates: list[dict[str, str]], limit: int = 3) -> str:
    ranked = rank_candidates(description, candidates)[:limit]
    return "; ".join(f"{build_locator(c)} (score {s:.2f})" for s, c in ranked) or "none"


# --- Robot Framework library -----------------------------------------------

class SelfHealing:
    """Robot Framework keyword library that resolves locator keys with self-healing.

    Import with ``Library    libraries.ai_assist.self_healing.SelfHealing``.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._healings: list[Healing] = []

    def resolve_locator(self, key: str, timeout: str | float | None = None, **params: str) -> str:
        """Return a working locator for ``key``, healing it if the primary locator is missing.

        ``timeout`` defaults to the current Selenium timeout. Templated keys take named
        arguments, e.g. ``product=Sauce Labs Backpack``. Fails only when the element
        cannot be found by any means, listing the closest candidates.

        Example: ``${locator}=    Resolve Locator    login.submit``
        """
        from robot.api import logger
        from robot.utils import timestr_to_secs
        from selenium.webdriver.support.ui import WebDriverWait

        selenium = self._selenium()
        wait_seconds = timestr_to_secs(timeout) if timeout else selenium.timeout
        primary = get_locator(key, **params)
        cache_key = f"{key}|{json.dumps(params, sort_keys=True)}"

        for locator in (self._cache.get(cache_key), primary):
            if locator and self._wait_for(selenium, locator, wait_seconds, WebDriverWait):
                return locator

        description = get_locator_entry(key)["description"].format(**params)
        candidates = selenium.driver.execute_script(COLLECT_CANDIDATES_JS)
        healing = heal(key, primary, description, candidates, get_provider())
        if not healing or not selenium.find_elements(healing.new):
            raise AssertionError(
                f"Locator '{key}' ({primary}) not found after {wait_seconds:.0f}s and could not be healed. "
                f"Closest candidates: {describe_closest(description, candidates)}"
            )
        self._record(healing, selenium.driver.current_url)
        self._cache[cache_key] = healing.new
        logger.warn(
            f"Self-healed '{key}': {healing.old} -> {healing.new} "
            f"({healing.source}, confidence {healing.confidence}). Update locators.yaml."
        )
        return healing.new

    def locator_should_have_been_healed(self, key: str) -> None:
        """Fails unless ``key`` was healed during this run. Used by the self-healing demo test."""
        if not any(h.key == key for h in self._healings):
            raise AssertionError(f"Locator '{key}' was not healed.")

    @staticmethod
    def _selenium() -> Any:
        from robot.libraries.BuiltIn import BuiltIn

        return BuiltIn().get_library_instance("SeleniumLibrary")

    @staticmethod
    def _wait_for(selenium: Any, locator: str, seconds: float, wait_class: Any) -> bool:
        from selenium.common.exceptions import TimeoutException

        try:
            wait_class(selenium.driver, seconds).until(lambda _: selenium.find_elements(locator))
            return True
        except TimeoutException:
            return False

    def _record(self, healing: Healing, url: str) -> None:
        from robot.libraries.BuiltIn import BuiltIn

        builtin = BuiltIn()
        test = builtin.get_variable_value("${TEST NAME}", "")
        healing = Healing(**{**asdict(healing), "test": test, "url": url})
        self._healings.append(healing)
        if test:
            builtin.set_tags("healed")
        # Under pabot each worker writes its own file; libraries/ai_assist/reports.py merges them.
        report = Path(builtin.get_variable_value("${OUTPUT DIR}")) / REPORT_NAME
        report.write_text(json.dumps([asdict(h) for h in self._healings], indent=2), encoding="utf-8")
