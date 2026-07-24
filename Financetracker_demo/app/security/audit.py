from flask import has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models.audit import AuditLog


def client_ip():
    if not has_request_context():
        return None
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return (request.remote_addr or "")[:45]


def client_agent():
    if not has_request_context():
        return None
    return (request.headers.get("User-Agent") or "")[:255]


def log_event(event, detail=None, user=None, commit=False):
    user_id = None
    if user is not None:
        user_id = user.id
    elif current_user and getattr(current_user, "is_authenticated", False):
        user_id = current_user.id

    entry = AuditLog(
        user_id=user_id,
        event=event,
        detail=(detail or "")[:255] or None,
        ip_address=client_ip(),
        user_agent=client_agent(),
    )
    db.session.add(entry)

    if commit:
        db.session.commit()

    return entry
