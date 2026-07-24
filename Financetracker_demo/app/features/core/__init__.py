from flask import Blueprint

core_bp = Blueprint("core", __name__, template_folder="templates")

from app.features.core import routes
