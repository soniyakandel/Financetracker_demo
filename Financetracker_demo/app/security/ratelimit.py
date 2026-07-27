from flask import render_template, request

from app.models.audit import EVENT_ACCESS_DENIED
from app.security.audit import log_event

LOGIN_LIMIT = "10 per minute; 40 per hour"
REGISTER_LIMIT = "5 per minute; 20 per hour"
OTP_VERIFY_LIMIT = "10 per minute; 30 per hour"
OTP_RESEND_LIMIT = "3 per minute; 10 per hour"
PASSWORD_CHANGE_LIMIT = "5 per minute; 20 per hour"

PASSWORD_RESET_REQUEST_LIMIT = "3 per minute; 10 per hour"
PASSWORD_RESET_SUBMIT_LIMIT = "10 per minute; 30 per hour"

WRITE_LIMIT = "60 per minute"


def register_ratelimit_handlers(app):
    @app.errorhandler(429)
    def handle_rate_limited(error):
        log_event(
            EVENT_ACCESS_DENIED,
            detail=f"Rate limit hit on {request.path}",
            commit=True,
        )
        return render_template("errors/429.html", error=error), 429
