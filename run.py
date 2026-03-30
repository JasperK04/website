"""
Entry point for the portfolio Flask application.

Development::

    FLASK_ENV=development python run.py

Production (via a WSGI server)::

    gunicorn "run:app"
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
