from flask import flash, redirect, request, session, url_for
from flask_login import current_user, logout_user

from app.extensions import db
from app.models.audit import EVENT_SESSION_EXPIRED
from app.models.session import UserSession
from app.security.audit import log_event

SESSION_TOKEN_KEY = "session_token"

EXEMPT_ENDPOINTS = {
    "static",
    "core.landing",
    "core.healthz",
    "auth.login",
    "auth.register",
    "auth.verify_otp",
    "auth.resend_otp",
}


def _end_session(message, reason):
    log_event(EVENT_SESSION_EXPIRED, detail=reason)
    db.session.commit()

    logout_user()
    session.clear()
    flash(message, "warning")
    return redirect(url_for("auth.login"))


def register_session_guard(app):
    @app.before_request
    def _enforce_session_rules():
        if request.endpoint in EXEMPT_ENDPOINTS or request.endpoint is None:
            return None
        if not current_user.is_authenticated:
            return None

        token = session.get(SESSION_TOKEN_KEY)
        record = (
            UserSession.query.filter_by(session_token=token).first() if token else None
        )

        if record is None or record.user_id != current_user.id:
            return _end_session(
                "Your session is no longer valid. Please sign in again.",
                "Session token did not match a live session",
            )

        if not record.is_active:
            return _end_session(
                "This device was signed out from your account. Please sign in again.",
                f"Session revoked ({record.revoked_reason})",
            )

        if record.is_absolute_expired:
            record.revoke(reason="absolute_timeout")
            return _end_session(
                "You have been signed out because sessions expire after "
                f"{app.config['SESSION_ABSOLUTE_HOURS']} hours.",
                "Absolute session lifetime reached",
            )

        if record.is_idle_expired:
            record.revoke(reason="idle_timeout")
            return _end_session(
                "You were signed out after "
                f"{app.config['SESSION_IDLE_MINUTES']} minutes of inactivity.",
                "Idle timeout reached",
            )

        record.touch()
        db.session.commit()
        return None
