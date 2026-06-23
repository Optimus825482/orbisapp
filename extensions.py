"""
Flask Extensions

Merkezi extension yönetimi. Production'da CORS kısıtlanmalıdır.
"""

import os
from flask_cors import CORS
from flask_caching import Cache

cors = CORS()
cache = Cache()


def init_extensions(app):
    """Extension'ları başlat."""
    # Production için CORS kısıtlaması
    if os.environ.get("FLASK_ENV") == "production":
        cors.init_app(
            app,
            resources={
                r"/api/*": {
                    "origins": ["https://app.orbisastro.online", "https://*.orbisastro.online"],
                    "methods": ["GET", "POST", "OPTIONS"],
                    "allow_headers": ["Content-Type"],
                }
            },
        )
    else:
        # Development: her şeye izin ver
        cors.init_app(app)

    # Cache initialization
    from cache_config import init_cache

    init_cache(app)
