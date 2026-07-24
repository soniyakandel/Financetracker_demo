from flask import Blueprint

goals_bp = Blueprint(
    "goals", __name__, url_prefix="/goals", template_folder="templates"
)

from app.features.goals import routes
