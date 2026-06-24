"""
ORBIS Google Analytics 4 — Data API wrapper.
Server-side metric çekme (admin dashboard için).
Fail-closed: credential yoksa / API hata verirse None.
"""
import os
import json
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Cache (Redis varsa kullan, yoksa in-process dict)
_cache: Dict[str, tuple] = {}  # key -> (expires_at, value)
CACHE_TTL = 3600  # 1 saat

# GA4 'date' dimension değeri "YYYYMMDD" → "23 Haz" gibi kısa Türkçe etiket
_MONTHS_TR = ['', 'Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz',
              'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']


def _fmt_date(d: str) -> str:
    """GA4 'YYYYMMDD' → '23 Haz' gibi kısa etiket. Beklenmeyen formatta olduğu gibi döner."""
    if not d or len(d) < 8 or not d.isdigit():
        return d
    try:
        day = int(d[6:8])
        month = int(d[4:6])
        return f'{day} {_MONTHS_TR[month]}'
    except (ValueError, IndexError):
        return d


def _get_property_id() -> Optional[str]:
    return os.environ.get('GA4_PROPERTY_ID')


def _get_service_account_path() -> Optional[str]:
    """Service account credentials: dosya veya env JSON. Öncelik: env JSON > dosya."""
    import tempfile
    json_env = os.environ.get('GA4_SERVICE_ACCOUNT_JSON')
    if json_env:
        # Env'den gelen JSON'u temp dosyaya yaz (Google lib dosya istiyor)
        try:
            fd, path = tempfile.mkstemp(suffix='.json', prefix='ga4-sa-')
            os.write(fd, json_env.encode('utf-8') if isinstance(json_env, str) else json_env)
            os.close(fd)
            return path
        except Exception:
            pass
    path = os.environ.get('GA4_SERVICE_ACCOUNT_PATH')
    if path and os.path.exists(path):
        return path
    return None


def _cache_get(key: str):
    if key in _cache:
        import time
        expires_at, value = _cache[key]
        if expires_at > time.time():
            return value
        _cache.pop(key, None)
    return None


def _cache_set(key: str, value, ttl: int = CACHE_TTL):
    import time
    _cache[key] = (time.time() + ttl, value)


def _get_client():
    """GA4 Data API client. None dönerse admin dashboard 'credentials missing' gösterir."""
    sa_path = _get_service_account_path()
    if not sa_path:
        return None
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            sa_path, scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        return BetaAnalyticsDataClient(credentials=creds)
    except Exception as e:
        logger.exception('[GA4] client init failed')
        return None


def _run_report(date_range: str = '7d') -> Optional[Dict[str, Any]]:
    """Ana metrikleri çek."""
    prop_id = _get_property_id()
    if not prop_id:
        return None
    cache_key = f'report:{date_range}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    client = _get_client()
    if client is None:
        return None

    days = {'1d': 1, '7d': 7, '30d': 30, '90d': 90}.get(date_range, 7)

    try:
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Metric, Dimension
        )
        req = RunReportRequest(
            property=f'properties/{prop_id}',
            dimensions=[Dimension(name='date')],
            metrics=[
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='screenPageViews'),
                Metric(name='conversions'),
                Metric(name='averageSessionDuration'),
            ],
            date_ranges=[DateRange(start_date=f'{days}daysAgo', end_date='today')],
        )
        resp = client.run_report(req)
        result = {
            'range': date_range,
            'rows': [
                {
                    'date': r.dimension_values[0].value,
                    'users': int(r.metric_values[0].value),
                    'sessions': int(r.metric_values[1].value),
                    'pageViews': int(r.metric_values[2].value),
                    'conversions': int(r.metric_values[3].value),
                    'avgDuration': float(r.metric_values[4].value),
                }
                for r in resp.rows
            ],
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        logger.exception('[GA4] run_report failed')
        return None


def get_overview(date_range: str = '7d') -> Optional[Dict[str, Any]]:
    """Admin dashboard overview: total + signups series + active series."""
    data = _run_report(date_range)
    if not data or not data.get('rows'):
        return None
    rows = data['rows']
    total_users = sum(r['users'] for r in rows)
    total_sessions = sum(r['sessions'] for r in rows)
    total_pageviews = sum(r['pageViews'] for r in rows)
    total_conversions = sum(r['conversions'] for r in rows)
    # Ağırlıklı ortalama session süresi (saniye → "1m 24s")
    if total_sessions > 0:
        avg_sec = sum(r.get('avgDuration', 0) * r['sessions'] for r in rows) / total_sessions
        avg_str = f'{int(avg_sec // 60)}m {int(avg_sec % 60)}s'
    else:
        avg_str = '—'
    return {
        'range': date_range,
        'totalUsers': total_users,
        'totalSessions': total_sessions,
        'totalPageViews': total_pageviews,
        'totalConversions': total_conversions,
        'avgSessionDuration': avg_str,
        'usersSeries': [{'label': _fmt_date(r['date']), 'value': r['users']} for r in rows],
        'sessionsSeries': [{'label': _fmt_date(r['date']), 'value': r['sessions']} for r in rows],
    }


def get_top_pages(date_range: str = '7d', limit: int = 10) -> Optional[List[Dict[str, Any]]]:
    """En çok ziyaret edilen sayfalar."""
    prop_id = _get_property_id()
    if not prop_id:
        return None
    cache_key = f'top_pages:{date_range}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    client = _get_client()
    if client is None:
        return None

    days = {'1d': 1, '7d': 7, '30d': 30, '90d': 90}.get(date_range, 7)
    try:
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Metric, Dimension, OrderBy
        )
        req = RunReportRequest(
            property=f'properties/{prop_id}',
            dimensions=[Dimension(name='pageTitle'), Dimension(name='pagePath')],
            metrics=[Metric(name='screenPageViews')],
            date_ranges=[DateRange(start_date=f'{days}daysAgo', end_date='today')],
            limit=limit,
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name='screenPageViews'), desc=True)],
        )
        resp = client.run_report(req)
        result = [
            {
                'title': r.dimension_values[0].value,
                'path': r.dimension_values[1].value,
                'views': int(r.metric_values[0].value),
            }
            for r in resp.rows
        ]
        _cache_set(cache_key, result)
        return result
    except Exception:
        logger.exception('[GA4] get_top_pages failed')
        return None


def get_traffic_sources(date_range: str = '7d') -> Optional[List[Dict[str, Any]]]:
    """Trafik kaynakları (source/medium)."""
    prop_id = _get_property_id()
    if not prop_id:
        return None
    cache_key = f'traffic:{date_range}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    client = _get_client()
    if client is None:
        return None

    days = {'1d': 1, '7d': 7, '30d': 30, '90d': 90}.get(date_range, 7)
    try:
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Metric, Dimension, OrderBy
        )
        req = RunReportRequest(
            property=f'properties/{prop_id}',
            dimensions=[Dimension(name='sessionSourceMedium')],
            metrics=[Metric(name='sessions')],
            date_ranges=[DateRange(start_date=f'{days}daysAgo', end_date='today')],
            limit=10,
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name='sessions'), desc=True)],
        )
        resp = client.run_report(req)
        result = [
            {'source': r.dimension_values[0].value, 'sessions': int(r.metric_values[0].value)}
            for r in resp.rows
        ]
        _cache_set(cache_key, result)
        return result
    except Exception:
        logger.exception('[GA4] get_traffic_sources failed')
        return None
