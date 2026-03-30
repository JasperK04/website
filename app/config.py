"""
Configuration classes for the portfolio Flask app.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DATA_DIR = BASE_DIR / "data"
    CODE_DIR = BASE_DIR / "static" / "code"


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
