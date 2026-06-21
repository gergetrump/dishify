from __future__ import annotations

import json
from uuid import UUID

from app.db import get_pool
from app.models.user_preferences import UserPreferencesRow


def _row_from_record(
    user_id: UUID, restrictions: object, updated_at: object
) -> UserPreferencesRow:
    if isinstance(restrictions, str):
        parsed = json.loads(restrictions)
    elif isinstance(restrictions, list):
        parsed = restrictions
    else:
        parsed = list(restrictions or [])
    return UserPreferencesRow(
        user_id=user_id,
        exclusion_restrictions=[str(item) for item in parsed],
        updated_at=updated_at,
    )


def get_preferences(user_id: UUID) -> UserPreferencesRow | None:
    pool = get_pool()
    with pool.connection() as conn:
        row = conn.execute(
            """
			SELECT exclusion_restrictions, updated_at
			FROM user_preferences
			WHERE user_id = %s
			""",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_from_record(user_id, row[0], row[1])


def upsert_preferences(
    user_id: UUID,
    exclusion_restrictions: list[str],
) -> UserPreferencesRow:
    pool = get_pool()
    payload = json.dumps(exclusion_restrictions)
    with pool.connection() as conn:
        row = conn.execute(
            """
			INSERT INTO user_preferences (user_id, exclusion_restrictions)
			VALUES (%s, %s::jsonb)
			ON CONFLICT (user_id) DO UPDATE
			SET exclusion_restrictions = EXCLUDED.exclusion_restrictions,
			    updated_at = now()
			RETURNING exclusion_restrictions, updated_at
			""",
            (user_id, payload),
        ).fetchone()
        conn.commit()
    if row is None:
        raise RuntimeError("Failed to upsert user preferences")
    return _row_from_record(user_id, row[0], row[1])
