import os
import pytest
from unittest.mock import patch
from app.api.core.config import Settings

def test_settings_basic():
    """Test basic settings initialization."""
    with patch.dict('os.environ', {'ENVIRONMENT': 'development'}):
        settings = Settings()
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is True

def test_settings_environment_override():
    """Test environment variable override."""
    with patch.dict('os.environ', {'ENVIRONMENT': 'production', 'DEBUG': 'false'}):
        settings = Settings()
        assert settings.ENVIRONMENT == "production"
        assert settings.DEBUG is False

def test_settings_validation():
    """Test settings validation."""
    with patch.dict('os.environ', {
        'ENVIRONMENT': 'invalid',
        'LOG_LEVEL': 'INVALID'
    }):
        with pytest.raises(ValueError):
            Settings()

def test_settings_secrets():
    """Test handling of sensitive configuration."""
    with patch.dict('os.environ', {
        'SECRET_KEY': 'test-secret',
        'JWT_SECRET_KEY': 'test-jwt-secret'
    }):
        settings = Settings()
        settings_str = str(settings)
        assert 'test-secret' not in settings_str
        assert 'test-jwt-secret' not in settings_str
        assert 'SECRET_KEY=<hidden>' in settings_str
        assert 'JWT_SECRET_KEY=<hidden>' in settings_str

def test_settings_database_urls():
    """Test database URL construction."""
    with patch.dict('os.environ', {
        'POSTGRES_USER': 'testuser',
        'POSTGRES_PASSWORD': 'testpass',
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'testdb',
        'REDIS_URL': 'redis://localhost:6379/0',
        'CLICKHOUSE_HOST': 'localhost',
        'CLICKHOUSE_PORT': '8123'
    }):
        settings = Settings()
        assert settings.POSTGRES_URL == "postgresql://testuser:testpass@localhost:5432/testdb"
        assert settings.REDIS_URL == "redis://localhost:6379/0"

def test_settings_singleton():
    """Test settings singleton pattern."""
    settings1 = Settings()
    settings2 = Settings()
    assert settings1 is not settings2  # Each instance should be unique

def test_settings_cors():
    """Test CORS configuration."""
    with patch.dict('os.environ', {
        'CORS_ORIGINS': '["http://localhost:3000", "http://app.example.com"]'
    }):
        settings = Settings()
        assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://app.example.com"]
        assert settings.BACKEND_CORS_ORIGINS == settings.CORS_ORIGINS

def test_settings_logging():
    """Test logging configuration."""
    with patch.dict('os.environ', {
        'LOG_LEVEL': 'DEBUG',
        'LOG_FORMAT': 'json'
    }):
        settings = Settings()
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.LOG_FORMAT == "json"

def test_settings_feature_flags():
    """Test feature flag configuration."""
    with patch.dict('os.environ', {
        'ENABLE_METRICS': 'true',
        'ENABLE_TRACING': 'false'
    }):
        settings = Settings()
        assert settings.ENABLE_METRICS is True
        assert settings.ENABLE_TRACING is False

def test_settings_environment():
    """Test environment-specific settings."""
    with patch.dict('os.environ', {'ENVIRONMENT': 'test'}):
        settings = Settings()
        assert settings.ENVIRONMENT == "test"
        assert settings.DEBUG is True

def test_settings_cors_origins():
    """Test CORS origins configuration."""
    with patch.dict('os.environ', {
        'CORS_ORIGINS': '["http://localhost:3000", "http://app.example.com"]'
    }):
        settings = Settings()
        assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://app.example.com"]

def test_settings_secret_keys():
    """Test secret key configuration."""
    with patch.dict('os.environ', {
        'SECRET_KEY': 'test-secret',
        'JWT_SECRET_KEY': 'test-jwt'
    }):
        settings = Settings()
        assert settings.SECRET_KEY == "test-secret"
        assert settings.JWT_SECRET_KEY == "test-jwt"

def test_settings_str_representation():
    """Test string representation of settings."""
    settings = Settings()
    settings_str = str(settings)
    assert "SECRET_KEY=<hidden>" in settings_str
    assert "JWT_SECRET_KEY=<hidden>" in settings_str
    assert "test-secret-key" not in settings_str
    assert "test-jwt-key" not in settings_str

def test_settings_cors_origins_validation():
    """Test CORS origins validation."""
    # Test with empty value (should use default)
    with patch.dict(os.environ, {
        'ENVIRONMENT': 'test',
        'CORS_ORIGINS': ''
    }, clear=True):
        settings = Settings()
        assert settings.CORS_ORIGINS == ["http://localhost:3000"]

    # Test with single URL
    with patch.dict(os.environ, {
        'ENVIRONMENT': 'test',
        'CORS_ORIGINS': 'http://localhost:3000'
    }, clear=True):
        settings = Settings()
        assert settings.CORS_ORIGINS == ["http://localhost:3000"]

    # Test with comma-separated list
    with patch.dict(os.environ, {
        'ENVIRONMENT': 'test',
        'CORS_ORIGINS': 'http://localhost:3000,http://app.example.com'
    }, clear=True):
        settings = Settings()
        assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://app.example.com"]

    # Test with JSON array string
    with patch.dict(os.environ, {
        'ENVIRONMENT': 'test',
        'CORS_ORIGINS': '["http://localhost:3000", "http://app.example.com"]'
    }, clear=True):
        settings = Settings()
        assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://app.example.com"] 