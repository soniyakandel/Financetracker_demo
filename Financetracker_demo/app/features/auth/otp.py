import os
from collections import namedtuple
from datetime import datetime

from flask import current_app

from app.extensions import db
from app.mailer import render_email, send_email
from app.models.audit import EVENT_OTP_ISSUED
from app.models.security import OtpCode
from app.security.audit import log_event

LOG_DIRECTORY = "logs"
LOG_FILENAME = "otp.log"

SUBJECT = "Your Finance Tracker verification code"

OtpDelivery = namedtuple("OtpDelivery", "record demo_code delivered")


def _write_to_log_file(user, code):
    folder = os.path.join(current_app.root_path, "..", LOG_DIRECTORY)
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] to={user.email} code={code}\n"
    with open(os.path.join(folder, LOG_FILENAME), "a", encoding="utf-8") as handle:
        handle.write(line)


def send_login_code(user):
    OtpCode.invalidate_all_for(user)

    record, plain_code = OtpCode.issue(user, purpose="login")
    log_event(EVENT_OTP_ISSUED, detail="Login verification code sent", user=user)
    db.session.commit()

    minutes = current_app.config["OTP_VALID_MINUTES"]
    text_body, html_body = render_email(
        "otp_code",
        user=user,
        code=plain_code,
        minutes=minutes,
        max_attempts=current_app.config["OTP_MAX_ATTEMPTS"],
    )
    delivered = send_email(SUBJECT, user.email, text_body, html_body)

    if not delivered:
        current_app.logger.info(
            "Verification code for %s is %s (valid %s minutes)",
            user.email,
            plain_code,
            minutes,
        )
        _write_to_log_file(user, plain_code)

    demo_code = plain_code if current_app.config.get("OTP_SHOW_IN_BROWSER") else None
    return OtpDelivery(record, demo_code, delivered)
