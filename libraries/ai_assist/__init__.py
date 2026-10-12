"""AI Test Assistant: runtime helpers that support testers (triage, self-healing, visual checks).

All features work without AI; a configured provider only adds richer explanations.
"""

from libraries.ai_assist.providers import AIProvider, GuardedProvider, NullProvider, get_provider

__all__ = ["AIProvider", "GuardedProvider", "NullProvider", "get_provider"]
