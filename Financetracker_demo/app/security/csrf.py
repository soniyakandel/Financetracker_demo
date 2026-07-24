from flask import flash, redirect, request, url_for
from flask_wtf.csrf import CSRFError

from app.models.audit import EVENT_ACCESS_DENIED
from app.security.audit import log_event
from app.security.urls import safe_redirect_target


def register_csrf_handlers(app):
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        log_event(
            EVENT_ACCESS_DENIED,
            detail=f"CSRF check failed on {request.path}: {error.description}",
            commit=True,
        )
        flash(
            "That request could not be verified, so it was blocked. "
            "Please reload the page and try again.",
            "danger",
        )
        fallback = url_for("core.landing")
        return redirect(safe_redirect_target(request.referrer, fallback)), 302
