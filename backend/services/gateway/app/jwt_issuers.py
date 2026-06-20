from __future__ import annotations


def accepted_issuers(*, keycloak_url: str, keycloak_realm: str, keycloak_public_url: str | None = None) -> list[str]:
	"""Return JWT issuers that Keycloak may use for the same realm."""
	issuers: list[str] = []
	for base in (keycloak_url, keycloak_public_url):
		if not base:
			continue
		issuer = f"{base.rstrip('/')}/realms/{keycloak_realm}"
		if issuer not in issuers:
			issuers.append(issuer)
	return issuers
