"""
Gunicorn yapılandırması — ORBIS Astrology Backend
Sync worker (threads) ile stabil performans.
"""
import os

# ── Worker tipi ──────────────────────────────────────────────────────────────
# sync: Klasik thread-based worker (gevent kapatıldı)
worker_class = "sync"

# ── Worker sayısı ───────────────────────────────────────────────────────────
workers = 4

# ── Thread sayısı (sync worker için) ────────────────────────────────────────
threads = 2  # Her worker 2 thread → 4 × 2 = 8 eşzamanlı istek

# ── Bağlantı ve timeout ──────────────────────────────────────────────────────
bind             = f"0.0.0.0:{os.environ.get('PORT', 8005)}"
timeout          = 120    # Timeout süre
keepalive        = 5
graceful_timeout = 30

# ── Logging ──────────────────────────────────────────────────────────────────
loglevel     = "info"
accesslog    = "-"
errorlog     = "-"

# ── Performans ───────────────────────────────────────────────────────────────
preload_app         = True   # Fork öncesi yükle
max_requests        = 1000   # Worker yenileme
max_requests_jitter = 100
