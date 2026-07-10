"""
Gunicorn entrypoint.
Usage: gunicorn --config gunicorn.conf.py wsgi:app
"""
from app import app
