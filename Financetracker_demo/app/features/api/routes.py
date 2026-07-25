from flask import current_app, jsonify, request

from app.extensions import db, limiter
from app.features.api import api_bp
from app.models.audit import EVENT_LOGIN_FAILED, EVENT_LOGIN_LOCKED, EVENT_LOGIN_SUCCESS
from app.models.security import LoginAttempt
from app.models.user import User
from app.security.audit import client_ip, log_event
from app.security.jwt_tokens import create_access_token
from app.security.ratelimit import LOGIN_LIMIT


@api_bp.route("/login", methods=["POST"])
@limiter.limit(LOGIN_LIMIT)
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").lower().strip()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    if user and user.is_currently_locked:
        LoginAttempt.record(email, client_ip(), False)
        log_event(EVENT_LOGIN_LOCKED, detail=email, user=user, commit=True)
        return jsonify(error="account_locked"), 423

    password_ok = bool(user and user.check_password(password))
    LoginAttempt.record(email, client_ip(), password_ok)

    if not password_ok:
        if user is not None:
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= current_app.config["MAX_LOGIN_ATTEMPTS"]:
                user.lock()
        log_event(EVENT_LOGIN_FAILED, detail=email, commit=True)
        return jsonify(error="invalid_credentials"), 401

    user.unlock()
    log_event(EVENT_LOGIN_SUCCESS, user=user, commit=True)
    db.session.commit()

    return jsonify(
        access_token=create_access_token(user),
        token_type="Bearer",
        expires_in=current_app.config["JWT_ACCESS_MINUTES"] * 60,
    )
