import os
from datetime import timedelta


def _int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///finance.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_NAME = "ftracker_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    SESSION_IDLE_MINUTES = _int_env("SESSION_IDLE_MINUTES", 30)
    SESSION_ABSOLUTE_HOURS = _int_env("SESSION_ABSOLUTE_HOURS", 12)

    MAX_LOGIN_ATTEMPTS = _int_env("MAX_LOGIN_ATTEMPTS", 5)
    LOCKOUT_MINUTES = _int_env("LOCKOUT_MINUTES", 15)

    OTP_VALID_MINUTES = _int_env("OTP_VALID_MINUTES", 5)
    OTP_MAX_ATTEMPTS = _int_env("OTP_MAX_ATTEMPTS", 3)

    OTP_SHOW_IN_BROWSER = False

    ITEMS_PER_PAGE = 10
    CURRENCY_SYMBOL = "Rs."

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_MINUTES = _int_env("JWT_ACCESS_MINUTES", 15)


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    OTP_SHOW_IN_BROWSER = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name=None):
    name = name or os.getenv("FLASK_ENV", "development")
    return config_by_name.get(name, DevelopmentConfig)
