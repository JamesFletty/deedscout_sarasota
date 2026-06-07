from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./deedscout.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    app_env: str = Field(default="local", alias="APP_ENV")
    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_max_calls_per_batch: int = Field(default=25, alias="LLM_MAX_CALLS_PER_BATCH", ge=0)
    llm_max_input_chars: int = Field(default=4000, alias="LLM_MAX_INPUT_CHARS", gt=0)
    llm_require_json: bool = Field(default=True, alias="LLM_REQUIRE_JSON")
    llm_timeout_seconds: int = Field(default=30, alias="LLM_TIMEOUT_SECONDS", gt=0)
    llm_retry_count: int = Field(default=1, alias="LLM_RETRY_COUNT", ge=0)
    scraper_headless: bool = Field(default=True, alias="SCRAPER_HEADLESS")
    scraper_max_pages: int = Field(default=150, alias="SCRAPER_MAX_PAGES", ge=1)
    scraper_max_retries: int = Field(default=2, alias="SCRAPER_MAX_RETRIES", ge=0)
    scraper_delay_ms: int = Field(default=1500, alias="SCRAPER_DELAY_MS", ge=0)
    scraper_timeout_ms: int = Field(default=30000, alias="SCRAPER_TIMEOUT_MS", gt=0)
    scraper_screenshots_enabled: bool = Field(default=True, alias="SCRAPER_SCREENSHOTS_ENABLED")
    scraper_save_html_enabled: bool = Field(default=True, alias="SCRAPER_SAVE_HTML_ENABLED")
    scraper_user_agent: str = Field(
        default="DeedScout Sarasota research-triage bot; public-record snapshot preservation",
        alias="SCRAPER_USER_AGENT",
        min_length=1,
    )
    local_storage_root: Path = Field(
        default=Path("./.storage"),
        validation_alias=AliasChoices("LOCAL_STORAGE_ROOT", "LOCAL_ARTIFACT_ROOT"),
    )
    sarasota_fixtures_dir: Path | None = Field(default=None, alias="SARASOTA_FIXTURES_DIR")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", populate_by_name=True, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
