from libraries.ai_assist.providers import GuardedProvider, NullProvider
from libraries.ai_assist.self_healing import (
    build_locator,
    heal,
    parse_ai_choice,
    pick_heuristic,
    rank_candidates,
    score_candidate,
    tokenize,
)
from unit_tests.fakes import FakeProvider

LOGIN_BUTTON = {"tag": "input", "type": "submit", "value": "Login", "data_test": "login-button",
                "id": "login-button", "name": "login-button", "text": "Login", "xpath": "/html[1]/input[3]"}
USERNAME = {"tag": "input", "type": "text", "placeholder": "Username", "data_test": "username",
            "id": "user-name", "name": "user-name", "text": "", "xpath": "/html[1]/input[1]"}
PASSWORD = {"tag": "input", "type": "password", "placeholder": "Password", "data_test": "password",
            "id": "password", "name": "password", "text": "", "xpath": "/html[1]/input[2]"}
PAGE = [USERNAME, PASSWORD, LOGIN_BUTTON]
ADD_BUTTONS = [{"tag": "button", "text": "Add to cart", "xpath": f"/html[1]/button[{i}]"} for i in (1, 2)]


def test_tokenize_splits_case_styles() -> None:
    assert tokenize("firstName login-button postal_code") == ["first", "name", "login", "button", "postal", "code"]


def test_description_matches_the_right_element() -> None:
    ranked = rank_candidates("Login submit button", PAGE)
    assert ranked[0][1] is LOGIN_BUTTON
    assert score_candidate("Username text input on the login form", USERNAME) > \
        score_candidate("Username text input on the login form", PASSWORD)


def test_heuristic_rejects_ambiguous_matches() -> None:
    assert pick_heuristic(rank_candidates("Add to cart button", ADD_BUTTONS)) is None


def test_build_locator_prefers_stable_attributes() -> None:
    assert build_locator(LOGIN_BUTTON) == 'css:[data-test="login-button"]'
    assert build_locator({**USERNAME, "data_test": ""}) == "id:user-name"
    assert build_locator({"tag": "input", "name": "q", "xpath": "/x"}) == 'css:input[name="q"]'
    assert build_locator(ADD_BUTTONS[0]) == "xpath:/html[1]/button[1]"


def test_heal_uses_heuristic_without_calling_ai() -> None:
    fake = FakeProvider("should not be used")
    healing = heal("login.submit", "css:#old", "Login submit button", PAGE, GuardedProvider(fake, 5))
    assert healing and healing.source == "heuristic"
    assert healing.new == 'css:[data-test="login-button"]'
    assert fake.prompts == []


def test_heal_asks_ai_when_heuristic_is_unsure() -> None:
    fake = FakeProvider('Sure: {"index": 1, "confidence": 0.8, "reason": "second card"}')
    healing = heal("inventory.add", "css:#old", "Add to cart button", ADD_BUTTONS, GuardedProvider(fake, 5))
    assert healing and healing.source == "ai"
    assert healing.new == "xpath:/html[1]/button[2]"
    assert "Add to cart button" in fake.prompts[0]


def test_heal_gives_up_without_ai() -> None:
    assert heal("k", "css:#old", "Add to cart button", ADD_BUTTONS, GuardedProvider(NullProvider(), 5)) is None


def test_parse_ai_choice_rejects_bad_answers() -> None:
    assert parse_ai_choice("no json here", 3) is None
    assert parse_ai_choice('{"index": 7, "confidence": 0.9}', 3) is None
    assert parse_ai_choice('{"index": 1, "confidence": 0.2}', 3) is None
    assert parse_ai_choice('{"index": null, "confidence": 0.9}', 3) is None
    assert parse_ai_choice('{"index": 2, "confidence": 0.9, "reason": "r"}', 3) == (2, 0.9, "r")
