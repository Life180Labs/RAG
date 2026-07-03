"""Shared Pydantic field validators for the tenancy hierarchy
(Organization/Workspace/Project schemas)."""

import re

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_slug(value: str) -> str:
    if not (3 <= len(value) <= 63):
        raise ValueError("Slug must be between 3 and 63 characters long.")
    if not _SLUG_PATTERN.match(value):
        raise ValueError(
            "Slug must contain only lowercase letters, digits, and single hyphens "
            "between segments (e.g. 'my-team')."
        )
    return value


def validate_name(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Name must not be empty.")
    if len(stripped) > 255:
        raise ValueError("Name must be at most 255 characters long.")
    return stripped
