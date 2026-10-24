import pytest
from car_catalog.config import Settings, get_settings


def test_default_settings() -> None:
    settings = Settings()
    assert settings.environment in {"development", "production", "test", "staging"}
    assert settings.app_name == "Car Catalog"
    assert "sqlite" in settings.database_url
    assert settings.log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def test_settings_custom_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Custom Catalog")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///custom_prod.db")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("API_PORT", "9000")
    settings = Settings()
    assert settings.app_name == "Custom Catalog"
    assert settings.environment == "production"
    assert settings.database_url == "sqlite:///custom_prod.db"
    assert settings.log_level == "DEBUG"
    assert settings.api_port == 9000


def test_get_settings_cached() -> None:
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
