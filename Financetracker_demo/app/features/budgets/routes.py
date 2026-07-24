from datetime import date
from decimal import Decimal

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.features.budgets import budgets_bp
from app.features.budgets.forms import BudgetForm, month_choices
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import EXPENSE, Transaction
from app.security.decorators import get_owned_or_404


def _user_categories():
    return (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.is_default.desc(), Category.name)
        .all()
    )


def current_month_key():
    return date.today().strftime("%Y-%m")


def spend_for_month(month_key):
    rows = (
        db.session.query(Transaction.category_id, func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == EXPENSE,
            func.strftime("%Y-%m", Transaction.spent_on) == month_key,
        )
        .group_by(Transaction.category_id)
        .all()
    )
    return {category_id: Decimal(total or 0) for category_id, total in rows}


@budgets_bp.route("/")
@login_required
def index():
    months = month_choices()
    month_key = request.args.get("month", "")
    if month_key not in dict(months):
        month_key = current_month_key()

    budgets = (
        Budget.query.filter_by(user_id=current_user.id, month=month_key)
        .join(Category)
        .order_by(Category.name)
        .all()
    )

    spent = spend_for_month(month_key)
    for budget in budgets:
        budget.spent = spent.get(budget.category_id, Decimal("0.00"))

    return render_template(
        "budgets/index.html",
        budgets=budgets,
        month_key=month_key,
        months=months,
        total_limit=sum((Decimal(b.amount_limit) for b in budgets), Decimal("0.00")),
        total_spent=sum((Decimal(b.spent) for b in budgets), Decimal("0.00")),
    )


@budgets_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = BudgetForm()
    form.set_choices(_user_categories())

    if request.method == "GET":
        form.month.data = request.args.get("month") or current_month_key()

    if form.validate_on_submit():
        existing = Budget.query.filter_by(
            user_id=current_user.id,
            category_id=form.category_id.data,
            month=form.month.data,
        ).first()
        if existing:
            flash(
                "There is already a budget for that category and month. "
                "Edit it instead.",
                "warning",
            )
            return redirect(url_for("budgets.index", month=form.month.data))

        db.session.add(
            Budget(
                user_id=current_user.id,
                category_id=form.category_id.data,
                month=form.month.data,
                amount_limit=form.amount_limit.data,
            )
        )
        db.session.commit()

        flash("Budget saved.", "success")
        return redirect(url_for("budgets.index", month=form.month.data))

    return render_template("budgets/form.html", form=form, budget=None)


@budgets_bp.route("/<int:budget_id>/edit", methods=["GET", "POST"])
@login_required
def edit(budget_id):
    budget = get_owned_or_404(Budget, budget_id)

    form = BudgetForm(obj=budget)
    form.set_choices(_user_categories())

    if form.validate_on_submit():
        clash = Budget.query.filter(
            Budget.user_id == current_user.id,
            Budget.id != budget.id,
            Budget.category_id == form.category_id.data,
            Budget.month == form.month.data,
        ).first()
        if clash:
            flash("That category already has a budget for that month.", "warning")
            return render_template("budgets/form.html", form=form, budget=budget)

        budget.category_id = form.category_id.data
        budget.month = form.month.data
        budget.amount_limit = form.amount_limit.data
        db.session.commit()

        flash("Budget updated.", "success")
        return redirect(url_for("budgets.index", month=budget.month))

    return render_template("budgets/form.html", form=form, budget=budget)


@budgets_bp.route("/<int:budget_id>/delete", methods=["POST"])
@login_required
def delete(budget_id):
    budget = get_owned_or_404(Budget, budget_id)

    month = budget.month
    db.session.delete(budget)
    db.session.commit()

    flash("Budget removed.", "success")
    return redirect(url_for("budgets.index", month=month))
