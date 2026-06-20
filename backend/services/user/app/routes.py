from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import user_id_from_claims, validate_token
from app.config import settings
from app.keycloak import KeycloakClient, KeycloakError, user_to_profile
from app.oidc_urls import publicize_oidc_config
from app.preferences_service import load_preferences, save_preferences, seed_preferences_on_register
from dishify_contracts import (
	AuthConfigResponse,
	HealthResponse,
	LoginRequest,
	RegisterRequest,
	RegisterResponse,
	TokenResponse,
	UpdatePreferencesRequest,
	UserPreferences,
	UserProfile,
)

router = APIRouter(tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)
_keycloak = KeycloakClient()


def require_claims(
	credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
	if credentials is None or credentials.scheme.lower() != "bearer":
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Missing bearer token",
		)
	try:
		return validate_token(credentials.credentials)
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid bearer token",
		) from exc


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
	return HealthResponse(status="ok", service=settings.app_name)


@router.get("/auth/config", response_model=AuthConfigResponse)
def auth_config() -> AuthConfigResponse:
	try:
		oidc = _keycloak.get_openid_config()
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail=f"Keycloak unavailable: {exc}",
		) from exc

	public_base = settings.keycloak_public_url or settings.keycloak_url
	oidc = publicize_oidc_config(
		oidc,
		internal_base=settings.keycloak_url,
		public_base=public_base,
	)

	return AuthConfigResponse(
		issuer=oidc["issuer"],
		authorization_endpoint=oidc["authorization_endpoint"],
		token_endpoint=oidc["token_endpoint"],
		logout_endpoint=oidc["end_session_endpoint"],
		userinfo_endpoint=oidc["userinfo_endpoint"],
		jwks_uri=oidc["jwks_uri"],
		realm=settings.keycloak_realm,
		clients={
			"ios": settings.keycloak_ios_client_id,
			"web": settings.keycloak_web_client_id,
			"backend": settings.keycloak_client_id,
			"api": settings.keycloak_login_client_id,
		},
	)


@router.post("/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest) -> RegisterResponse:
	try:
		user_id = _keycloak.register_user(
			username=body.username,
			email=body.email,
			password=body.password,
		)
		seed_preferences_on_register(user_id, body.exclusion_restrictions)
	except KeycloakError as exc:
		status_code = exc.status_code or status.HTTP_502_BAD_GATEWAY
		raise HTTPException(status_code=status_code, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail=f"Failed to store user preferences: {exc}",
		) from exc

	return RegisterResponse(
		id=user_id,
		username=body.username,
		email=body.email,
	)


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
	try:
		payload = _keycloak.login(body.username, body.password)
	except KeycloakError as exc:
		status_code = exc.status_code or status.HTTP_502_BAD_GATEWAY
		raise HTTPException(status_code=status_code, detail=str(exc)) from exc

	return TokenResponse(
		access_token=payload["access_token"],
		expires_in=int(payload.get("expires_in", 0)),
		refresh_token=payload.get("refresh_token"),
		token_type=payload.get("token_type", "Bearer"),
		scope=payload.get("scope"),
	)


@router.get("/me", response_model=UserProfile)
def get_me(claims: dict = Depends(require_claims)) -> UserProfile:
	user_id = user_id_from_claims(claims)
	try:
		user = _keycloak.get_user(user_id)
	except KeycloakError as exc:
		status_code = exc.status_code or status.HTTP_502_BAD_GATEWAY
		raise HTTPException(status_code=status_code, detail=str(exc)) from exc
	return UserProfile(**user_to_profile(user))


@router.get("/me/preferences", response_model=UserPreferences)
def get_preferences(claims: dict = Depends(require_claims)) -> UserPreferences:
	user_id = user_id_from_claims(claims)
	try:
		return load_preferences(user_id, _keycloak)
	except KeycloakError as exc:
		status_code = exc.status_code or status.HTTP_502_BAD_GATEWAY
		raise HTTPException(status_code=status_code, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail=f"Failed to load user preferences: {exc}",
		) from exc


@router.put("/me/preferences", response_model=UserPreferences)
def update_preferences(
	body: UpdatePreferencesRequest,
	claims: dict = Depends(require_claims),
) -> UserPreferences:
	user_id = user_id_from_claims(claims)
	try:
		return save_preferences(user_id, body.exclusion_restrictions, _keycloak)
	except KeycloakError as exc:
		status_code = exc.status_code or status.HTTP_502_BAD_GATEWAY
		raise HTTPException(status_code=status_code, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail=f"Failed to update user preferences: {exc}",
		) from exc
