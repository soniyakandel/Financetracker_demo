from decimal import Decimal

from flask import render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.features.categories import categories_bp
from app.models.category import Category
from app.models.transaction import EXPENSE, Transaction


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
