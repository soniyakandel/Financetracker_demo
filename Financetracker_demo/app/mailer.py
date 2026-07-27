import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from flask import current_app, render_template

OUTBOX_KEY = "mail_outbox"


def is_configured():
    config = current_app.config
    return bool(config.get("MAIL_ENABLED")) and bool(config.get("MAIL_SERVER"))


def outbox():
    return current_app.extensions.setdefault(OUTBOX_KEY, [])


def render_email(template_name, **context):
    text = render_template(f"emails/{template_name}.txt", **context)
    html = render_template(f"emails/{template_name}.html", **context)
    return text, html


def send_email(subject, recipient, text_body, html_body=None):
    message = _build_message(subject, recipient, text_body, html_body)

    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        outbox().append(message)
        return True

    if not is_configured():
        current_app.logger.warning(
            "No mail server configured - %r was not emailed to %s",
            subject,
            recipient,
        )
        return False

    try:
        _deliver(message)
    except (smtplib.SMTPException, ssl.SSLError, OSError) as error:
        current_app.logger.error("Email to %s failed: %s", recipient, error)
        return False

    current_app.logger.info("Email sent to %s (%s)", recipient, subject)
    return True


def _build_message(subject, recipient, text_body, html_body=None):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = current_app.config["MAIL_SENDER"]
    message["To"] = recipient
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    message["Auto-Submitted"] = "auto-generated"

    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    return message


def _deliver(message):
    config = current_app.config
    host = config["MAIL_SERVER"]
    port = config["MAIL_PORT"]
    timeout = config["MAIL_TIMEOUT"]
    username = config["MAIL_USERNAME"]

    context = ssl.create_default_context()

    if username and not (config["MAIL_USE_SSL"] or config["MAIL_USE_TLS"]):
        current_app.logger.warning(
            "MAIL_USERNAME is set but neither MAIL_USE_TLS nor MAIL_USE_SSL "
            "is on - the mail password would cross the network in the clear."
        )

    if config["MAIL_USE_SSL"]:
        server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=timeout)

    with server:
        server.ehlo()
        if not config["MAIL_USE_SSL"] and config["MAIL_USE_TLS"]:
            server.starttls(context=context)
            server.ehlo()
        if username:
            server.login(username, config["MAIL_PASSWORD"])
        server.send_message(message)
