from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	app_name: str = "dishify-backend"
	disable_auth: bool = True
	database_url: str = "postgresql+psycopg://dishify:dishify@localhost:5432/dishify"
	qdrant_url: str = "http://localhost:6333"
	keycloak_url: str = "http://localhost:9001"
	keycloak_realm: str = "dishify"


settings = Settings()
