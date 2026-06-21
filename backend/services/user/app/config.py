from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "dishify-user"
    database_url: str = "postgresql+psycopg://dishify:dishify@localhost:5432/dishify"
    keycloak_url: str = "http://localhost:9001"
    keycloak_public_url: str | None = None
    keycloak_realm: str = "dishify"
    keycloak_client_id: str = "dishify-backend"
    keycloak_login_client_id: str = "dishify-web"
    keycloak_client_secret: str = "backend-secret"
    keycloak_login_client_secret: str | None = (
        None  # uses keycloak_client_secret when set below
    )
    keycloak_ios_client_id: str = "dishify-ios"
    keycloak_web_client_id: str = "dishify-web"
    request_timeout_seconds: int = 30

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
