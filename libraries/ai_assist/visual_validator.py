"""Visual checks for Robot Framework + SeleniumLibrary.

Two kinds of keyword:

- **Deterministic** (``Images Should Be Valid``, ``Elements Should Be Aligned``): measure the
  DOM (image load state, ``src``, bounding boxes) and FAIL the test on a defect. These give
  the same answer with or without AI.
- **Advisory** (``Screen Should Match Description``): sends a screenshot to the vision model
  and logs its verdict as WARN/INFO. It never fails a test, and is skipped without AI.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from libraries.ai_assist.providers import get_provider

POSITION_TOLERANCE_PX = 3
PLACEHOLDER_PATTERN = re.compile(r"(^|[^a-z])(404|placeholder|missing|not[-_]?found)([^a-z]|$)", re.IGNORECASE)

MEASURE_JS = r"""
return arguments[0].map((el, index) => {
  const r = el.getBoundingClientRect();
  return {
    index,
    left: Math.round(r.left), top: Math.round(r.top),
    width: Math.round(r.width), height: Math.round(r.height),
    src: el.currentSrc || el.getAttribute('src') || '',
    loaded: el.tagName !== 'IMG' || (el.complete && el.naturalWidth > 0),
    label: (el.getAttribute('alt') || el.innerText || '').trim().slice(0, 60),
  };
});
"""


@dataclass(frozen=True)
class Box:
    """Measured element: position, size and (for images) source and load state."""

    index: int
    left: int
    top: int
    width: int
    height: int
    src: str = ""
    loaded: bool = True
    label: str = ""

    @property
    def name(self) -> str:
        return f"#{self.index + 1} {self.label or Path(self.src).name}".strip()


# --- pure checks (unit tested) ---------------------------------------------

def _near(a: int, b: int) -> bool:
    return abs(a - b) <= POSITION_TOLERANCE_PX


def _mode(values: list[int]) -> int:
    return Counter(values).most_common(1)[0][0]


def broken_images(boxes: list[Box]) -> list[str]:
    return [f"{b.name}: image failed to load" for b in boxes if not b.loaded]


def placeholder_images(boxes: list[Box]) -> list[str]:
    return [f"{b.name}: placeholder image {Path(b.src).name}" for b in boxes
            if PLACEHOLDER_PATTERN.search(Path(b.src).name)]


def duplicate_images(boxes: list[Box]) -> list[str]:
    counts = Counter(b.src for b in boxes if b.src)
    return [f"{count} elements share image {Path(src).name}" for src, count in counts.items() if count > 1]


def size_outliers(boxes: list[Box]) -> list[str]:
    """Elements whose width or height differs from the most common size."""
    if len(boxes) < 3:
        return []
    width, height = _mode([b.width for b in boxes]), _mode([b.height for b in boxes])
    return [f"{b.name}: size {b.width}x{b.height}, expected {width}x{height}" for b in boxes
            if not (_near(b.width, width) and _near(b.height, height))]


def column_outliers(boxes: list[Box]) -> list[str]:
    """Elements whose left edge lines up with no other element (broken grid column)."""
    if len(boxes) < 4:
        return []
    return [f"{b.name}: left edge at x={b.left} matches no column" for b in boxes
            if not any(_near(b.left, other.left) for other in boxes if other is not b)]


def image_defects(boxes: list[Box]) -> list[str]:
    return broken_images(boxes) + placeholder_images(boxes) + duplicate_images(boxes) + size_outliers(boxes)


def alignment_defects(boxes: list[Box]) -> list[str]:
    return column_outliers(boxes) + size_outliers(boxes)


def build_vision_prompt(expectation: str) -> str:
    return (
        "You are reviewing a screenshot from an automated UI test of an e-commerce web app.\n"
        f"Expected: {expectation}\n"
        "Look for visual defects: wrong or broken images, misaligned or overlapping elements, "
        "wrong prices or text, elements out of place. Reply with JSON only: "
        '{"looks_correct": <true|false>, "issues": ["<short issue>", ...]}'
    )


def parse_vision_verdict(answer: str) -> tuple[bool, list[str]] | None:
    match = re.search(r"\{.*\}", answer, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return bool(data["looks_correct"]), [str(issue) for issue in data.get("issues", [])]
    except (ValueError, KeyError, TypeError):
        return None


# --- Robot Framework library -----------------------------------------------

class VisualValidator:
    """Robot Framework keyword library for visual checks.

    Import with ``Library    libraries.ai_assist.visual_validator.VisualValidator``.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def images_should_be_valid(self, locator: str) -> None:
        """Fails if any matched image is broken, a placeholder, duplicated, or oddly sized.

        Example: ``Images Should Be Valid    css:img.inventory_item_img``
        """
        self._assert_none(image_defects(self._measure(locator)), f"Image defects for {locator}")

    def elements_should_be_aligned(self, locator: str) -> None:
        """Fails if any matched element breaks the grid columns or has an odd size.

        Example: ``Elements Should Be Aligned    css:.pricebar button``
        """
        self._assert_none(alignment_defects(self._measure(locator)), f"Alignment defects for {locator}")

    def screen_should_match_description(self, expectation: str) -> None:
        """Advisory AI vision check. Logs the model's verdict; never fails the test.

        Skipped (INFO) when AI is disabled, over budget, or the call fails.

        Example: ``Screen Should Match Description    Six products in a two-column grid``
        """
        from robot.api import logger
        from robot.libraries.BuiltIn import BuiltIn

        ai = get_provider()
        if not ai.available:
            logger.info("AI visual check skipped: AI disabled or call budget spent.")
            return
        output_dir = Path(BuiltIn().get_variable_value("${OUTPUT DIR}"))
        test = BuiltIn().get_variable_value("${TEST NAME}", "screen")
        screenshot = output_dir / f"visual-{re.sub(r'[^A-Za-z0-9]+', '-', test).strip('-')}.png"
        self._selenium().driver.save_screenshot(str(screenshot))
        verdict = parse_vision_verdict(ai.complete_with_image(build_vision_prompt(expectation), screenshot) or "")
        if verdict is None:
            logger.info("AI visual check gave no usable answer; skipped.")
        elif verdict[0]:
            logger.info(f"AI visual check: looks correct ({expectation}).")
        else:
            logger.warn(f"AI visual check (advisory) found issues: {'; '.join(verdict[1]) or 'unspecified'}")

    @staticmethod
    def _selenium() -> Any:
        from robot.libraries.BuiltIn import BuiltIn

        return BuiltIn().get_library_instance("SeleniumLibrary")

    def _measure(self, locator: str) -> list[Box]:
        selenium = self._selenium()
        elements = selenium.find_elements(locator)
        if not elements:
            raise AssertionError(f"No elements match {locator}")
        return [Box(**data) for data in selenium.driver.execute_script(MEASURE_JS, elements)]

    @staticmethod
    def _assert_none(defects: list[str], title: str) -> None:
        if defects:
            raise AssertionError(f"{title}:\n- " + "\n- ".join(defects))
