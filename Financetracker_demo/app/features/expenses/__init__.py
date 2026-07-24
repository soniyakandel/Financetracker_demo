from flask import Blueprint

expenses_bp = Blueprint(
    "expenses", __name__, url_prefix="/expenses", template_folder="templates"
)

from app.features.expenses import routes
