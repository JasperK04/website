"""
Configuration classes for the portfolio Flask app.
"""

import os
from pathlib import Path

import dotenv

dotenv.load_dotenv()

BASE_DIR = Path(__file__).parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("Missing required environment variable: SECRET_KEY")
    DATA_DIR = BASE_DIR / "data"
    CODE_DIR = BASE_DIR / "static" / "projects"
    SITE_URL = os.environ.get("SITE_URL")
    if not SITE_URL:
        raise RuntimeError("Missing required environment variable: SITE_URL")
    SITE_URL = SITE_URL.rstrip("/")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


_config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config(env: str | None = None) -> type[Config]:
    """Return the config class for the given environment name."""
    name = env or os.environ.get("FLASK_ENV", "production")
    return _config_map.get(name, ProductionConfig)
