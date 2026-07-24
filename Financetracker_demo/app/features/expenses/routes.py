from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.features.expenses import expenses_bp
from app.features.expenses.filters import build_query, read_filters, summarise
from app.features.expenses.forms import TransactionForm
from app.models.category import Category
from app.models.transaction import EXPENSE, INCOME, Transaction
from app.security.decorators import get_owned_or_404


def _user_categories():
    return (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.is_default.desc(), Category.name)
        .all()
    )


@expenses_bp.route("/")
@login_required
def index():
    filters = read_filters(request.args)
    query = build_query(filters)

    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["ITEMS_PER_PAGE"]
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "expenses/index.html",
        transactions=pagination.items,
        pagination=pagination,
        filters=filters,
        totals=summarise(filters),
        categories=_user_categories(),
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

        word = "Expense" if transaction.type == EXPENSE else "Income"
        flash(f"{word} of {transaction.amount} saved.", "success")
        return redirect(url_for("expenses.index"))

    return render_template("expenses/form.html", form=form, transaction=None)


@expenses_bp.route("/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit(transaction_id):
    transaction = get_owned_or_404(Transaction, transaction_id)

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
    transaction = get_owned_or_404(Transaction, transaction_id)

    db.session.delete(transaction)
    db.session.commit()

    flash("Transaction deleted.", "success")
    return redirect(url_for("expenses.index"))
