from __future__ import annotations


def publicize_oidc_url(url: str, *, internal_base: str, public_base: str) -> str:
	"""Rewrite an OIDC URL from the internal Keycloak base to the client-facing base."""
	internal = internal_base.rstrip("/")
	public = public_base.rstrip("/")
	if internal == public or not url.startswith(internal):
		return url
	return public + url[len(internal) :]


def publicize_oidc_config(config: dict[str, str], *, internal_base: str, public_base: str) -> dict[str, str]:
	"""Return a copy of OIDC discovery fields with public-facing hostnames."""
	keys = (
		"issuer",
		"authorization_endpoint",
		"token_endpoint",
		"end_session_endpoint",
		"userinfo_endpoint",
		"jwks_uri",
	)
	result = dict(config)
	for key in keys:
		value = result.get(key)
		if isinstance(value, str):
			result[key] = publicize_oidc_url(value, internal_base=internal_base, public_base=public_base)
	return result
