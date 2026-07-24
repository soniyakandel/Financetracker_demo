from datetime import date, datetime
from decimal import Decimal

from flask import current_app


def money(value, with_symbol=True):
    try:
        amount = Decimal(value or 0)
    except (TypeError, ValueError):
        amount = Decimal(0)

    text = f"{amount:,.2f}"
    if with_symbol:
        return f"{current_app.config['CURRENCY_SYMBOL']} {text}"
    return text


def short_date(value):
    if not value:
        return "-"
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d %b %Y")


def date_time(value):
    if not value:
        return "-"
    return value.strftime("%d %b %Y, %H:%M")


def month_name(month_key):
    try:
        year, month = month_key.split("-")
        return date(int(year), int(month), 1).strftime("%B %Y")
    except (ValueError, AttributeError):
        return month_key


def time_ago(value):
    if not value:
        return "-"
    seconds = (datetime.utcnow() - value).total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)} min ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)} hours ago"
    return f"{int(seconds // 86400)} days ago"


def register_filters(app):
    app.jinja_env.filters["money"] = money
    app.jinja_env.filters["short_date"] = short_date
    app.jinja_env.filters["date_time"] = date_time
    app.jinja_env.filters["month_name"] = month_name
    app.jinja_env.filters["time_ago"] = time_ago
