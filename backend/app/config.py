from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	app_name: str = "dishify-backend"
	disable_auth: bool = True
	database_url: str = "postgresql+psycopg://dishify:dishify@localhost:5432/dishify"
	qdrant_url: str = "http://localhost:6333"
	qdrant_api_key: str | None = None
	qdrant_collection: str = "recipes_10000"
	embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
	semantic_weight: float = 0.7
	ingredient_weight: float = 0.3
	enable_llm_reasoning: bool = False
	llm_provider: str = "openrouter"
	openrouter_api_key: str | None = None
	openrouter_model: str | None = None
	openrouter_base_url: str | None = None
	llm_timeout_seconds: int = 30
	keycloak_url: str = "http://localhost:9001"
	keycloak_realm: str = "dishify"


settings = Settings()
