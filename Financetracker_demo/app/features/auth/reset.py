from collections import namedtuple

from flask import current_app, url_for

from app.extensions import db
from app.mailer import render_email, send_email
from app.models.audit import EVENT_PASSWORD_RESET_REQUESTED
from app.models.security import PasswordResetToken
from app.security.audit import client_ip, log_event

RESET_SUBJECT = "Reset your Finance Tracker password"
CHANGED_SUBJECT = "Your Finance Tracker password was reset"

ResetDelivery = namedtuple("ResetDelivery", "record demo_link delivered")


def send_reset_link(user):
    PasswordResetToken.invalidate_all_for(user)

    record, plain_token = PasswordResetToken.issue(user, ip_address=client_ip())
    log_event(
        EVENT_PASSWORD_RESET_REQUESTED,
        detail="Reset link issued",
        user=user,
    )
    db.session.commit()

    reset_url = url_for("auth.reset_password", token=plain_token, _external=True)
    minutes = current_app.config["PASSWORD_RESET_VALID_MINUTES"]

    text_body, html_body = render_email(
        "password_reset", user=user, reset_url=reset_url, minutes=minutes
    )
    delivered = send_email(RESET_SUBJECT, user.email, text_body, html_body)

    if not delivered:
        current_app.logger.info("Password reset link for %s: %s", user.email, reset_url)

    demo_link = reset_url if current_app.config.get("RESET_SHOW_IN_BROWSER") else None
    return ResetDelivery(record, demo_link, delivered)


def send_password_changed_notice(user):
    text_body, html_body = render_email("password_changed", user=user)
    return send_email(CHANGED_SUBJECT, user.email, text_body, html_body)
