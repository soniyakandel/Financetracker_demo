from datetime import date, datetime
from decimal import Decimal

from flask_login import current_user
from sqlalchemy import func

from app.extensions import db
from app.models.transaction import EXPENSE, INCOME, TRANSACTION_TYPES, Transaction

SORT_OPTIONS = {
    "newest": (Transaction.spent_on.desc(), Transaction.id.desc()),
    "oldest": (Transaction.spent_on.asc(), Transaction.id.asc()),
    "highest": (Transaction.amount.desc(), Transaction.id.desc()),
    "lowest": (Transaction.amount.asc(), Transaction.id.asc()),
}


def parse_date(text):
    if not text:
        return None
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def read_filters(args):
    category_id = args.get("category", type=int)
    kind = args.get("type", "").strip().lower()

    return {
        "start": parse_date(args.get("start")),
        "end": parse_date(args.get("end")),
        "category": category_id if category_id and category_id > 0 else None,
        "type": kind if kind in TRANSACTION_TYPES else None,
        "search": (args.get("search") or "").strip()[:50],
        "sort": args.get("sort") if args.get("sort") in SORT_OPTIONS else "newest",
    }


def build_query(filters):
    query = Transaction.query.filter_by(user_id=current_user.id)

    if filters["start"]:
        query = query.filter(Transaction.spent_on >= filters["start"])
    if filters["end"]:
        query = query.filter(Transaction.spent_on <= filters["end"])
    if filters["category"]:
        query = query.filter(Transaction.category_id == filters["category"])
    if filters["type"]:
        query = query.filter(Transaction.type == filters["type"])
    if filters["search"]:
        query = query.filter(Transaction.note.ilike(f"%{filters['search']}%"))

    return query.order_by(*SORT_OPTIONS[filters["sort"]])


def month_bounds(today=None):
    today = today or date.today()
    first = today.replace(day=1)
    return first, today


def summarise(filters):
    base = build_query(filters).order_by(None).subquery()
    rows = (
        db.session.query(base.c.type, func.sum(base.c.amount), func.count())
        .group_by(base.c.type)
        .all()
    )

    totals = {kind: Decimal("0.00") for kind in (INCOME, EXPENSE)}
    count = 0
    for kind, amount, rows_of_kind in rows:
        totals[kind] = Decimal(amount or 0)
        count += rows_of_kind

    totals["net"] = totals[INCOME] - totals[EXPENSE]
    totals["count"] = count
    return totals
