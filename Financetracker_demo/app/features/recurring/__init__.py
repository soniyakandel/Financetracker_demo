from flask import Blueprint

recurring_bp = Blueprint(
    "recurring", __name__, url_prefix="/recurring", template_folder="templates"
)

from app.features.recurring import routes
