from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.features.auth import auth_bp
from app.features.auth.forms import LoginForm, OtpForm, RegisterForm
from app.features.auth.otp import send_login_code
from app.models.audit import (
    EVENT_LOGIN_FAILED,
    EVENT_LOGIN_LOCKED,
    EVENT_LOGIN_SUCCESS,
    EVENT_LOGOUT,
    EVENT_OTP_FAILED,
    EVENT_OTP_VERIFIED,
    EVENT_REGISTER,
)
from app.models.base import utcnow
from app.models.category import Category
from app.models.security import LoginAttempt, OtpCode
from app.models.session import UserSession
from app.models.user import User
from app.security.audit import client_agent, client_ip, log_event
from app.security.policy import RULES

PENDING_USER_KEY = "pending_user_id"
PENDING_REMEMBER_KEY = "pending_remember"
PENDING_NEXT_KEY = "pending_next"

SESSION_TOKEN_KEY = "session_token"

LOCKED_MESSAGE = (
    "This account is temporarily locked after too many failed sign-in "
    "attempts. Please try again in about {minutes} minutes."
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
def register():
    if current_user.is_authenticated:
        return redirect(url_for("core.landing"))

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
def login():
    if current_user.is_authenticated:
        return redirect(url_for("core.landing"))

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

        _, demo_code = send_login_code(user)
        if demo_code:
            flash(f"Development mode - your verification code is {demo_code}", "info")

        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/login.html", form=form)


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

    flash(f"Welcome back, {user.name}.", "success")
    target = url_for("core.landing")
    return redirect(target)


def _pending_user():
    user_id = session.get(PENDING_USER_KEY)
    if not user_id:
        return None
    return db.session.get(User, user_id)


@auth_bp.route("/verify", methods=["GET", "POST"])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for("core.landing"))

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
def resend_otp():
    user = _pending_user()
    if user is None:
        flash("Please sign in with your password first.", "warning")
        return redirect(url_for("auth.login"))

    _, demo_code = send_login_code(user)
    if demo_code:
        flash(f"Development mode - your new verification code is {demo_code}", "info")
    else:
        flash("A new code is on its way.", "success")

    return redirect(url_for("auth.verify_otp"))


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
