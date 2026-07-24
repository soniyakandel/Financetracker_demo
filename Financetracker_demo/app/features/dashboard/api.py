from flask import jsonify
from flask_login import login_required

from app.features.dashboard import dashboard_bp
from app.features.dashboard.stats import category_breakdown, monthly_trend


@dashboard_bp.route("/api/category-breakdown")
@login_required
def api_category_breakdown():
    rows = category_breakdown()
    return jsonify(
        {
            "labels": [row["name"] for row in rows],
            "colours": [row["colour"] for row in rows],
            "values": [float(row["amount"]) for row in rows],
            "total": float(sum(row["amount"] for row in rows)),
        }
    )


@dashboard_bp.route("/api/monthly-trend")
@login_required
def api_monthly_trend():
    series = monthly_trend()
    return jsonify(
        {
            "labels": [point["label"] for point in series],
            "income": [float(point["income"]) for point in series],
            "expense": [float(point["expense"]) for point in series],
        }
    )
