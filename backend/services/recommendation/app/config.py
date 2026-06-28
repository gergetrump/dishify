from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "dishify-recommendation"
    retrieval_url: str = "http://localhost:8002"
    reasoning_url: str = "http://localhost:8003"
    semantic_weight: float = 0.7
    ingredient_weight: float = 0.3
    enable_llm_reasoning: bool = False
    request_timeout_seconds: int = 60
    # Only send the top N ranked recipes to the (slow) LLM explain stage; the rest
    # fall back to fast inventory-based reasoning.
    explain_max_recipes: int = 2


settings = Settings()
