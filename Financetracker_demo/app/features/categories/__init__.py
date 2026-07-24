from flask import Blueprint

categories_bp = Blueprint(
    "categories", __name__, url_prefix="/categories", template_folder="templates"
)

from app.features.categories import routes
