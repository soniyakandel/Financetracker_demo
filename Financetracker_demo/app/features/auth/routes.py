from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db, limiter
from app.features.auth import auth_bp
from app.features.auth.forms import (
    ForgotPasswordForm,
    LoginForm,
    OtpForm,
    RegisterForm,
    ResetPasswordForm,
)
from app.features.auth.otp import send_login_code
from app.features.auth.reset import send_password_changed_notice, send_reset_link
from app.features.recurring.generator import generate_due_for
from app.models.audit import (
    EVENT_LOGIN_FAILED,
    EVENT_LOGIN_LOCKED,
    EVENT_LOGIN_SUCCESS,
    EVENT_LOGOUT,
    EVENT_OTP_FAILED,
    EVENT_OTP_VERIFIED,
    EVENT_PASSWORD_RESET_COMPLETED,
    EVENT_PASSWORD_RESET_FAILED,
    EVENT_PASSWORD_RESET_REQUESTED,
    EVENT_REGISTER,
)
from app.models.base import utcnow
from app.models.category import Category
from app.models.security import LoginAttempt, OtpCode, PasswordResetToken
from app.models.session import UserSession
from app.models.user import User
from app.security.audit import client_agent, client_ip, log_event
from app.security.policy import RULES
from app.security.ratelimit import (
    LOGIN_LIMIT,
    OTP_RESEND_LIMIT,
    OTP_VERIFY_LIMIT,
    PASSWORD_RESET_REQUEST_LIMIT,
    PASSWORD_RESET_SUBMIT_LIMIT,
    REGISTER_LIMIT,
)
from app.security.urls import safe_redirect_target

PENDING_USER_KEY = "pending_user_id"
PENDING_REMEMBER_KEY = "pending_remember"
PENDING_NEXT_KEY = "pending_next"

SESSION_TOKEN_KEY = "session_token"

LOCKED_MESSAGE = (
    "This account is temporarily locked after too many failed sign-in "
    "attempts. Please try again in about {minutes} minutes."
)

RESET_SENT_MESSAGE = (
    "If that email address has an account with us, a reset link is on its way. "
    "The link is valid for {minutes} minutes."
)


def lockout_minutes():
    return current_app.config["LOCKOUT_MINUTES"]


def _handle_failed_password(user, email):
    LoginAttempt.record(email, client_ip(), success=False)

    if user is None:
        log_event(
            EVENT_LOGIN_FAILED,
            detail=f"Sign-in attempt for unknown address {email}",
            commit=True,
        )
        return

    user.failed_attempts = (user.failed_attempts or 0) + 1
    limit = current_app.config["MAX_LOGIN_ATTEMPTS"]

    if user.failed_attempts >= limit:
        user.lock()
        log_event(
            EVENT_LOGIN_LOCKED,
            detail=f"Locked after {user.failed_attempts} failed attempts",
            user=user,
        )
    else:
        log_event(
            EVENT_LOGIN_FAILED,
            detail=f"Wrong password ({user.failed_attempts} of {limit})",
            user=user,
        )

    db.session.commit()


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit(REGISTER_LIMIT, methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        if User.query.filter_by(email=email).first():
            flash(
                "We could not create that account. If you already have one, "
                "please sign in instead.",
                "warning",
            )
            return render_template(
                "auth/register.html", form=form, password_rules=RULES
            )

        user = User(name=form.name.data.strip(), email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        Category.create_defaults_for(user)
        log_event(EVENT_REGISTER, detail=f"New account for {email}", user=user)
        db.session.commit()

        flash("Your account is ready. Please sign in to continue.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form, password_rules=RULES)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(LOGIN_LIMIT, methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user is not None and user.is_currently_locked:
            LoginAttempt.record(email, client_ip(), success=False)
            log_event(
                EVENT_LOGIN_LOCKED,
                detail="Sign-in attempt while the account was locked",
                user=user,
                commit=True,
            )
            flash(LOCKED_MESSAGE.format(minutes=lockout_minutes()), "danger")
            return render_template("auth/login.html", form=form)

        if user is None or not user.check_password(form.password.data):
            _handle_failed_password(user, email)
            flash("Email or password is incorrect.", "danger")
            return render_template("auth/login.html", form=form)

        user.failed_attempts = 0
        user.unlock()
        LoginAttempt.record(email, client_ip(), success=True)

        session.clear()
        session[PENDING_USER_KEY] = user.id
        session[PENDING_REMEMBER_KEY] = bool(form.remember_me.data)
        session[PENDING_NEXT_KEY] = request.args.get("next", "")
        db.session.commit()

        _flash_code_delivery(send_login_code(user), user)
        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/login.html", form=form)


def _flash_code_delivery(delivery, user, resend=False):
    if delivery.demo_code:
        which = "new verification code" if resend else "verification code"
        flash(f"Development mode - your {which} is {delivery.demo_code}", "info")
    elif delivery.delivered:
        flash(f"We emailed a six digit code to {user.email}.", "info")
    else:
        flash(
            "We could not email your code just now. Please ask for a new one "
            "in a moment.",
            "warning",
        )


def _complete_login(user):
    remember = bool(session.get(PENDING_REMEMBER_KEY))
    next_page = session.get(PENDING_NEXT_KEY) or ""

    session.clear()

    record = UserSession.start(user, client_ip(), client_agent())
    db.session.flush()

    login_user(user, remember=remember)
    session[SESSION_TOKEN_KEY] = record.session_token
    session.permanent = True

    user.last_login_at = utcnow()
    log_event(EVENT_LOGIN_SUCCESS, detail=record.device_label, user=user)
    db.session.commit()

    created = generate_due_for(user)
    if created:
        flash(
            f"{created} recurring expense(s) were added to your history.",
            "info",
        )

    flash(f"Welcome back, {user.name}.", "success")
    target = safe_redirect_target(next_page, url_for("dashboard.index"))
    return redirect(target)


def _pending_user():
    user_id = session.get(PENDING_USER_KEY)
    if not user_id:
        return None
    return db.session.get(User, user_id)


@auth_bp.route("/verify", methods=["GET", "POST"])
@limiter.limit(OTP_VERIFY_LIMIT, methods=["POST"])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    user = _pending_user()
    if user is None:
        flash("Please sign in with your password first.", "warning")
        return redirect(url_for("auth.login"))

    form = OtpForm()

    if form.validate_on_submit():
        record = (
            OtpCode.query.filter_by(user_id=user.id, purpose="login", used=False)
            .order_by(OtpCode.created_at.desc())
            .first()
        )

        if record is None or not record.verify(form.code.data):
            log_event(EVENT_OTP_FAILED, detail="Wrong or expired code", user=user)
            db.session.commit()
            flash("That code is not correct, or it has expired.", "danger")
            return render_template("auth/verify_otp.html", form=form, user=user)

        log_event(EVENT_OTP_VERIFIED, detail="Verification code accepted", user=user)
        db.session.commit()
        return _complete_login(user)

    return render_template("auth/verify_otp.html", form=form, user=user)


@auth_bp.route("/verify/resend", methods=["POST"])
@limiter.limit(OTP_RESEND_LIMIT)
def resend_otp():
    user = _pending_user()
    if user is None:
        flash("Please sign in with your password first.", "warning")
        return redirect(url_for("auth.login"))

    _flash_code_delivery(send_login_code(user), user, resend=True)
    return redirect(url_for("auth.verify_otp"))


@auth_bp.route("/forgot", methods=["GET", "POST"])
@limiter.limit(PASSWORD_RESET_REQUEST_LIMIT, methods=["POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("profile.change_password"))

    form = ForgotPasswordForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        delivery = None
        if user is not None:
            delivery = send_reset_link(user)
        else:
            log_event(
                EVENT_PASSWORD_RESET_REQUESTED,
                detail=f"Reset requested for unknown address {email}",
                commit=True,
            )

        if delivery is not None and delivery.demo_link:
            flash(f"Development mode - your reset link is {delivery.demo_link}", "info")

        flash(
            RESET_SENT_MESSAGE.format(
                minutes=current_app.config["PASSWORD_RESET_VALID_MINUTES"]
            ),
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
@limiter.limit(PASSWORD_RESET_SUBMIT_LIMIT)
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("profile.change_password"))

    record = PasswordResetToken.lookup(token)
    if record is None:
        log_event(
            EVENT_PASSWORD_RESET_FAILED,
            detail="Reset link was unknown, already used or expired",
            commit=True,
        )
        flash(
            "That reset link is no longer valid. Links can only be used once "
            "and they expire - please request a new one.",
            "danger",
        )
        return redirect(url_for("auth.forgot_password"))

    user = record.user
    form = ResetPasswordForm()

    if form.validate_on_submit():
        if user.check_password(form.password.data):
            flash("Please choose a password you have not used before.", "warning")
            return render_template(
                "auth/reset_password.html", form=form, token=token, password_rules=RULES
            )

        user.set_password(form.password.data)

        record.consume()
        PasswordResetToken.invalidate_all_for(user)

        user.unlock()

        OtpCode.invalidate_all_for(user)

        active = UserSession.query.filter(
            UserSession.user_id == user.id,
            UserSession.is_active.is_(True),
        ).all()
        for existing in active:
            existing.revoke(reason="password_reset")

        log_event(
            EVENT_PASSWORD_RESET_COMPLETED,
            detail=f"Password reset from a link; {len(active)} session(s) ended",
            user=user,
        )
        db.session.commit()

        send_password_changed_notice(user)

        session.clear()

        flash(
            "Your password has been reset and every signed-in device was "
            "signed out. Please sign in with your new password.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/reset_password.html", form=form, token=token, password_rules=RULES
    )


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    token = session.get(SESSION_TOKEN_KEY)
    if token:
        record = UserSession.query.filter_by(session_token=token).first()
        if record and record.user_id == current_user.id:
            record.revoke(reason="logout")

    log_event(EVENT_LOGOUT, detail="Signed out")
    db.session.commit()

    logout_user()
    session.clear()

    flash("You have been signed out.", "success")
    return redirect(url_for("core.landing"))
