"""Test data and locator lookup for Robot Framework and Python libraries.

Keywords:

- ``Get User`` returns credentials from ``data/users.yaml``.
- ``Get Locator`` returns the primary locator for a dotted key from ``locators/locators.yaml``,
  e.g. ``login.username``.

Files are parsed once per process and cached.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USERS_FILE = PROJECT_ROOT / "data" / "users.yaml"
LOCATORS_FILE = PROJECT_ROOT / "locators" / "locators.yaml"

__all__ = ["get_user", "get_locator", "get_locator_entry"]


@lru_cache(maxsize=None)
def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def get_user(name: str) -> dict[str, str]:
    """Return ``{username, password}`` for the user key ``name`` (e.g. ``standard``).

    Example: ``${user}=    Get User    standard``
    """
    users = _load_yaml(USERS_FILE)
    if name not in users:
        raise KeyError(f"Unknown user {name!r}. Known: {', '.join(sorted(users))}")
    entry = users[name]
    return {"username": entry["username"], "password": entry["password"]}


def get_locator_entry(key: str) -> dict[str, str]:
    """Return the full ``{primary, description}`` entry for a dotted locator key."""
    page, _, element = key.partition(".")
    entry = _load_yaml(LOCATORS_FILE).get(page, {}).get(element)
    if not entry:
        raise KeyError(f"Unknown locator key {key!r} in {LOCATORS_FILE.name}")
    return entry


def get_locator(key: str) -> str:
    """Return the primary locator for a dotted key.

    Example: ``${field}=    Get Locator    login.username``
    """
    return get_locator_entry(key)["primary"]
