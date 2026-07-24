from flask import Blueprint

core_bp = Blueprint("core", __name__)

from app.features.core import routes
