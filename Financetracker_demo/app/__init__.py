import os

from flask import Flask

from app.config import Config
from app.commands import register_commands
from app.filters import register_filters
from app.extensions import csrf, db, login_manager
from app.security.session_guard import register_session_guard


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models

    register_session_guard(app)

    register_filters(app)

    from app.features.core import core_bp
    from app.features.auth import auth_bp
    from app.features.dashboard import dashboard_bp
    from app.features.expenses import expenses_bp
    from app.features.categories import categories_bp
    from app.features.budgets import budgets_bp
    from app.features.goals import goals_bp
    from app.features.recurring import recurring_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(recurring_bp)

    register_commands(app)

    return app
