from flask import Blueprint

budgets_bp = Blueprint(
    "budgets", __name__, url_prefix="/budgets", template_folder="templates"
)

from app.features.budgets import routes
