"""
Gunicorn yapılandırması — ORBIS Astrology Backend
Gevent worker ile streaming desteği, paylaşımlı sunucu için muhafazakar ayarlar.
"""
import os

# ── Worker tipi ──────────────────────────────────────────────────────────────
# gevent: AI streaming (SSE) için I/O bloğu olmadan çalışır
worker_class = "sync"

# ── Worker sayısı — sabit ve düşük ──────────────────────────────────────────
# Paylaşımlı sunucuda diğer uygulamaları yormamak için 2 worker sabit.
# Gevent sayesinde 2 worker × 500 greenlet = 1000 eşzamanlı bağlantı
# bu uygulama için fazlasıyla yeterli.
workers = 4

# ── Her worker'ın eşzamanlı bağlantı kapasitesi ─────────────────────────────
# worker_connections: sadece async worker'lar (gevent/eventlet) için, sync worker'da kullanılmaz

# ── Thread — gevent'te kullanılmaz ───────────────────────────────────────────
threads = 2

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
preload_app         = True   # Fork öncesi yükle → worker'lar belleği paylaşır
max_requests        = 1000   # Bellek sızıntısına karşı worker yenileme
max_requests_jitter = 100
