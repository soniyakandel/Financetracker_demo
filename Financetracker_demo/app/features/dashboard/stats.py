from datetime import date
from decimal import Decimal

from flask_login import current_user
from sqlalchemy import func

from app.extensions import db
from app.models.budget import Budget
from app.models.category import Category
from app.models.goal import SavingsGoal
from app.models.transaction import EXPENSE, INCOME, Transaction


def month_key(value=None):
    return (value or date.today()).strftime("%Y-%m")


def previous_month_key(value=None):
    today = value or date.today()
    year, month = today.year, today.month - 1
    if month == 0:
        year, month = year - 1, 12
    return f"{year:04d}-{month:02d}"


def _totals_for_month(key):
    rows = (
        db.session.query(Transaction.type, func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == current_user.id,
            func.strftime("%Y-%m", Transaction.spent_on) == key,
        )
        .group_by(Transaction.type)
        .all()
    )
    totals = {INCOME: Decimal("0.00"), EXPENSE: Decimal("0.00")}
    for kind, amount in rows:
        totals[kind] = Decimal(amount or 0)
    return totals[INCOME], totals[EXPENSE]


def percent_change(now, before):
    if before == 0:
        return None
    return int(round((now - before) / before * 100))


def summary():
    this_key = month_key()
    last_key = previous_month_key()

    income, expense = _totals_for_month(this_key)
    last_income, last_expense = _totals_for_month(last_key)

    saved = sum(
        (goal.saved_amount for goal in SavingsGoal.query.filter_by(
            user_id=current_user.id).all()),
        Decimal("0.00"),
    )

    return {
        "month_label": date.today().strftime("%B %Y"),
        "income": income,
        "expense": expense,
        "balance": income - expense,
        "saved": saved,
        "income_change": percent_change(income, last_income),
        "expense_change": percent_change(expense, last_expense),
        "last_expense": last_expense,
    }


def category_breakdown(key=None):
    key = key or month_key()
    rows = (
        db.session.query(
            Category.name,
            Category.colour,
            Category.icon,
            func.sum(Transaction.amount),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == EXPENSE,
            func.strftime("%Y-%m", Transaction.spent_on) == key,
        )
        .group_by(Category.id)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    return [
        {"name": name, "colour": colour, "icon": icon, "amount": Decimal(total or 0)}
        for name, colour, icon, total in rows
    ]


def monthly_trend(months=6):
    today = date.today()
    keys = []
    year, month = today.year, today.month
    for _ in range(months):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    keys.reverse()

    series = []
    for key in keys:
        income, expense = _totals_for_month(key)
        year_text, month_text = key.split("-")
        series.append(
            {
                "key": key,
                "label": date(int(year_text), int(month_text), 1).strftime("%b"),
                "income": income,
                "expense": expense,
            }
        )
    return series


def budget_snapshot(limit=4):
    key = month_key()
    budgets = (
        Budget.query.filter_by(user_id=current_user.id, month=key).join(Category).all()
    )
    if not budgets:
        return []

    rows = (
        db.session.query(Transaction.category_id, func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == EXPENSE,
            func.strftime("%Y-%m", Transaction.spent_on) == key,
        )
        .group_by(Transaction.category_id)
        .all()
    )
    spent = {category_id: Decimal(total or 0) for category_id, total in rows}

    for budget in budgets:
        budget.spent = spent.get(budget.category_id, Decimal("0.00"))

    budgets.sort(key=lambda b: b.percent_used, reverse=True)
    return budgets[:limit]


def recent_transactions(limit=6):
    return (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.spent_on.desc(), Transaction.id.desc())
        .limit(limit)
        .all()
    )
