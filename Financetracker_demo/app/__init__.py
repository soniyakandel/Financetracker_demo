import logging
import os
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

from app.commands import register_commands
from app.config import get_config
from app.filters import register_filters
from app.extensions import csrf, db, limiter, login_manager
from app.security.csrf import register_csrf_handlers
from app.security.errors import register_error_handlers
from app.security.headers import register_security_headers
from app.security.ratelimit import register_ratelimit_handlers
from app.security.session_guard import register_session_guard


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config(config_name))

    os.makedirs(app.instance_path, exist_ok=True)

    _check_production_settings(app)
    _configure_logging(app)
    _apply_proxy_fix(app)

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


def _check_production_settings(app):
    if app.debug or app.testing:
        return

    if app.config["SECRET_KEY"] in ("", "dev-only-insecure-key"):
        raise RuntimeError(
            "SECRET_KEY is missing or still the development placeholder. "
            "Set a real one in .env before running in production, e.g.\n"
            '    python -c "import secrets; print(secrets.token_hex(32))"'
        )


def _configure_logging(app):
    if app.debug or app.testing:
        return

    log_dir = os.path.join(os.path.dirname(app.root_path), "logs")
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=1_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(file_handler)
        root.addHandler(console)

    app.logger.setLevel(logging.INFO)


def _apply_proxy_fix(app):
    hops = app.config.get("TRUSTED_PROXY_HOPS", 0)
    if hops > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops, x_prefix=hops
        )


def _init_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)


def _register_blueprints(app):
    from app.features.api import api_bp
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

    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)
