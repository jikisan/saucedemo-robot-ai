"""Test doubles shared by the unit tests. No network."""

from __future__ import annotations

from pathlib import Path

from libraries.ai_assist.providers import AIProvider


class FakeProvider(AIProvider):
    """Returns scripted answers in order and records every prompt.

    An answer that is an ``Exception`` instance is raised instead of returned.
    """

    name = "fake"

    def __init__(self, *answers: str | Exception) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []
        self.images: list[str] = []

    def _next(self) -> str:
        answer = self.answers.pop(0) if self.answers else ""
        if isinstance(answer, Exception):
            raise answer
        return answer

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._next()

    def complete_with_image(self, prompt: str, image_path: str | Path) -> str:
        self.prompts.append(prompt)
        self.images.append(str(image_path))
        return self._next()
