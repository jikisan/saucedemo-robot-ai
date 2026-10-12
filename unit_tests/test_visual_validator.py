from libraries.ai_assist.visual_validator import (
    Box,
    alignment_defects,
    image_defects,
    parse_vision_verdict,
)


def grid(**overrides: object) -> list[Box]:
    """Six 159x238 images in two columns (x=184, x=739), like the SauceDemo inventory."""
    boxes = [Box(index=i, left=184 if i % 2 == 0 else 739, top=155 + 252 * (i // 2),
                 width=159, height=238, src=f"/img/item-{i}.jpg") for i in range(6)]
    if overrides:
        boxes[0] = Box(**{**boxes[0].__dict__, **overrides})
    return boxes


def test_clean_grid_has_no_defects() -> None:
    assert image_defects(grid()) == []
    assert alignment_defects(grid()) == []


def test_detects_broken_placeholder_and_resized_image() -> None:
    defects = image_defects(grid(loaded=False, src="/assets/sl-404-Cq1a9k9X.jpg", width=262))
    assert any("failed to load" in d for d in defects)
    assert any("placeholder" in d for d in defects)
    assert any("262x238" in d for d in defects)


def test_detects_duplicate_images() -> None:
    boxes = [Box(**{**b.__dict__, "src": "/img/dog.jpg"}) for b in grid()]
    assert image_defects(boxes) == ["6 elements share image dog.jpg"]


def test_detects_element_outside_grid_column() -> None:
    defects = alignment_defects(grid(left=240))
    assert defects == ["#1 item-0.jpg: left edge at x=240 matches no column"]


def test_small_jitter_is_tolerated() -> None:
    assert alignment_defects(grid(left=186)) == []


def test_parse_vision_verdict() -> None:
    assert parse_vision_verdict('{"looks_correct": false, "issues": ["cart icon moved"]}') == (False, ["cart icon moved"])
    assert parse_vision_verdict("I think it is fine") is None
