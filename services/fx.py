"""
ORBIS FX (Foreign Exchange) service.
USD → TRY dönüşümü için canlı kur + cache.
"""
import os
import time
import logging
from typing import Optional, Dict

import requests

logger = logging.getLogger(__name__)

CACHE_TTL = 3600  # 1 saat
_cache: Dict[str, tuple] = {}

API_URL = 'https://open.er-api.com/v6/latest/USD'
DEFAULT_USD_TO_TRY = float(os.environ.get('FX_USD_TO_TRY', '35.0'))


def _cache_get(key: str):
    if key in _cache:
        expires_at, value = _cache[key]
        if expires_at > time.time():
            return value
        _cache.pop(key, None)
    return None


def _cache_set(key: str, value, ttl: int = CACHE_TTL):
    _cache[key] = (time.time() + ttl, value)


def get_usd_to_try() -> float:
    cached = _cache_get('usd_try')
    if cached is not None:
        return cached
    env_rate = os.environ.get('FX_USD_TO_TRY')
    if env_rate:
        try:
            rate = float(env_rate)
            _cache_set('usd_try', rate)
            logger.info(f'[FX] USD→TRY from env: {rate}')
            return rate
        except (ValueError, TypeError):
            pass
    try:
        resp = requests.get(API_URL, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            rates = data.get('rates') or {}
            try_rate = rates.get('TRY')
            if try_rate and try_rate > 0:
                _cache_set('usd_try', float(try_rate))
                logger.info(f'[FX] USD→TRY from API: {try_rate}')
                return float(try_rate)
    except Exception as e:
        logger.warning(f'[FX] API failed: {e}')
    logger.info(f'[FX] USD→TRY fallback: {DEFAULT_USD_TO_TRY}')
    _cache_set('usd_try', DEFAULT_USD_TO_TRY, ttl=300)
    return DEFAULT_USD_TO_TRY


def to_try(usd: float) -> float:
    if usd is None or usd == 0:
        return 0.0
    return round(float(usd) * get_usd_to_try(), 2)


def fmt_usd_and_try(usd: float) -> str:
    if usd is None or usd == 0:
        return '$0.00'
    try_usd = to_try(usd)
    return f'${usd:.2f} (₺{try_usd:.2f})'
