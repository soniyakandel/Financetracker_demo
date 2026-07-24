from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.features.expenses import expenses_bp
from app.features.expenses.forms import ExpenseForm
from app.models import Expense

CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Other"]


def _category_choices():
    return [(name, name) for name in CATEGORIES]


@expenses_bp.route("/")
@login_required
def index():
    expenses = (
        Expense.query.filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc())
        .all()
    )
    total = sum(expense.amount for expense in expenses)
    return render_template("expenses/index.html", expenses=expenses, total=total)


@expenses_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ExpenseForm()
    form.category.choices = _category_choices()
    if form.validate_on_submit():
        expense = Expense(
            user_id=current_user.id,
            title=form.title.data.strip(),
            amount=float(form.amount.data),
            date=form.date.data,
            category=form.category.data,
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense saved.", "success")
        return redirect(url_for("expenses.index"))
    return render_template("expenses/form.html", form=form, expense=None)


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    form = ExpenseForm(obj=expense)
    form.category.choices = _category_choices()
    if form.validate_on_submit():
        expense.title = form.title.data.strip()
        expense.amount = float(form.amount.data)
        expense.date = form.date.data
        expense.category = form.category.data
        db.session.commit()
        flash("Expense updated.", "success")
        return redirect(url_for("expenses.index"))
    return render_template("expenses/form.html", form=form, expense=expense)


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("expenses.index"))
