"""
Gunicorn entrypoint.
Usage: gunicorn wsgi:app
"""
from app import app  # noqa: F401
