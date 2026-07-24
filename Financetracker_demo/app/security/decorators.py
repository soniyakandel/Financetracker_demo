from functools import wraps

from flask import abort, flash, redirect, request, url_for
from flask_login import current_user

from app.extensions import db
from app.models.audit import EVENT_ACCESS_DENIED
from app.security.audit import log_event


def get_owned_or_404(model, record_id):
    record = db.session.get(model, record_id)
    if record is None:
        abort(404)
    if getattr(record, "user_id", None) != current_user.id:
        log_event(
            EVENT_ACCESS_DENIED,
            detail=f"Tried to access {model.__name__} id={record_id} owned by another user",
            commit=True,
        )
        abort(404)
    return record


def fresh_login_required(view):

    @wraps(view)
    def wrapper(*args, **kwargs):
        from flask_login import login_fresh

        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.full_path))
        if not login_fresh():
            flash("Please sign in again to continue with this action.", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapper
