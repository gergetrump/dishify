from pydantic import BaseModel, EmailStr, Field, field_validator

from dishify_contracts.restrictions import validate_restriction_tags


class AuthConfigResponse(BaseModel):
	issuer: str
	authorization_endpoint: str
	token_endpoint: str
	logout_endpoint: str
	userinfo_endpoint: str
	jwks_uri: str
	realm: str
	clients: dict[str, str]


class RegisterRequest(BaseModel):
	username: str = Field(..., min_length=3, max_length=64)
	email: EmailStr
	password: str = Field(..., min_length=8, max_length=128)
	exclusion_restrictions: list[str] | None = None

	@field_validator("exclusion_restrictions")
	@classmethod
	def _validate_exclusion_restrictions(cls, value: list[str] | None) -> list[str] | None:
		return validate_restriction_tags(value)


class RegisterResponse(BaseModel):
	id: str
	username: str
	email: str
	message: str = "Registration successful"


class LoginRequest(BaseModel):
	username: str = Field(..., min_length=1)
	password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
	refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
	refresh_token: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
	access_token: str
	expires_in: int
	refresh_token: str | None = None
	token_type: str = "Bearer"
	scope: str | None = None


class UserProfile(BaseModel):
	id: str
	username: str | None = None
	email: str | None = None
	email_verified: bool | None = None
	first_name: str | None = None
	last_name: str | None = None


class UserPreferences(BaseModel):
	exclusion_restrictions: list[str] = Field(default_factory=list)


class UpdatePreferencesRequest(BaseModel):
	exclusion_restrictions: list[str] | None = None

	@field_validator("exclusion_restrictions")
	@classmethod
	def _validate_exclusion_restrictions(cls, value: list[str] | None) -> list[str] | None:
		return validate_restriction_tags(value)
