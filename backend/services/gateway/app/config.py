from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "dishify-backend"
    disable_auth: bool = True
    recommendation_url: str = "http://localhost:8001"
    user_url: str = "http://localhost:8004"
    ingest_url: str = "http://localhost:8005"
    reasoning_url: str = "http://localhost:8003"
    keycloak_url: str = "http://localhost:9001"
    keycloak_public_url: str | None = None
    keycloak_realm: str = "dishify"
    request_timeout_seconds: int = 60

    @property
    def keycloak_internal_base_url(self) -> str:
        return self.keycloak_url.rstrip("/")

    @property
    def keycloak_public_base_url(self) -> str:
        return (self.keycloak_public_url or self.keycloak_url).rstrip("/")

    @property
    def keycloak_internal_realm_url(self) -> str:
        return f"{self.keycloak_internal_base_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_public_realm_url(self) -> str:
        return f"{self.keycloak_public_base_url}/realms/{self.keycloak_realm}"


settings = Settings()
