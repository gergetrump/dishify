from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	app_name: str = "dishify-backend"
	disable_auth: bool = True
	recommendation_url: str = "http://localhost:8001"
	user_url: str = "http://localhost:8004"
	keycloak_url: str = "http://localhost:9001"
	keycloak_public_url: str | None = None
	keycloak_realm: str = "dishify"
	request_timeout_seconds: int = 60


settings = Settings()
