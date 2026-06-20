from app.oidc_urls import publicize_oidc_config, publicize_oidc_url


def test_publicize_oidc_url_rewrites_internal_host() -> None:
	internal = "http://keycloak:9001/realms/dishify/protocol/openid-connect/auth"
	public = publicize_oidc_url(
		internal,
		internal_base="http://keycloak:9001",
		public_base="http://localhost:9001",
	)
	assert public == "http://localhost:9001/realms/dishify/protocol/openid-connect/auth"


def test_publicize_oidc_url_leaves_url_when_bases_match() -> None:
	url = "http://localhost:9001/realms/dishify"
	assert publicize_oidc_url(url, internal_base=url, public_base=url) == url


def test_publicize_oidc_config_rewrites_discovery_fields() -> None:
	config = {
		"issuer": "http://keycloak:9001/realms/dishify",
		"authorization_endpoint": "http://keycloak:9001/realms/dishify/protocol/openid-connect/auth",
		"token_endpoint": "http://keycloak:9001/realms/dishify/protocol/openid-connect/token",
		"end_session_endpoint": "http://keycloak:9001/realms/dishify/protocol/openid-connect/logout",
		"userinfo_endpoint": "http://keycloak:9001/realms/dishify/protocol/openid-connect/userinfo",
		"jwks_uri": "http://keycloak:9001/realms/dishify/protocol/openid-connect/certs",
	}
	public = publicize_oidc_config(
		config,
		internal_base="http://keycloak:9001",
		public_base="http://localhost:9001",
	)
	assert public["issuer"] == "http://localhost:9001/realms/dishify"
	assert public["authorization_endpoint"].startswith("http://localhost:9001/")
