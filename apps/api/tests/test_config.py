from app.core.config import Settings


def test_settings_load_environment_values(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("SCRAPER_MAX_PAGES", "3")
    monkeypatch.setenv("SCRAPER_MAX_RETRIES", "4")
    monkeypatch.setenv("SCRAPER_SCREENSHOTS_ENABLED", "false")
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", "./custom-storage")

    settings = Settings()

    assert settings.app_env == "test"
    assert settings.database_url == "sqlite:///:memory:"
    assert settings.llm_provider == "mock"
    assert settings.scraper_max_pages == 3
    assert settings.scraper_max_retries == 4
    assert settings.scraper_screenshots_enabled is False
    assert str(settings.local_storage_root) == "custom-storage"
