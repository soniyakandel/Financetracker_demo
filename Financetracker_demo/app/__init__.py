import os

from dotenv import load_dotenv
from flask import Flask

from app.commands import register_commands
from app.config import get_config
from app.filters import register_filters
from app.extensions import csrf, db, limiter, login_manager
from app.security.csrf import register_csrf_handlers
from app.security.errors import register_error_handlers
from app.security.headers import register_security_headers
from app.security.ratelimit import register_ratelimit_handlers
from app.security.session_guard import register_session_guard

load_dotenv()


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config(config_name))

    os.makedirs(app.instance_path, exist_ok=True)

    _init_extensions(app)

    from app import models

    register_security_headers(app)
    register_csrf_handlers(app)
    register_ratelimit_handlers(app)
    register_error_handlers(app)
    register_session_guard(app)
    register_filters(app)
    _register_blueprints(app)
    register_commands(app)

    return app


def _init_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)


def _register_blueprints(app):
    from app.features.auth import auth_bp
    from app.features.budgets import budgets_bp
    from app.features.categories import categories_bp
    from app.features.core import core_bp
    from app.features.dashboard import dashboard_bp
    from app.features.expenses import expenses_bp
    from app.features.goals import goals_bp
    from app.features.profile import profile_bp
    from app.features.recurring import recurring_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(profile_bp)
