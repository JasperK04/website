"""
Portfolio Flask application — app factory.

Usage::

    from app import create_app
    app = create_app()          # production
    app = create_app('development')   # dev / debug
"""
from pathlib import Path

from flask import Flask

from .config import get_config
from .routes import main

_BASE_DIR = Path(__file__).parent.parent


def create_app(env: str | None = None) -> Flask:
    """
    Application factory.

    Creates and returns a configured Flask instance with the 'main'
    blueprint registered. Templates and static files are resolved
    relative to the project root, not the package directory.

    Args:
        env: Environment name ('development' or 'production').
             Falls back to the FLASK_ENV environment variable,
             then defaults to 'production'.
    """
    app = Flask(
        __name__,
        template_folder=str(_BASE_DIR / "templates"),
        static_folder=str(_BASE_DIR / "static"),
    )

    app.config.from_object(get_config(env))
    app.config["BASE_DIR"] = _BASE_DIR

    app.register_blueprint(main)

    return app
