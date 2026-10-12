import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from libraries.ai_assist.providers import (
    AnthropicProvider,
    GuardedProvider,
    NullProvider,
    OpenAIProvider,
    create_provider,
)
from libraries.utils.config import Config
from unit_tests.fakes import FakeProvider

PNG_BYTES = b"\x89PNG\r\n\x1a\nfake"


@pytest.fixture
def image(tmp_path: Path) -> Path:
    path = tmp_path / "shot.png"
    path.write_bytes(PNG_BYTES)
    return path


# --- GuardedProvider -------------------------------------------------------

def test_guard_returns_answer_and_counts_calls() -> None:
    guard = GuardedProvider(FakeProvider("hello"), max_calls=5)
    assert guard.complete("hi") == "hello"
    assert guard.calls_made == 1


def test_guard_swallows_provider_errors(caplog: pytest.LogCaptureFixture) -> None:
    guard = GuardedProvider(FakeProvider(RuntimeError("boom")), max_calls=5)
    assert guard.complete("hi") is None
    assert "boom" in caplog.text


def test_guard_stops_at_budget() -> None:
    fake = FakeProvider("a", "b", "c")
    guard = GuardedProvider(fake, max_calls=2)
    assert [guard.complete("x") for _ in range(3)] == ["a", "b", None]
    assert len(fake.prompts) == 2
    assert guard.available is False


def test_guard_treats_empty_answer_as_none() -> None:
    assert GuardedProvider(FakeProvider(""), max_calls=1).complete("x") is None


def test_null_provider_is_never_called_or_counted() -> None:
    guard = GuardedProvider(NullProvider(), max_calls=1)
    assert guard.complete("x") is None
    assert guard.complete_with_image("x", "shot.png") is None
    assert guard.calls_made == 0


def test_guard_passes_image_through(image: Path) -> None:
    fake = FakeProvider("looks fine")
    assert GuardedProvider(fake, max_calls=1).complete_with_image("check", image) == "looks fine"
    assert fake.images == [str(image)]


# --- create_provider -------------------------------------------------------

@pytest.mark.parametrize("config", [
    Config(ai_provider="none"),
    Config(ai_provider="anthropic", ai_model="some-model"),               # no key
    Config(ai_provider="openai", openai_api_key="k"),                     # no model
])
def test_create_provider_falls_back_to_null(config: Config) -> None:
    assert isinstance(create_provider(config), NullProvider)


def test_create_provider_falls_back_when_sdk_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)  # makes `import anthropic` fail
    config = Config(ai_provider="anthropic", ai_model="m", anthropic_api_key="k")
    assert isinstance(create_provider(config), NullProvider)


# --- SDK adapters (fake SDK modules, no network) ---------------------------

class _Recorder:
    def __init__(self, response: object) -> None:
        self.response = response
        self.kwargs: dict = {}

    def create(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return self.response


def _fake_anthropic(monkeypatch: pytest.MonkeyPatch, response: object) -> _Recorder:
    recorder = _Recorder(response)
    client = SimpleNamespace(messages=recorder)
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=lambda api_key: client))
    return recorder


def test_anthropic_provider_joins_text_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(stop_reason="end_turn", content=[
        SimpleNamespace(type="thinking", thinking=""),
        SimpleNamespace(type="text", text="root "),
        SimpleNamespace(type="text", text="cause"),
    ])
    recorder = _fake_anthropic(monkeypatch, response)
    provider = create_provider(Config(ai_provider="anthropic", ai_model="model-x", anthropic_api_key="k"))
    assert isinstance(provider, AnthropicProvider)
    assert provider.complete("why?") == "root cause"
    assert recorder.kwargs["model"] == "model-x"


def test_anthropic_provider_returns_empty_on_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_anthropic(monkeypatch, SimpleNamespace(stop_reason="refusal", content=[]))
    assert AnthropicProvider(api_key="k", model="m").complete("x") == ""


def test_anthropic_provider_sends_base64_image(monkeypatch: pytest.MonkeyPatch, image: Path) -> None:
    response = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="ok")])
    recorder = _fake_anthropic(monkeypatch, response)
    AnthropicProvider(api_key="k", model="m").complete_with_image("look", image)
    image_block, text_block = recorder.kwargs["messages"][0]["content"]
    assert image_block["source"]["media_type"] == "image/png"
    assert text_block == {"type": "text", "text": "look"}


def test_openai_provider_sends_data_url(monkeypatch: pytest.MonkeyPatch, image: Path) -> None:
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])
    recorder = _Recorder(response)
    client = SimpleNamespace(chat=SimpleNamespace(completions=recorder))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda api_key: client))
    provider = OpenAIProvider(api_key="k", model="gpt-x")
    assert provider.complete_with_image("look", image) == "ok"
    image_part = recorder.kwargs["messages"][0]["content"][1]
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")
    assert recorder.kwargs["model"] == "gpt-x"

