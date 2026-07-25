from flask import current_app, jsonify, request

from app.extensions import db, limiter
from app.features.api import api_bp
from app.models.audit import EVENT_LOGIN_FAILED, EVENT_LOGIN_LOCKED, EVENT_LOGIN_SUCCESS
from app.models.security import LoginAttempt
from app.models.transaction import EXPENSE, INCOME, Transaction
from app.models.user import User
from app.security.audit import client_ip, log_event
from app.security.jwt_tokens import create_access_token, current_api_user, token_required
from app.security.ratelimit import LOGIN_LIMIT


@api_bp.route("/login", methods=["POST"])
@limiter.limit(LOGIN_LIMIT)
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").lower().strip()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    if user and user.is_currently_locked:
        LoginAttempt.record(email, client_ip(), False)
        log_event(EVENT_LOGIN_LOCKED, detail=email, user=user, commit=True)
        return jsonify(error="account_locked"), 423

    password_ok = bool(user and user.check_password(password))
    LoginAttempt.record(email, client_ip(), password_ok)

    if not password_ok:
        if user is not None:
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= current_app.config["MAX_LOGIN_ATTEMPTS"]:
                user.lock()
        log_event(EVENT_LOGIN_FAILED, detail=email, commit=True)
        return jsonify(error="invalid_credentials"), 401

    user.unlock()
    log_event(EVENT_LOGIN_SUCCESS, user=user, commit=True)
    db.session.commit()

    return jsonify(
        access_token=create_access_token(user),
        token_type="Bearer",
        expires_in=current_app.config["JWT_ACCESS_MINUTES"] * 60,
    )


@api_bp.route("/me")
@token_required
def me():
    user = current_api_user()
    return jsonify(id=user.id, name=user.name, email=user.email)


@api_bp.route("/transactions")
@token_required
def transactions():
    user = current_api_user()
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["ITEMS_PER_PAGE"]

    pagination = (
        Transaction.query.filter_by(user_id=user.id)
        .order_by(Transaction.spent_on.desc(), Transaction.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify(
        page=pagination.page,
        pages=pagination.pages,
        total=pagination.total,
        items=[
            {
                "id": t.id,
                "type": t.type,
                "amount": str(t.amount),
                "category": t.category.name if t.category else None,
                "note": t.note,
                "spent_on": t.spent_on.isoformat(),
            }
            for t in pagination.items
        ],
    )


@api_bp.route("/summary")
@token_required
def summary():
    user = current_api_user()
    rows = (
        db.session.query(Transaction.type, db.func.sum(Transaction.amount))
        .filter(Transaction.user_id == user.id)
        .group_by(Transaction.type)
        .all()
    )
    totals = {kind: amount or 0 for kind, amount in rows}
    income = totals.get(INCOME, 0)
    expense = totals.get(EXPENSE, 0)

    return jsonify(
        income=str(income), expense=str(expense), balance=str(income - expense)
    )
