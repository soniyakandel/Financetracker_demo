from datetime import datetime

from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.features.expenses import expenses_bp
from app.models import Expense

CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Other"]


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
    if request.method == "POST":
        expense = Expense(
            user_id=current_user.id,
            title=request.form["title"],
            amount=float(request.form["amount"]),
            date=datetime.strptime(request.form["date"], "%Y-%m-%d").date(),
            category=request.form["category"],
        )
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for("expenses.index"))
    return render_template("expenses/form.html", expense=None, categories=CATEGORIES)


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if request.method == "POST":
        expense.title = request.form["title"]
        expense.amount = float(request.form["amount"])
        expense.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        expense.category = request.form["category"]
        db.session.commit()
        return redirect(url_for("expenses.index"))
    return render_template(
        "expenses/form.html", expense=expense, categories=CATEGORIES
    )


@expenses_bp.route("/<int:expense_id>/delete")
@login_required
def delete(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for("expenses.index"))
