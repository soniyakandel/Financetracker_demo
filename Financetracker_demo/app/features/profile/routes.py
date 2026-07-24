from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.features.auth.routes import SESSION_TOKEN_KEY
from app.features.profile import profile_bp
from app.features.profile.forms import ChangePasswordForm, ProfileForm
from app.models.audit import (
    EVENT_LOGIN_FAILED,
    EVENT_OTP_FAILED,
    EVENT_PASSWORD_CHANGED,
    EVENT_PROFILE_UPDATED,
    EVENT_SESSION_REVOKED,
)
from app.models.audit import AuditLog
from app.models.session import UserSession
from app.models.user import User
from app.security.audit import log_event
from app.security.decorators import get_owned_or_404
from app.security.policy import RULES


@profile_bp.route("/")
@login_required
def index():
    return render_template("profile/index.html")


@profile_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        taken = User.query.filter(
            User.email == email, User.id != current_user.id
        ).first()
        if taken:
            flash("That email address cannot be used.", "warning")
            return render_template("profile/edit.html", form=form)

        changed = []
        if current_user.name != form.name.data.strip():
            changed.append("name")
        if current_user.email != email:
            changed.append("email")

        current_user.name = form.name.data.strip()
        current_user.email = email
        log_event(EVENT_PROFILE_UPDATED, detail=f"Changed: {', '.join(changed) or 'nothing'}")
        db.session.commit()

        flash("Your profile has been updated.", "success")
        return redirect(url_for("profile.index"))

    return render_template("profile/edit.html", form=form)


@profile_bp.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            log_event(EVENT_LOGIN_FAILED, detail="Wrong current password on change", commit=True)
            flash("Your current password is not correct.", "danger")
            return render_template(
                "profile/password.html", form=form, password_rules=RULES
            )

        if form.current_password.data == form.new_password.data:
            flash("The new password must be different from the old one.", "warning")
            return render_template(
                "profile/password.html", form=form, password_rules=RULES
            )

        current_user.set_password(form.new_password.data)

        keep = session.get(SESSION_TOKEN_KEY)
        others = UserSession.query.filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active.is_(True),
            UserSession.session_token != keep,
        ).all()
        for record in others:
            record.revoke(reason="password_changed")

        log_event(
            EVENT_PASSWORD_CHANGED,
            detail=f"Password changed; {len(others)} other session(s) ended",
        )
        db.session.commit()

        flash(
            "Your password has been changed"
            + (f" and {len(others)} other device(s) were signed out." if others else "."),
            "success",
        )
        return redirect(url_for("profile.index"))

    return render_template("profile/password.html", form=form, password_rules=RULES)


@profile_bp.route("/sessions")
@login_required
def sessions():
    current_token = session.get(SESSION_TOKEN_KEY)

    records = (
        UserSession.query.filter_by(user_id=current_user.id)
        .order_by(UserSession.is_active.desc(), UserSession.last_seen_at.desc())
        .limit(20)
        .all()
    )
    live = [r for r in records if r.is_valid]
    ended = [r for r in records if not r.is_valid]

    return render_template(
        "profile/sessions.html",
        live_sessions=live,
        ended_sessions=ended,
        current_token=current_token,
    )


@profile_bp.route("/sessions/<int:session_id>/revoke", methods=["POST"])
@login_required
def revoke_session(session_id):
    record = get_owned_or_404(UserSession, session_id)

    if record.session_token == session.get(SESSION_TOKEN_KEY):
        flash("To end this session, use Sign out instead.", "warning")
        return redirect(url_for("profile.sessions"))

    record.revoke(reason="revoked_by_user")
    log_event(EVENT_SESSION_REVOKED, detail=f"Revoked {record.device_label}")
    db.session.commit()

    flash("That device has been signed out.", "success")
    return redirect(url_for("profile.sessions"))


@profile_bp.route("/sessions/revoke-others", methods=["POST"])
@login_required
def revoke_other_sessions():
    keep = session.get(SESSION_TOKEN_KEY)

    others = UserSession.query.filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active.is_(True),
        UserSession.session_token != keep,
    ).all()
    for record in others:
        record.revoke(reason="revoked_by_user")

    log_event(EVENT_SESSION_REVOKED, detail=f"Revoked {len(others)} other session(s)")
    db.session.commit()

    if others:
        flash(f"{len(others)} other device(s) were signed out.", "success")
    else:
        flash("There were no other devices signed in.", "info")

    return redirect(url_for("profile.sessions"))


@profile_bp.route("/activity")
@login_required
def activity():
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["ITEMS_PER_PAGE"] * 2

    pagination = (
        AuditLog.query.filter_by(user_id=current_user.id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    failed_recently = AuditLog.query.filter(
        AuditLog.user_id == current_user.id,
        AuditLog.event.in_([EVENT_LOGIN_FAILED, EVENT_OTP_FAILED]),
    ).count()

    return render_template(
        "profile/activity.html",
        pagination=pagination,
        entries=pagination.items,
        failed_recently=failed_recently,
    )
