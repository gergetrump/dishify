from app.jwt_issuers import accepted_issuers


def test_accepted_issuers_includes_internal_and_public_hosts() -> None:
	issuers = accepted_issuers(
		keycloak_url="http://keycloak:9001",
		keycloak_realm="dishify",
		keycloak_public_url="http://localhost:9001",
	)
	assert issuers == [
		"http://keycloak:9001/realms/dishify",
		"http://localhost:9001/realms/dishify",
	]


def test_accepted_issuers_deduplicates_matching_bases() -> None:
	issuers = accepted_issuers(
		keycloak_url="http://localhost:9001",
		keycloak_realm="dishify",
		keycloak_public_url="http://localhost:9001",
	)
	assert issuers == ["http://localhost:9001/realms/dishify"]
