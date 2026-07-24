from flask import render_template
from flask_login import login_required

from app.features.dashboard import dashboard_bp
from app.features.dashboard.stats import summary


@dashboard_bp.route("/")
@login_required
def index():
    return render_template("dashboard/index.html", stats=summary())
