from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

from app.features.api import routes
