"""
Cache Configuration Module
===========================

Bu modül, Flask-Caching yapılandırmasını ve cache decorator'larını içerir.
Redis backend ile API response caching yapar.

Kullanım:
    from cache_config import cache, cached_view
    @cached_view(timeout=3600)
    def my_view():
        return expensive_calculation()
"""

from extensions import cache
from functools import wraps
import hashlib
import json
import logging
from typing import Any, Callable
from utils import Constants

logger = logging.getLogger(__name__)


# =============================================================================
# FLASK-CACHING CONFIGURATION
# =============================================================================
# cache is imported from extensions


CACHE_CONFIG = {
    "cache_type": "redis",
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
    "redis_password": "",
    "default_timeout": Constants.CACHE_TTL_AI_INTERPRETATION,
    "key_prefix": "astro_cache_",
    "threshold": 500,  # Maksimum cache entries
}


def init_cache(app):
    """
    Cache'i başlat.

    Args:
        app: Flask app instance
    """
    # Environment'dan cache yapılandırmasını al
    import os

    cache_type = os.getenv("CACHE_TYPE", "simple")

    if cache_type == "redis":
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = os.getenv("REDIS_DB", "0")
        redis_password = os.getenv("REDIS_PASSWORD", "")

        cache_config = {
            "CACHE_TYPE": "redis",
            "CACHE_REDIS_HOST": redis_host,
            "CACHE_REDIS_PORT": redis_port,
            "CACHE_REDIS_DB": int(redis_db),
            "CACHE_REDIS_PASSWORD": redis_password,
            "CACHE_DEFAULT_TIMEOUT": Constants.CACHE_TTL_AI_INTERPRETATION,
            "CACHE_KEY_PREFIX": "astro_cache_",
        }

        if redis_password:
            cache_config["CACHE_REDIS_URL"] = (
                f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            )
        else:
            cache_config["CACHE_REDIS_URL"] = (
                f"redis://{redis_host}:{redis_port}/{redis_db}"
            )

        logger.info(f"Redis cache configured at {redis_host}:{redis_port}")
    else:
        # Simple filesystem cache (fallback)
        cache_config = {
            "CACHE_TYPE": "simple",
            "CACHE_DEFAULT_TIMEOUT": Constants.CACHE_TTL_AI_INTERPRETATION,
            "CACHE_KEY_PREFIX": "astro_cache_",
        }

        logger.info("Simple cache configured (filesystem)")

    app.config.update(cache_config)
    cache.init_app(app)


# =============================================================================
# CACHE DECORATORS
# =============================================================================
def cached_ai_interpretation(timeout: int = Constants.CACHE_TTL_AI_INTERPRETATION):
    """
    AI yorumlarını cache'leyen decorator.

    Args:
        timeout: Cache timeout (saniye)

    Usage:
        @cached_ai_interpretation(timeout=3600)
        def generate_interpretation(provider, chart_data):
            # Expensive AI API call
            pass
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Cache key oluştur
            key_parts = [f.__name__]

            # Args'ı key'e ekle
            for arg in args:
                if isinstance(arg, (str, int, float, bool)):
                    key_parts.append(str(arg))
                elif isinstance(arg, dict):
                    # Dict'i sorted JSON'a çevir (deterministic)
                    sorted_dict = json.dumps(arg, sort_keys=True)
                    key_parts.append(hashlib.md5(sorted_dict.encode()).hexdigest()[:8])
                elif isinstance(arg, list):
                    key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])

            # Kwargs'ı key'e ekle
            for k in sorted(kwargs.keys()):
                v = kwargs[k]
                if isinstance(v, (str, int, float, bool)):
                    key_parts.append(f"{k}:{v}")
                elif isinstance(v, dict):
                    sorted_dict = json.dumps(v, sort_keys=True)
                    key_parts.append(
                        f"{k}:{hashlib.md5(sorted_dict.encode()).hexdigest()[:8]}"
                    )

            cache_key = ":".join(key_parts)

            # Cache'ten al
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value

            # Cache miss - hesapla ve cache'e koy
            logger.debug(f"Cache MISS: {cache_key}")
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)

            return result

        return wrapper

    return decorator


def cached_location_search(timeout: int = Constants.CACHE_TTL_LOCATION_SEARCH):
    """
    Location search sonuçlarını cache'leyen decorator.

    Args:
        timeout: Cache timeout (saniye) - 24 saat varsayılan

    Usage:
        @cached_location_search(timeout=86400)
        def search_location(query):
            # Expensive API call
            pass
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(query: str, *args, **kwargs):
            # Normalize query (trim, lowercase)
            normalized_query = query.strip().lower()

            # Cache key oluştur
            cache_key = (
                f"location_search:{hashlib.md5(normalized_query.encode()).hexdigest()}"
            )

            # Cache'ten al
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Location cache HIT: {normalized_query}")
                return cached_value

            # Cache miss - API çağrısı yap
            logger.debug(f"Location cache MISS: {normalized_query}")
            result = f(query, *args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)

            return result

        return wrapper

    return decorator


def cached_astro_calculation(timeout: int = Constants.CACHE_TTL_ASTRO_CALCULATION):
    """
    Astrolojik hesaplamaları cache'leyen decorator.

    Args:
        timeout: Cache timeout (saniye) - 30 dakika varsayılan

    Usage:
        @cached_astro_calculation(timeout=1800)
        def calculate_astro_data(birth_date, birth_time, lat, lon):
            # Expensive calculation
            pass
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(
            birth_date: Any,
            birth_time: Any,
            latitude: float,
            longitude: float,
            *args,
            **kwargs,
        ):
            # Cache key oluştur
            key_parts = [
                "astro_calc",
                str(birth_date),
                str(birth_time),
                f"{latitude:.4f}",
                f"{longitude:.4f}",
            ]

            cache_key = ":".join(key_parts)

            # Cache'ten al
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Astro calculation cache HIT: {cache_key}")
                return cached_value

            # Cache miss - hesapla
            logger.debug(f"Astro calculation cache MISS: {cache_key}")
            result = f(birth_date, birth_time, latitude, longitude, *args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)

            return result

        return wrapper

    return decorator


def invalidate_pattern(pattern: str):
    """
    Cache'i pattern ile temizle.

    Args:
        pattern: Cache key pattern (örn: "location_search:*")

    Note:
        Redis'te KEYS ve DELETE komutları kullanır.
    """
    try:
        # Redis client'ı al
        redis_client = cache.cache._client

        if redis_client:
            # Pattern ile eşleşen key'leri bul
            keys = redis_client.keys(f"*{pattern}*")

            if keys:
                # Sil
                redis_client.delete(*keys)
                logger.info(f"Cache invalidated: {len(keys)} keys matching '{pattern}'")
            else:
                logger.debug(f"No cache keys found matching pattern: '{pattern}'")
        else:
            logger.warning("Redis client not available for cache invalidation")

    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")


def clear_all_cache():
    """Tüm cache'i temizle."""
    try:
        cache.clear()
        logger.info("All cache cleared")
    except Exception as e:
        logger.error(f"Cache clear error: {e}")


def get_cache_stats() -> dict:
    """
    Cache istatistiklerini döndür.

    Returns:
        Cache stats dict
    """
    try:
        redis_client = cache.cache._client

        if redis_client:
            info = redis_client.info("stats")
            return {
                "type": "redis",
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_keys": redis_client.dbsize(),
            }
        else:
            return {"type": "simple", "message": "Stats not available for simple cache"}

    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {"error": str(e)}


# =============================================================================
# SESSION CACHING WRAPPER
# =============================================================================
def cached_session_data(
    session_id: str, timeout: int = Constants.SESSION_TIMEOUT_SECONDS
):
    """
    Session data'yı cache'leyen wrapper.

    Args:
        session_id: Session ID
        timeout: Cache timeout (saniye)

    Returns:
        Session data veya None
    """
    cache_key = f"session_data:{session_id}"
    return cache.get(cache_key)


def set_session_cache(
    session_id: str, data: Any, timeout: int = Constants.SESSION_TIMEOUT_SECONDS
):
    """
    Session data'yı cache'e kaydet.

    Args:
        session_id: Session ID
        data: Session data
        timeout: Cache timeout (saniye)
    """
    cache_key = f"session_data:{session_id}"
    cache.set(cache_key, data, timeout=timeout)


if __name__ == "__main__":
    # Test cache decorators
    print("Testing cache decorators...")

    @cached_ai_interpretation(timeout=60)
    def test_ai_func(provider, data):
        print(f"Calculating AI interpretation for {provider}")
        return {"result": f"AI result for {provider}"}

    # Test cache miss
    result1 = test_ai_func("natal", {"user": "John"})
    print(f"Result 1: {result1}")

    # Test cache hit
    result2 = test_ai_func("natal", {"user": "John"})
    print(f"Result 2: {result2}")

    print("✅ Cache decorators test completed!")
