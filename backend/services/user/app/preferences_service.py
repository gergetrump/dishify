from __future__ import annotations

from uuid import UUID

from app.keycloak import (
	KeycloakClient,
	KeycloakError,
	attribute_list,
	clear_preference_attributes,
	user_to_preferences,
)
from app.models.user_preferences import UserPreferencesRow
from app.preferences_store import get_preferences, upsert_preferences
from dishify_contracts import UserPreferences


def row_to_user_preferences(row: UserPreferencesRow | None) -> UserPreferences:
	if row is None:
		return UserPreferences(exclusion_restrictions=[])
	return UserPreferences(exclusion_restrictions=row.exclusion_restrictions)


def load_preferences(user_id: str, keycloak: KeycloakClient) -> UserPreferences:
	user_uuid = UUID(user_id)
	row = get_preferences(user_uuid)
	if row is not None:
		return row_to_user_preferences(row)

	try:
		user = keycloak.get_user(user_id)
	except KeycloakError:
		return UserPreferences(exclusion_restrictions=[])

	legacy = user_to_preferences(user)
	restrictions = legacy.exclusion_restrictions
	if not restrictions:
		return UserPreferences(exclusion_restrictions=[])

	row = upsert_preferences(user_uuid, restrictions)
	try:
		clear_preference_attributes(user_id, keycloak)
	except KeycloakError:
		pass
	return row_to_user_preferences(row)


def save_preferences(
	user_id: str,
	exclusion_restrictions: list[str] | None,
	keycloak: KeycloakClient,
) -> UserPreferences:
	user_uuid = UUID(user_id)
	if exclusion_restrictions is None:
		return load_preferences(user_id, keycloak)

	row = upsert_preferences(user_uuid, exclusion_restrictions)
	return row_to_user_preferences(row)


def seed_preferences_on_register(
	user_id: str,
	exclusion_restrictions: list[str] | None,
) -> None:
	if not exclusion_restrictions:
		return
	upsert_preferences(UUID(user_id), exclusion_restrictions)
