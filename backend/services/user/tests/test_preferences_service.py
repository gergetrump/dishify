from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import app.preferences_service as preferences_service
from app.models.user_preferences import UserPreferencesRow


class _KeycloakStub:
	def get_user(self, _user_id: str) -> dict:
		return {
			"attributes": {
				"exclusion_restrictions": ["vegetarian"],
			}
		}


def test_load_preferences_handles_legacy_preferences_dict() -> None:
	original_get_preferences = preferences_service.get_preferences
	original_upsert_preferences = preferences_service.upsert_preferences
	original_clear_attrs = preferences_service.clear_preference_attributes

	try:
		preferences_service.get_preferences = lambda _user_uuid: None

		def _upsert(user_uuid: UUID, restrictions: list[str]) -> UserPreferencesRow:
			return UserPreferencesRow(
				user_id=user_uuid,
				exclusion_restrictions=restrictions,
				updated_at=datetime.now(timezone.utc),
			)

		preferences_service.upsert_preferences = _upsert
		preferences_service.clear_preference_attributes = lambda _user_id, _keycloak: None

		result = preferences_service.load_preferences(
			"00000000-0000-0000-0000-000000000001",
			_KeycloakStub(),
		)

		assert result.exclusion_restrictions == ["vegetarian"]
	finally:
		preferences_service.get_preferences = original_get_preferences
		preferences_service.upsert_preferences = original_upsert_preferences
		preferences_service.clear_preference_attributes = original_clear_attrs
