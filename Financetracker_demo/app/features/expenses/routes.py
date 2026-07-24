from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.features.expenses import expenses_bp
from app.features.expenses.forms import TransactionForm
from app.models.category import Category
from app.models.transaction import EXPENSE, INCOME, Transaction


def _user_categories():
    return (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.is_default.desc(), Category.name)
        .all()
    )


@expenses_bp.route("/")
@login_required
def index():
    transactions = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.spent_on.desc(), Transaction.id.desc())
        .all()
    )
    spent = sum(t.amount for t in transactions if t.type == EXPENSE)
    earned = sum(t.amount for t in transactions if t.type == INCOME)
    return render_template(
        "expenses/index.html",
        transactions=transactions,
        spent=spent,
        earned=earned,
    )


@expenses_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = TransactionForm()
    form.set_category_choices(_user_categories())

    if request.method == "GET" and request.args.get("type") == INCOME:
        form.type.data = INCOME

    if form.validate_on_submit():
        transaction = Transaction(
            user_id=current_user.id,
            type=form.type.data,
            amount=form.amount.data,
            category_id=form.category_id.data or None,
            spent_on=form.spent_on.data,
            note=(form.note.data or "").strip() or None,
        )
        db.session.add(transaction)
        db.session.commit()
        flash("Transaction saved.", "success")
        return redirect(url_for("expenses.index"))

    return render_template("expenses/form.html", form=form, transaction=None)


@expenses_bp.route("/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    form = TransactionForm(obj=transaction)
    form.set_category_choices(_user_categories())

    if request.method == "GET":
        form.category_id.data = transaction.category_id or 0

    if form.validate_on_submit():
        transaction.type = form.type.data
        transaction.amount = form.amount.data
        transaction.category_id = form.category_id.data or None
        transaction.spent_on = form.spent_on.data
        transaction.note = (form.note.data or "").strip() or None
        db.session.commit()
        flash("Transaction updated.", "success")
        return redirect(url_for("expenses.index"))

    return render_template("expenses/form.html", form=form, transaction=transaction)


@expenses_bp.route("/<int:transaction_id>/delete", methods=["POST"])
@login_required
def delete(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    db.session.delete(transaction)
    db.session.commit()
    flash("Transaction deleted.", "success")
    return redirect(url_for("expenses.index"))
