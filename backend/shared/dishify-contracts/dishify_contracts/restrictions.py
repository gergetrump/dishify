from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path


class InvalidRestrictionTagsError(ValueError):
    def __init__(self, unknown: list[str]):
        self.unknown = unknown
        super().__init__(f"Unknown restriction tags: {', '.join(unknown)}")


def _rules_path() -> Path:
    if env_path := os.environ.get("RESTRICTION_RULES_PATH"):
        return Path(env_path)

    candidates = [
        Path(__file__).resolve().parents[4] / "data" / "restriction_rules.json",
        Path("/data/restriction_rules.json"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "restriction_rules.json not found; set RESTRICTION_RULES_PATH"
    )


@lru_cache(maxsize=1)
def get_allowed_restriction_keys() -> frozenset[str]:
    path = _rules_path()
    with path.open("r", encoding="utf-8") as handle:
        rules = json.load(handle)
    return frozenset(str(key) for key in rules)


def validate_restriction_tags(tags: list[str] | None) -> list[str] | None:
    if tags is None:
        return None

    allowed = get_allowed_restriction_keys()
    unknown = [tag for tag in tags if tag not in allowed]
    if unknown:
        raise InvalidRestrictionTagsError(unknown)
    return tags
