"""LLM provider abstraction for the AI Test Assistant.

Every AI feature talks to a ``GuardedProvider`` obtained from ``get_provider()``. It:

- picks ``AnthropicProvider``, ``OpenAIProvider`` or ``NullProvider`` from config,
- never raises: an SDK/network/auth error is logged as a warning and returns ``None``,
- enforces ``AI_MAX_CALLS`` across all AI features in the process.

SDKs are imported lazily, so neither ``anthropic`` nor ``openai`` has to be installed
when ``AI_PROVIDER=none``. Model ids come from ``AI_MODEL``; nothing here hardcodes one.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from libraries.utils.config import Config, load_config

logger = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 4000


def _encode_image(image_path: str | Path) -> tuple[str, str]:
    """Return ``(media_type, base64_data)`` for an image file."""
    path = Path(image_path)
    media_type = mimetypes.guess_type(path.name)[0] or "image/png"
    return media_type, base64.standard_b64encode(path.read_bytes()).decode("ascii")


class AIProvider(ABC):
    """Base class: one prompt in, plain text out."""

    name: str = "base"

    @property
    def available(self) -> bool:
        return True

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return the model's text answer to ``prompt``."""

    @abstractmethod
    def complete_with_image(self, prompt: str, image_path: str | Path) -> str:
        """Return the model's text answer to ``prompt`` about the image at ``image_path``."""


class NullProvider(AIProvider):
    """Used when AI is disabled or misconfigured. Callers fall back to heuristics."""

    name = "none"

    @property
    def available(self) -> bool:
        return False

    def complete(self, prompt: str) -> str:
        return ""

    def complete_with_image(self, prompt: str, image_path: str | Path) -> str:
        return ""


class AnthropicProvider(AIProvider):
    """Claude via the official ``anthropic`` SDK."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        import anthropic  # lazy: optional dependency

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def _send(self, content: str | list[dict]) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_OUTPUT_TOKENS,
            messages=[{"role": "user", "content": content}],
        )
        if response.stop_reason == "refusal":
            logger.warning("AI provider declined the request (stop_reason=refusal).")
            return ""
        return "".join(block.text for block in response.content if block.type == "text")

    def complete(self, prompt: str) -> str:
        return self._send(prompt)

    def complete_with_image(self, prompt: str, image_path: str | Path) -> str:
        media_type, data = _encode_image(image_path)
        return self._send([
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
            {"type": "text", "text": prompt},
        ])


class OpenAIProvider(AIProvider):
    """OpenAI chat models via the official ``openai`` SDK."""

    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        import openai  # lazy: optional dependency

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def _send(self, content: str | list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_completion_tokens=MAX_OUTPUT_TOKENS,
            messages=[{"role": "user", "content": content}],
        )
        return response.choices[0].message.content or ""

    def complete(self, prompt: str) -> str:
        return self._send(prompt)

    def complete_with_image(self, prompt: str, image_path: str | Path) -> str:
        media_type, data = _encode_image(image_path)
        return self._send([
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}},
        ])


class GuardedProvider:
    """Wraps a provider with a call budget and blanket error handling.

    Returns ``None`` when AI is unavailable, the budget is spent, or the call failed,
    so callers can write ``answer = ai.complete(p)`` / ``if answer is None: heuristic()``.
    """

    def __init__(self, provider: AIProvider, max_calls: int) -> None:
        self.provider = provider
        self.max_calls = max_calls
        self.calls_made = 0

    @property
    def available(self) -> bool:
        return self.provider.available and self.calls_made < self.max_calls

    def complete(self, prompt: str) -> str | None:
        return self._call(lambda: self.provider.complete(prompt))

    def complete_with_image(self, prompt: str, image_path: str | Path) -> str | None:
        return self._call(lambda: self.provider.complete_with_image(prompt, image_path))

    def _call(self, request) -> str | None:
        if not self.provider.available:
            return None
        if self.calls_made >= self.max_calls:
            logger.warning("AI call budget (AI_MAX_CALLS=%d) spent; using heuristics.", self.max_calls)
            return None
        self.calls_made += 1
        try:
            return request() or None
        except Exception as error:  # noqa: BLE001 - AI must never fail a test
            logger.warning("AI call via %s failed, using heuristics: %s", self.provider.name, error)
            return None


def create_provider(config: Config) -> AIProvider:
    """Build the provider named by ``config.ai_provider``; ``NullProvider`` on any gap."""
    if config.ai_provider == "none":
        return NullProvider()
    key = {"anthropic": config.anthropic_api_key, "openai": config.openai_api_key}[config.ai_provider]
    if not key or not config.ai_model:
        logger.warning("AI_PROVIDER=%s but API key or AI_MODEL is missing; AI disabled.", config.ai_provider)
        return NullProvider()
    provider_class = AnthropicProvider if config.ai_provider == "anthropic" else OpenAIProvider
    try:
        return provider_class(api_key=key, model=config.ai_model)
    except Exception as error:  # noqa: BLE001 - missing SDK or bad client config
        logger.warning("Could not initialise %s provider, AI disabled: %s", config.ai_provider, error)
        return NullProvider()


@lru_cache(maxsize=1)
def get_provider() -> GuardedProvider:
    """Process-wide provider, so ``AI_MAX_CALLS`` is shared by all AI features.

    ponytail: budget is per process; under pabot each worker gets its own budget.
    A cross-process counter (file lock) is the upgrade if that matters.
    """
    config = load_config()
    return GuardedProvider(create_provider(config), config.ai_max_calls)
