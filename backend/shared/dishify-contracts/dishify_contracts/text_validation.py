from __future__ import annotations

import unicodedata

MAX_QUERY_LENGTH = 512


def reject_control_characters(value: str, *, field_name: str) -> str:
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError(f"{field_name} must not contain control characters")
    return value
