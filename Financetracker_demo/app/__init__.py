import os

from flask import Flask

from app.config import Config
from app.extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app import models

    from app.features.auth import auth_bp
    from app.features.core import core_bp
    from app.features.expenses import expenses_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)

    return app
