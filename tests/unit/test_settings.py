from __future__ import annotations

from src.shared.config.settings import Environment, get_settings


def test_settings_load_with_defaults(monkeypatch) -> None:
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.app_name == "AI Job Application Platform"
    assert settings.environment in (Environment.DEVELOPMENT, Environment.TESTING)
    assert 0.0 <= settings.minimum_match_score_to_apply <= 1.0


def test_settings_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.is_production is True
    get_settings.cache_clear()


def test_cors_origins_list_parses_comma_separated(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://a.com, http://b.com")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.cors_origins_list == ["http://a.com", "http://b.com"]
    get_settings.cache_clear()
