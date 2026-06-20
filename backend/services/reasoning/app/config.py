from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	app_name: str = "dishify-reasoning"
	enable_llm_reasoning: bool = False
	llm_provider: str = "openrouter"
	openrouter_api_key: str | None = None
	openrouter_model: str | None = None
	openrouter_base_url: str | None = None
	llm_timeout_seconds: int = 30


settings = Settings()
