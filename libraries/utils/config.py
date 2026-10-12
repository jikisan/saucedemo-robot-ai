"""Run configuration read from environment variables and an optional ``.env`` file.

Used two ways:

- From Python: ``load_config()`` returns a typed, immutable ``Config``.
- From Robot Framework as a variable file: ``Variables    libraries/utils/config.py``
  exposes ``${BASE_URL}``, ``${BROWSER}``, ``${HEADLESS}``, ``${TIMEOUT}`` and the AI settings.

Real environment variables win over values in ``.env``.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_PROVIDERS = ("anthropic", "openai", "none")


@dataclass(frozen=True)
class Config:
    """Settings for one test run."""

    base_url: str = "https://www.saucedemo.com"
    browser: str = "chrome"
    headless: bool = True
    timeout: float = 10.0
    ai_provider: str = "none"
    ai_model: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ai_max_calls: int = 20


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def load_config(env_file: Path | None = None) -> Config:
    """Build a ``Config`` from the environment, loading ``.env`` from the project root first.

    Raises ``ValueError`` for an unknown ``AI_PROVIDER`` so a typo fails fast instead of
    silently disabling AI.
    """
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)
    defaults = Config()
    provider = _env("AI_PROVIDER", defaults.ai_provider).lower()
    if provider not in AI_PROVIDERS:
        raise ValueError(f"AI_PROVIDER must be one of {AI_PROVIDERS}, got {provider!r}")
    return Config(
        base_url=_env("BASE_URL", defaults.base_url).rstrip("/"),
        browser=_env("BROWSER", defaults.browser).lower(),
        headless=_env_bool("HEADLESS", defaults.headless),
        timeout=float(_env("TIMEOUT", str(defaults.timeout))),
        ai_provider=provider,
        ai_model=_env("AI_MODEL", defaults.ai_model),
        anthropic_api_key=_env("ANTHROPIC_API_KEY", ""),
        openai_api_key=_env("OPENAI_API_KEY", ""),
        ai_max_calls=int(_env("AI_MAX_CALLS", str(defaults.ai_max_calls))),
    )


def get_variables() -> dict[str, object]:
    """Robot Framework variable-file hook. API keys are deliberately not exposed."""
    config = asdict(load_config())
    secrets = {"anthropic_api_key", "openai_api_key"}
    return {key.upper(): value for key, value in config.items() if key not in secrets}
