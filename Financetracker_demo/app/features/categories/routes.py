from decimal import Decimal

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.features.categories import categories_bp
from app.features.categories.forms import CategoryForm
from app.models.category import Category
from app.models.transaction import EXPENSE, Transaction
from app.security.decorators import get_owned_or_404


def _spend_by_category():
    rows = (
        db.session.query(Transaction.category_id, func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == EXPENSE,
        )
        .group_by(Transaction.category_id)
        .all()
    )
    return {category_id: Decimal(total or 0) for category_id, total in rows}


@categories_bp.route("/")
@login_required
def index():
    categories = (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.is_default.desc(), Category.name)
        .all()
    )
    totals = _spend_by_category()

    return render_template(
        "categories/index.html",
        categories=categories,
        totals=totals,
        grand_total=sum(totals.values(), Decimal("0.00")),
    )


@categories_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = CategoryForm()

    if form.validate_on_submit():
        name = form.name.data.strip()

        existing = Category.query.filter(
            Category.user_id == current_user.id,
            func.lower(Category.name) == name.lower(),
        ).first()
        if existing:
            flash(f'You already have a category called "{name}".', "warning")
            return render_template("categories/form.html", form=form, category=None)

        category = Category(
            user_id=current_user.id,
            name=name,
            icon=form.icon.data,
            colour=form.colour.data,
            is_default=False,
        )
        db.session.add(category)
        db.session.commit()

        flash(f'Category "{name}" added.', "success")
        return redirect(url_for("categories.index"))

    return render_template("categories/form.html", form=form, category=None)


@categories_bp.route("/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
def edit(category_id):
    category = get_owned_or_404(Category, category_id)
    form = CategoryForm(obj=category)

    if form.validate_on_submit():
        name = form.name.data.strip()

        clash = Category.query.filter(
            Category.user_id == current_user.id,
            Category.id != category.id,
            func.lower(Category.name) == name.lower(),
        ).first()
        if clash:
            flash(f'You already have a category called "{name}".', "warning")
            return render_template(
                "categories/form.html", form=form, category=category
            )

        category.name = name
        category.icon = form.icon.data
        category.colour = form.colour.data
        db.session.commit()

        flash("Category updated.", "success")
        return redirect(url_for("categories.index"))

    return render_template("categories/form.html", form=form, category=category)


@categories_bp.route("/<int:category_id>/delete", methods=["POST"])
@login_required
def delete(category_id):
    category = get_owned_or_404(Category, category_id)

    if category.is_default:
        flash("The standard categories cannot be deleted.", "warning")
        return redirect(url_for("categories.index"))

    in_use = Transaction.query.filter_by(
        user_id=current_user.id, category_id=category.id
    ).count()
    if in_use:
        flash(
            f'"{category.name}" is used by {in_use} transaction(s), so it cannot '
            "be deleted. You can rename it instead.",
            "warning",
        )
        return redirect(url_for("categories.index"))

    name = category.name
    db.session.delete(category)
    db.session.commit()

    flash(f'Category "{name}" deleted.', "success")
    return redirect(url_for("categories.index"))
