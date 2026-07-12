from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "dishify-ingest"

    # Gemini (native multimodal: handles both audio transcription and image vision).
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_transcribe_model: str = "gemini-2.5-flash"
    gemini_vision_model: str = "gemini-2.5-flash"
    # gemini-2.5 models "think" by default, which adds latency we don't need for
    # transcription / detection. 0 disables it; -1 would mean dynamic/auto.
    gemini_thinking_budget: int = 0

    request_timeout_seconds: int = 60
    # Reject decoded uploads larger than this (Gemini inline data caps around 20MB).
    max_upload_bytes: int = 15 * 1024 * 1024


settings = Settings()
