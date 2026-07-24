from flask import redirect, render_template, url_for
from flask_login import current_user

from app.features.core import core_bp


@core_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return render_template("core/landing.html")
