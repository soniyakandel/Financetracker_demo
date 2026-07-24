from flask import render_template
from flask_login import login_required

from app.features.dashboard import dashboard_bp
from app.features.dashboard.stats import (
    budget_snapshot,
    category_breakdown,
    recent_transactions,
    summary,
)


@dashboard_bp.route("/")
@login_required
def index():
    return render_template(
        "dashboard/index.html",
        stats=summary(),
        breakdown=category_breakdown(),
        budgets=budget_snapshot(),
        recent=recent_transactions(),
    )
