import pytest

from app.core.config import ConfigError, Settings

BASE_ENV = {
    "DATABASE_URL": "postgres://user:sandi-rahasia@db.example.com/two_beans",
    "SECRET_KEY": "k" * 32,
}

def test_postgres_url_uses_psycopg_driver():
    settings = Settings.from_env(BASE_ENV)
    assert settings.database_url == "postgresql+psycopg://user:sandi-rahasia@db.example.com/two_beans"

def test_local_defaults():
    settings = Settings.from_env(BASE_ENV)
    assert settings.app_env == "local"
    assert settings.allowed_origins == ("http://localhost:5173",)
    assert settings.cookie_secure is False
    assert (settings.session_idle_minutes, settings.session_max_hours) == (60, 12)
    assert (settings.login_rate_limit, settings.bcrypt_rounds) == ("5/minute", 12)
    assert settings.serverless is False

def test_all_errors_reported_at_once():
    with pytest.raises(ConfigError) as info:
        Settings.from_env({"SECRET_KEY": "pendek", "BCRYPT_ROUNDS": "dua belas", "LOGIN_RATE_LIMIT": "lima"})
    assert info.value.error == [
        "DATABASE_URL wajib diisi",
        "SECRET_KEY minimal 32 karakter",
        "LOGIN_RATE_LIMIT harus berbentuk seperti 5/minute",
        "BCRYPT_ROUNDS harus bilangan bulat 4 sampai 31",
    ]
    assert "backend/.env.example" in str(info.value)

def test_error_message_hides_secrets():
    with pytest.raises(ConfigError) as info:
        Settings.from_env({"DATABASE_URL": "mysql://user:sandi-rahasia@db/x", "SECRET_KEY": "rahasia-pendek"})
    assert "sandi-rahasia" not in str(info.value)
    assert "rahasia-pendek" not in str(info.value)

def test_repr_hides_secrets():
    text = repr(Settings.from_env(BASE_ENV))
    assert "sandi-rahasia" not in text
    assert "k" * 32 not in text

def test_production_requires_secure_cookie():
    assert Settings.from_env(BASE_ENV | {"APP_ENV": "production"}).cookie_secure is True
    with pytest.raises(ConfigError, match="COOKIE_SECURE wajib true"):
        Settings.from_env(BASE_ENV | {"APP_ENV": "production", "COOKIE_SECURE": "false"})

def test_idle_timeout_within_max_lifetime():
    with pytest.raises(ConfigError, match="SESSION_IDLE_MINUTES tidak boleh melebihi"):
        Settings.from_env(BASE_ENV | {"SESSION_IDLE_MINUTES": "800", "SESSION_MAX_HOURS": "12"})

def test_origins_normalized_and_vercel_urls_allowed():
    settings = Settings.from_env(BASE_ENV | {
        "ALLOWED_ORIGINS": "https://twobeans.example.com/, http://localhost:5173",
        "VERCEL": "1",
        "VERCEL_URL": "two-beans-app-a1b2c3.vercel.app",
        "VERCEL_PROJECT_PRODUCTION_URL": "two-beans-app.vercel.app",
    })
    assert settings.allowed_origins == (
        "https://twobeans.example.com",
        "http://localhost:5173",
        "https://two-beans-app-a1b2c3.vercel.app",
        "https://two-beans-app.vercel.app",
    )
    assert settings.serverless is True

@pytest.mark.parametrize("origin", ["localhost:5173", "ftp://example.com", "https://example.com/app"])
def test_invalid_origin_rejected(origin):
    with pytest.raises(ConfigError, match="ALLOWED_ORIGINS load origin tidak valid"):
        Settings.from_env(BASE_ENV | {"ALLOWED_ORIGINS": origin})
