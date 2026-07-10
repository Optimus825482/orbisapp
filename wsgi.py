"""
Gunicorn entrypoint.
Usage: gunicorn --config gunicorn.conf.py wsgi:app

Gevent monkey patch: stdlib'in I/O operasyonlarını (socket, ssl, threading)
async-uyumlu gevent versiyonlarıyla değiştirir. Bu olmadan gevent worker
tam kapasiteyle çalışamaz.
"""
from gevent import monkey
monkey.patch_all()

from app import app  # noqa: F401
