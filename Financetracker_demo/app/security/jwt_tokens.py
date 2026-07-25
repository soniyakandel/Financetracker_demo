import uuid
from datetime import timedelta

import jwt
from flask import current_app

from app.models.base import utcnow

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
