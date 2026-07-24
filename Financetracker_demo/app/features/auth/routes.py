from flask import flash, redirect, render_template, url_for
from flask_login import login_required, login_user, logout_user

from app.extensions import db
from app.features.auth import auth_bp
from app.features.auth.forms import LoginForm, RegisterForm
from app.models.audit import (
    EVENT_LOGIN_FAILED,
    EVENT_LOGIN_SUCCESS,
    EVENT_LOGOUT,
    EVENT_REGISTER,
)
from app.models.category import Category
from app.models.security import LoginAttempt
from app.models.user import User
from app.security.audit import client_ip, log_event


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter_by(email=email).first():
            flash("That email is already registered.", "danger")
            return render_template("auth/register.html", form=form)

        user = User(name=form.name.data.strip(), email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        Category.create_defaults_for(user)
        log_event(EVENT_REGISTER, user=user)
        db.session.commit()

        flash("Account created, you can sign in now.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        password_ok = bool(user and user.check_password(form.password.data))

        LoginAttempt.record(email, client_ip(), password_ok)

        if password_ok:
            login_user(user, remember=bool(form.remember_me.data))
            log_event(EVENT_LOGIN_SUCCESS, user=user, commit=True)
            return redirect(url_for("dashboard.index"))

        log_event(EVENT_LOGIN_FAILED, detail=email, commit=True)
        flash("Email or password is not correct.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_event(EVENT_LOGOUT, commit=True)
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
