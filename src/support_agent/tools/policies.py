"""Expose local store policies as a JSON tool response."""

from __future__ import annotations

import json

from ..data import _get_policies_text


def read_policies() -> str:
    """Load and return the store policies."""
    return json.dumps({"policies": _get_policies_text()})
