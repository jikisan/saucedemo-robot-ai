from pathlib import Path

import pytest
import yaml

from libraries.utils import config as config_module
from libraries.utils.config import get_variables, load_config
from libraries.utils.data_loader import LOCATORS_FILE, get_locator, get_locator_entry, get_user

NO_ENV_FILE = Path("/nonexistent/.env")


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in ("BASE_URL", "BROWSER", "HEADLESS", "TIMEOUT", "AI_PROVIDER", "AI_MODEL",
                 "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AI_MAX_CALLS"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_config_defaults(clean_env: pytest.MonkeyPatch) -> None:
    config = load_config(NO_ENV_FILE)
    assert config.ai_provider == "none"
    assert config.headless is True
    assert config.timeout == 10.0


def test_config_reads_env(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("HEADLESS", "false")
    clean_env.setenv("BASE_URL", "https://example.test/")
    clean_env.setenv("AI_PROVIDER", "Anthropic")
    config = load_config(NO_ENV_FILE)
    assert config.headless is False
    assert config.base_url == "https://example.test"
    assert config.ai_provider == "anthropic"


def test_config_rejects_unknown_provider(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("AI_PROVIDER", "gemini")
    with pytest.raises(ValueError):
        load_config(NO_ENV_FILE)


def test_variable_file_hides_api_keys(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("ANTHROPIC_API_KEY", "secret")
    clean_env.setattr(config_module, "PROJECT_ROOT", Path("/nonexistent"))
    variables = get_variables()
    assert "BASE_URL" in variables
    assert "ANTHROPIC_API_KEY" not in variables


def test_get_user() -> None:
    assert get_user("standard") == {"username": "standard_user", "password": "secret_sauce"}
    with pytest.raises(KeyError):
        get_user("nobody")


def test_every_locator_has_primary_and_description() -> None:
    pages = yaml.safe_load(LOCATORS_FILE.read_text(encoding="utf-8"))
    for page, elements in pages.items():
        for element in elements:
            entry = get_locator_entry(f"{page}.{element}")
            assert entry["primary"] and entry["description"], f"{page}.{element}"


def test_get_locator() -> None:
    assert get_locator("login.username") == 'css:[data-test="username"]'
    with pytest.raises(KeyError):
        get_locator("login.missing")
