from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UserPreferencesRow:
    user_id: UUID
    exclusion_restrictions: list[str]
    updated_at: datetime
