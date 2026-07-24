import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        BASE_DIR, "instance", "site.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ITEMS_PER_PAGE = 20
    CURRENCY_SYMBOL = "Rs"

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15

    OTP_LENGTH = 6
    OTP_VALID_MINUTES = 5
    OTP_MAX_ATTEMPTS = 5
    OTP_RESEND_SECONDS = 60

    SESSION_IDLE_MINUTES = 30
    SESSION_ABSOLUTE_HOURS = 12
