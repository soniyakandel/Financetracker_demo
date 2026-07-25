import uuid
from datetime import timedelta
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from app.extensions import db
from app.models.base import utcnow
from app.models.user import User

ACCESS = "access"


def _secret():
    return current_app.config.get("JWT_SECRET_KEY") or current_app.config["SECRET_KEY"]


def _algorithm():
    return current_app.config["JWT_ALGORITHM"]


def create_access_token(user):
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "type": ACCESS,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=current_app.config["JWT_ACCESS_MINUTES"]),
    }
    return jwt.encode(payload, _secret(), algorithm=_algorithm())


def decode_token(token, expected_type=ACCESS):
    payload = jwt.decode(token, _secret(), algorithms=[_algorithm()])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


def current_api_user():
    return getattr(g, "api_user", None)


def token_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="missing_token"), 401

        try:
            payload = decode_token(header[7:].strip())
        except jwt.ExpiredSignatureError:
            return jsonify(error="token_expired"), 401
        except jwt.InvalidTokenError:
            return jsonify(error="invalid_token"), 401

        user = db.session.get(User, int(payload["sub"]))
        if user is None or not user.is_active:
            return jsonify(error="invalid_token"), 401

        g.api_user = user
        return view(*args, **kwargs)

    return wrapper
