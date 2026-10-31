"""
ORBIS Admin Dashboard Routes
Premium kullanıcı yönetimi, kredi sistemi ve push bildirimleri
"""

from functools import wraps
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from services.firebase_service import firebase_service
from exceptions import (
    ValidationError, DatabaseError, ConfigurationError,
    error_response, handle_errors
)
import os
import json
import logging

from google.cloud.firestore_v1.base_query import FieldFilter

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ═══════════════════════════════════════════════════════════════
# ADMIN AUTHENTICATION
# ═══════════════════════════════════════════════════════════════

# Admin email listesi (environment variable'dan veya hardcoded)
ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get('ADMIN_EMAILS', 'erkan@example.com').split(',') if e.strip()]


def admin_required(f):
    """Admin yetkisi gerektiren route'lar için decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Session'dan admin kontrolü
        admin_email = (session.get('admin_email') or '').strip().lower()
        if not admin_email or admin_email not in ADMIN_EMAILS:
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET'])
def login():
    """Admin giriş sayfası"""
    return render_template('admin/login.html')


@admin_bp.route('/auth/verify', methods=['POST'])
@handle_errors("Admin doğrulama başarısız")
def verify_admin():
    """Firebase token'ı doğrula ve admin yetkisi kontrol et"""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    uid = data.get('uid')
    
    if not email:
        return jsonify({
            'success': False, 
            'error': 'EMAIL_REQUIRED',
            'message': 'Email gerekli'
        }), 400
    
    # Admin kontrolü
    if email not in ADMIN_EMAILS:
        logger.warning(f"Unauthorized admin access attempt: {email}")
        return jsonify({
            'success': False, 
            'error': 'FORBIDDEN',
            'message': 'Bu hesap admin yetkisine sahip değil'
        }), 403
    
    # Session'a kaydet
    session['admin_email'] = email
    session['admin_uid'] = uid
    session['admin_name'] = data.get('displayName') or email.split('@')[0]
    
    logger.info(f"Admin login successful: {email}")
    
    return jsonify({
        'success': True,
        'redirect': url_for('admin.dashboard')
    })


@admin_bp.route('/logout')
def logout():
    """Admin çıkış"""
    session.pop('admin_email', None)
    session.pop('admin_uid', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin.login'))


# ═══════════════════════════════════════════════════════════════
# DASHBOARD PAGES
# ═══════════════════════════════════════════════════════════════

@admin_bp.route('/')
@admin_required
def dashboard():
    """Ana dashboard sayfası"""
    return render_template('admin/dashboard.html')


@admin_bp.route('/users')
@admin_required
def users():
    """Kullanıcı listesi sayfası"""
    return render_template('admin/users.html')


@admin_bp.route('/users/<user_id>')
@admin_required
def user_detail(user_id):
    """Kullanıcı detay sayfası"""
    return render_template('admin/user_detail.html', user_id=user_id)


@admin_bp.route('/push')
@admin_required
def push_notifications():
    """Push bildirim gönderme sayfası"""
    return render_template('admin/push.html')


@admin_bp.route('/pricing')
@admin_required
def pricing():
    """Fiyat yönetimi sayfası"""
    return render_template('admin/pricing.html')


@admin_bp.route('/ai-settings')
@admin_required
def ai_settings():
    """AI Yapılandırma sayfası"""
    return render_template('admin/ai_settings.html')


@admin_bp.route('/admob')
@admin_required
def admob_page():
    """AdMob raporları sayfası — gelir, impressions, eCPM, uygulama bazlı performans."""
    from services.admob import _get_config
    configured = _get_config() is not None
    return render_template('admin/admob.html', admob_configured=configured)


@admin_bp.route('/stats')
@admin_required
def statistics():
    """İstatistikler sayfası"""
    return render_template('admin/stats.html')


# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@admin_bp.route('/api/stats/overview', methods=['GET'])
@admin_required
@handle_errors("İstatistikler alınamadı")
def get_stats_overview():
    """Dashboard için genel istatistikler - StatsCounter kullanır (1 READ)"""
    from services.stats_counter import stats_counter
    
    stats = stats_counter.get_overview()
    
    if not stats:
        return jsonify({
            'success': False,
            'error': 'DATABASE_UNAVAILABLE',
            'message': 'İstatistikler alınamadı'
        }), 500
    
    return jsonify({
        'success': True,
        'data': {
            'totalUsers': stats.get('total_users', 0),
            # Premium kaldirildi: geriye uyumluluk icin 0 dondurulur
            'premiumUsers': 0,
            'freeUsers': stats.get('total_users', 0),
            'totalCredits': 0,
            'totalAnalyses': stats.get('total_analyses', 0),
            'totalAdsWatched': stats.get('total_ads_watched', 0),
            'totalRewardedAds': stats.get('total_rewarded_ads', 0),
            'activeToday': stats.get('active_today', 0),
            'analysesToday': stats.get('analyses_today', 0),
            'rewardedAdsToday': stats.get('rewarded_ads_today', 0),
            'lastLoginEmail': stats.get('last_login_email', ''),
            'lastLoginName': stats.get('last_login_name', ''),
            'lastLoginTime': stats.get('last_login_time', ''),
            # GA4 series (None ise client default gösterir)
            **_attach_ga_data(request.args.get('range', '7d')),
            # AdMob (None ise client default gösterir)
            **_attach_admob_data(request.args.get('range', '7d')),
            # Activity feed (Firestore son olaylar)
            **_attach_activity(),
        }
    })


def _attach_ga_data(date_range: str) -> dict:
    """GA4 Data API'den series çek. Service yoksa boş döner (client default)."""
    try:
        from services.google_analytics import get_overview
        data = get_overview(date_range)
        if not data:
            return {}
        rows = data.get('rows', []) or []
        # Son gün (bugün) değerleri
        today = rows[-1] if rows else {}
        return {
            'signupsSeries': data.get('usersSeries', []),
            'activeSeries': data.get('sessionsSeries', []),
            'gaConversions': data.get('totalConversions', 0),
            'gaPageViews': data.get('totalPageViews', 0),
            'gaUsersToday': today.get('users', 0),
            'gaSessionsToday': today.get('sessions', 0),
            'gaAvgTime': data.get('avgSessionDuration', '—'),
        }
    except Exception:
        return {}


def _attach_admob_data(date_range: str) -> dict:
    """AdMob API'den revenue/impressions. Service yoksa boş döner."""
    try:
        from services.admob import get_overview
        from services.fx import to_try
        data = get_overview(date_range)
        if not data:
            return {}
        rows = data.get('rows', []) or []
        # Bugünün (son gün) değeri
        today = rows[-1] if rows else {}
        rev_today_usd = today.get('revenue_usd', data.get('revenue_usd', 0)) or 0
        rev_total_usd = data.get('revenue_usd', 0) or 0
        ecpm_usd = data.get('ecpm_usd', 0) or 0
        # Sparkline: son N günlük gelir (USD)
        spark_usd = [float(r.get('revenue_usd', 0) or 0) for r in rows[-8:]]
        # Chart series
        revenue_series = [{'label': r.get('date', '')[-5:], 'value': float(r.get('revenue_usd', 0) or 0)} for r in rows[-8:]] if rows else []
        rewarded_series = [{'label': r.get('date', '')[-5:], 'value': int(r.get('rewarded_impressions', r.get('impressions', 0)) or 0)} for r in rows[-8:]] if rows else []
        return {
            'admob': {
                'revenue_today': rev_today_usd,
                'revenue_today_try': to_try(rev_today_usd),
                'impressions_today': today.get('impressions', data.get('impressions', 0)),
                'ecpm_today': ecpm_usd,
                'ecpm_today_try': to_try(ecpm_usd),
                'revenue_total': rev_total_usd,
                'revenue_total_try': to_try(rev_total_usd),
                'impressions_total': data.get('impressions', 0),
                'range': data.get('range', date_range),
            },
            'admobSparkline': spark_usd or None,
            'admobRevenueSeries': revenue_series or None,
            'admobRewardedSeries': rewarded_series or None,
        }
    except Exception:
        return {}


def _attach_activity() -> dict:
    """Firestore son 10 olay (signup, push, admin işlem)."""
    try:
        from services.firebase_service import firebase_service
        if not firebase_service.db:
            return {}
        from google.cloud.firestore import Query
        from datetime import datetime, timezone

        def format_rel(t):
            if not t:
                return ''
            try:
                dt = t if isinstance(t, datetime) else datetime.fromisoformat(str(t).replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - dt
                if delta.days > 0:
                    return f'{delta.days}g önce'
                elif delta.seconds > 3600:
                    return f'{delta.seconds // 3600}s önce'
                elif delta.seconds > 60:
                    return f'{delta.seconds // 60}dk önce'
                else:
                    return 'az önce'
            except Exception:
                return ''

        items = []

        # 1. Son kullanıcı kayıtları
        try:
            users_docs = list(firebase_service.db.collection('users')
                .order_by('createdAt', direction=Query.DESCENDING)
                .limit(6).stream())
            for d in users_docs:
                u = d.to_dict() or {}
                t = u.get('createdAt')
                email = u.get('email', '')
                name = u.get('displayName') or (email.split('@')[0] if email else 'Yeni Kullanıcı')
                items.append({
                    'type': 'signup',
                    'title': f'Yeni Kayıt · {name}',
                    'meta': email or f"uid: {d.id[:10]}…",
                    'relative': format_rel(t),
                    'timestamp': str(t) if t else '',
                })
        except Exception as e:
            logger.debug(f"[Admin] Activity user signup fetch notice: {e}")

        # 2. Son admin işlem kayıtları (push gönderimi, ayar güncelleme vs.)
        try:
            admin_docs = list(firebase_service.db.collection('admin_logs')
                .order_by('timestamp', direction=Query.DESCENDING)
                .limit(6).stream())
            for d in admin_docs:
                log_data = d.to_dict() or {}
                t = log_data.get('timestamp')
                act = log_data.get('action', 'islem')
                title = 'Admin İşlemi'
                meta = log_data.get('adminEmail', 'Admin')
                if act == 'push_sent':
                    title = f"Push Bildirim: {log_data.get('details', {}).get('title', '')[:25]}"
                elif act == 'ai_settings_update':
                    title = f"AI Sağlayıcı Güncellendi ({log_data.get('details', {}).get('active_provider', '')})"

                items.append({
                    'type': 'info',
                    'title': title,
                    'meta': meta,
                    'relative': format_rel(t),
                    'timestamp': str(t) if t else '',
                })
        except Exception as e:
            logger.debug(f"[Admin] Activity admin logs fetch notice: {e}")

        # 3. Geriye uyumluluk: eski purchases
        if len(items) < 5:
            try:
                p_docs = list(firebase_service.db.collection('purchases')
                    .order_by('timestamp', direction=Query.DESCENDING)
                    .limit(5).stream())
                for d in p_docs:
                    data = d.to_dict() or {}
                    t = data.get('timestamp')
                    items.append({
                        'type': 'info',
                        'title': f"Etkinlik · {data.get('packageId', data.get('type', 'bilinmiyor'))}",
                        'meta': f"uid: {data.get('userId', '?')[:12]}…",
                        'relative': format_rel(t),
                        'timestamp': str(t) if t else '',
                    })
            except Exception:
                pass

        # Tarihe göre sırala ve son 10 adedini dön
        items.sort(key=lambda x: x.get('timestamp') or '', reverse=True)
        return {'activity': items[:10]} if items else {}
    except Exception:
        return {}


# ─── GA4 + AdMob standalone endpoints (deep link için) ─────
@admin_bp.route('/api/analytics/overview', methods=['GET'])
@admin_required
@handle_errors("Analytics alınamadı")
def get_analytics_overview():
    """GA4 özet verileri (kendi route'u, dashboard bağımsız)."""
    from services.google_analytics import get_overview as ga_overview
    date_range = request.args.get('range', '7d')
    data = ga_overview(date_range)
    if data is None:
        return jsonify({
            'success': False,
            'error': 'GA4_NOT_CONFIGURED',
            'message': 'GA4 service account / property ID eksik. env.example\'a bakın.',
        }), 503
    return jsonify({'success': True, 'data': data})


@admin_bp.route('/api/analytics/top-pages', methods=['GET'])
@admin_required
@handle_errors("Top pages alınamadı")
def get_analytics_top_pages():
    from services.google_analytics import get_top_pages
    date_range = request.args.get('range', '7d')
    data = get_top_pages(date_range)
    if data is None:
        return jsonify({'success': False, 'error': 'GA4_NOT_CONFIGURED'}), 503
    return jsonify({'success': True, 'data': data})


@admin_bp.route('/api/analytics/traffic', methods=['GET'])
@admin_required
@handle_errors("Traffic alınamadı")
def get_analytics_traffic():
    from services.google_analytics import get_traffic_sources
    date_range = request.args.get('range', '7d')
    data = get_traffic_sources(date_range)
    if data is None:
        return jsonify({'success': False, 'error': 'GA4_NOT_CONFIGURED'}), 503
    return jsonify({'success': True, 'data': data})


@admin_bp.route('/api/admob/overview', methods=['GET'])
@admin_required
@handle_errors("AdMob alınamadı")
def get_admob_overview():
    from services.admob import get_overview as admob_overview
    date_range = request.args.get('range', '30d')
    data = admob_overview(date_range)
    if data is None:
        return jsonify({
            'success': False,
            'error': 'ADMOB_NOT_CONFIGURED',
            'message': 'AdMob OAuth credentials eksik. env.example\'a bakın.',
        }), 503
    return jsonify({'success': True, 'data': data})


@admin_bp.route('/api/fx/rate', methods=['GET'])
@admin_required
def get_fx_rate():
    """USD→TRY kuru (client-side hesaplama için)."""
    from services.fx import get_usd_to_try
    return jsonify({'success': True, 'rate': get_usd_to_try(), 'base': 'USD', 'symbol': 'TRY'})


@admin_bp.route('/api/admob/apps', methods=['GET'])
@admin_required
@handle_errors("AdMob apps alınamadı")
def get_admob_apps():
    from services.admob import get_apps
    data = get_apps()
    if data is None:
        return jsonify({'success': False, 'error': 'ADMOB_NOT_CONFIGURED'}), 503
    return jsonify({'success': True, 'data': data})


@admin_bp.route('/api/users', methods=['GET'])
@admin_required
@handle_errors("Kullanıcı listesi alınamadı")
def get_users():
    """Kullanıcı listesi - select() projection + Firestore pagination"""
    db = firebase_service.db
    if not db:
        return jsonify({
            'success': False,
            'error': 'DATABASE_UNAVAILABLE',
            'message': 'Firebase bağlantısı yok'
        }), 500

    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    filter_type = request.args.get('filter', 'all')
    search = request.args.get('search', '').lower()

    # Sadece gerekli field'lari oku (premium/credits kaldirildi)
    PROJECTION = ["email", "displayName", "photoURL",
                   "totalAnalyses", "adsWatched", "rewardedAdsWatched",
                   "createdAt", "dailyUsage", "lastLogin", "lastSeen", "isAdmin"]

    users_ref = db.collection('users')

    # Premium/free filtreleri kaldirildi — uygulama ucretsiz.
    # Geriye uyumluluk: filter=all kabul edilir, premium/free no-op sayilir.

    # Search varsa tumunu oku (Firestore text search desteklemez)
    if search:
        all_users = list(users_ref.select(PROJECTION).stream())
        filtered = []
        for u in all_users:
            data = u.to_dict()
            email = (data.get('email', '') or '').lower()
            name = (data.get('displayName', '') or '').lower()
            if search in email or search in name:
                filtered.append((u.id, data))
        total = len(filtered)
        users = filtered[offset:offset + limit]
    else:
        # COUNT ile toplam sayi
        total = users_ref.count().get()[0][0].value
        # Pagination ile oku
        users_data = list(
            users_ref.select(PROJECTION)
            .offset(offset)
            .limit(limit)
            .stream()
        )
        users = [(u.id, u.to_dict()) for u in users_data]

    user_list = [{
        'id': uid,
        'email': data.get('email'),
        'displayName': data.get('displayName'),
        'photoURL': data.get('photoURL'),
        'isAdmin': ((data.get('email') or '').lower() in ADMIN_EMAILS) or bool(data.get('isAdmin', False)),
        'isPremium': False,  # geriye uyumluluk: artik herkes ucretsiz
        'credits': 0,        # geriye uyumluluk
        'totalAnalyses': data.get('totalAnalyses', 0),
        'adsWatched': data.get('adsWatched', 0),
        'rewardedAdsWatched': data.get('rewardedAdsWatched', 0),
        'createdAt': data.get('createdAt'),
        'lastLogin': data.get('lastLogin'),
        'lastSeen': data.get('lastSeen') or data.get('lastLogin'),
        'dailyUsage': data.get('dailyUsage', {})
    } for uid, data in users]

    return jsonify({
        'success': True,
        'data': {
            'users': user_list,
            'total': total,
            'limit': limit,
            'offset': offset
        }
    })


@admin_bp.route('/api/users/<user_id>', methods=['GET'])
@admin_required
@handle_errors("Kullanıcı detayı alınamadı")
def get_user_detail(user_id):
    """Tek kullanıcı detayı"""
    db = firebase_service.db
    if not db:
        return jsonify({
            'success': False,
            'error': 'DATABASE_UNAVAILABLE',
            'message': 'Firebase bağlantısı yok'
        }), 500
    
    doc = db.collection('users').document(user_id).get()
    
    if not doc.exists:
        return jsonify({
            'success': False, 
            'error': 'USER_NOT_FOUND',
            'message': 'Kullanıcı bulunamadı'
        }), 404
    
    data = doc.to_dict()
    
    # Satın alma / etkinlik geçmişi (composite index hatasına karşı korumalı)
    purchase_list = []
    try:
        purchases = list(
            db.collection('purchases')
            .where(filter=FieldFilter('userId', '==', user_id))
            .limit(20)
            .stream()
        )
        for p in purchases:
            pdata = p.to_dict()
            purchase_list.append({
                'id': p.id,
                'type': pdata.get('type'),
                'item': pdata.get('item') or pdata.get('packageId'),
                'amount': pdata.get('amount') or pdata.get('credits'),
                'timestamp': pdata.get('timestamp')
            })
        purchase_list.sort(key=lambda x: str(x.get('timestamp') or ''), reverse=True)
    except Exception as e:
        logger.warning(f"User purchases query error: {e}")

    return jsonify({
        'success': True,
        'data': {
            'id': user_id,
            'email': data.get('email'),
            'displayName': data.get('displayName'),
            'photoURL': data.get('photoURL'),
            'isAdmin': ((data.get('email') or '').lower() in ADMIN_EMAILS) or bool(data.get('isAdmin', False)),
            'isPremium': False,  # geriye uyumluluk: artik herkes ucretsiz
            'premiumPackageId': None,
            'premiumExpiry': None,
            'credits': 0,
            'totalAnalyses': data.get('totalAnalyses', 0),
            'adsWatched': data.get('adsWatched', 0),
            'rewardedAdsWatched': data.get('rewardedAdsWatched', 0),
            'createdAt': data.get('createdAt'),
            'lastLogin': data.get('lastLogin'),
            'lastSeen': data.get('lastSeen') or data.get('lastLogin'),
            'dailyUsage': data.get('dailyUsage', {}),
            'fcmTokens': data.get('fcmTokens', []),
            'purchases': purchase_list
        }
    })


@admin_bp.route('/api/users/<user_id>/premium', methods=['POST'])
@admin_required
@handle_errors("Premium durum güncellenemedi")
def update_user_premium(user_id):
    """DEPRECATED: Premium kaldirildi. Uygulama ucretsiz.

    Geriye uyumluluk icin no-op dondurur. Yeni premium alanlari kullanmayin.
    """
    logger.warning(
        "[admin] update_user_premium called for %s but premium is removed (no-op)",
        user_id,
    )
    return jsonify({
        'success': True,
        'message': 'Premium kaldirildi. Uygulama tamamen ucretsiz, sadece reklam destekli.',
        'deprecated': True,
    })


@admin_bp.route('/api/users/<user_id>/credits', methods=['POST'])
@admin_required
@handle_errors("Kredi güncellenemedi")
def update_user_credits(user_id):
    """DEPRECATED: Krediler kaldirildi. Analizler reklam destekli ucretsiz.

    Geriye uyumluluk icin no-op dondurur.
    """
    logger.warning(
        "[admin] update_user_credits called for %s but credits are removed (no-op)",
        user_id,
    )
    return jsonify({
        'success': True,
        'message': 'Krediler kaldirildi. Analizler reklam izleyerek ucretsiz.',
        'deprecated': True,
    })


@admin_bp.route('/api/push/send', methods=['POST'])
@admin_required
@handle_errors("Push bildirim gönderilemedi")
def send_push_notification():
    """Push bildirim gönder"""
    data = request.get_json()
    
    target_type = data.get('targetType')  # user, topic, all
    target = data.get('target')  # userId veya topic adı
    title = data.get('title')
    body = data.get('body')
    extra_data = data.get('data', {})
    
    if not all([target_type, title, body]):
        return jsonify({
            'success': False,
            'error': 'MISSING_PARAMS',
            'message': 'targetType, title ve body gerekli'
        }), 400
    
    result = None
    
    if target_type == 'user':
        tokens = firebase_service.get_user_tokens(target)
        if tokens:
            result = firebase_service.send_push_to_multiple(tokens, title, body, extra_data)
        else:
            return jsonify({
                'success': False,
                'error': 'NO_TOKENS',
                'message': 'Kullanıcının kayıtlı token\'ı yok'
            }), 404
            
    elif target_type == 'topic':
        result = firebase_service.send_push_to_topic(target, title, body, extra_data)
        
    elif target_type == 'all':
        result = firebase_service.send_push_to_topic('all_users', title, body, extra_data)
    
    # Admin log
    db = firebase_service.db
    if db:
        from firebase_admin import firestore
        db.collection('admin_logs').add({
            'action': 'push_sent',
            'adminEmail': session.get('admin_email'),
            'details': {
                'targetType': target_type,
                'target': target,
                'title': title
            },
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    
    logger.info(f"Push notification sent by {session.get('admin_email')}: {target_type} - {title}")
    
    return jsonify({
        'success': result is not None,
        'result': result if isinstance(result, dict) else {'messageId': result}
    })


@admin_bp.route('/api/stats/purchases', methods=['GET'])
@admin_required
@handle_errors("Satın alma istatistikleri alınamadı")
def get_purchase_stats():
    """Satın alma istatistikleri"""
    db = firebase_service.db
    if not db:
        return jsonify({
            'success': False,
            'error': 'DATABASE_UNAVAILABLE',
            'message': 'Firebase bağlantısı yok'
        }), 500
    
    # Son 30 günlük etkinlikler (premium/credits kaldirildi)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)

    purchases = list(
        db.collection('purchases')
        .where(filter=FieldFilter('timestamp', '>=', thirty_days_ago))
        .stream()
    )

    # Premium/credit satisi kaldirildi — sadece toplam kayit sayisi
    total_events = len(purchases)

    return jsonify({
        'success': True,
        'data': {
            'last30Days': {
                # Premium ve kredi satisi kaldirildi
                'premiumPurchases': 0,
                'creditPurchases': 0,
                'totalCreditsSold': 0,
                'totalEvents': total_events,
                'totalPurchases': total_events,
                'message': 'Premium ve krediler kaldirildi. Uygulama tamamen ucretsizdir.'
            }
        }
    })


@admin_bp.route('/api/pricing', methods=['GET'])
@admin_required
@handle_errors("Fiyat bilgileri alınamadı")
def get_pricing():
    """Firestore'dan fiyat bilgilerini getir (admin)"""
    db = firebase_service.db
    if not db:
        return jsonify({
            'success': False,
            'error': 'DATABASE_UNAVAILABLE',
            'message': 'Firebase bağlantısı yok'
        }), 500
    
    doc = db.collection('config').document('pricing').get()
    
    if doc.exists:
        data = doc.to_dict()
        return jsonify({
            'success': True,
            'data': {
                'daily': data.get('daily', 30),
                'monthly': data.get('monthly', 300),
                'yearly': data.get('yearly', 3000),
                'currency': data.get('currency', 'TRY'),
                'updated_at': data.get('updated_at'),
                'updated_by': data.get('updated_by'),
            }
        })
    
    # Varsayılan
    return jsonify({
        'success': True,
        'data': {
            'daily': 30,
            'monthly': 300,
            'yearly': 3000,
            'currency': 'TRY',
        }
    })


@admin_bp.route('/api/pricing', methods=['POST'])
@admin_required
@handle_errors("Fiyatlar güncellenemedi")
def update_pricing():
    """Firestore'a fiyat bilgilerini kaydet (admin)"""
    data = request.get_json()
    
    daily = data.get('daily')
    monthly = data.get('monthly')
    yearly = data.get('yearly')
    
    if not all([daily, monthly, yearly]):
        return jsonify({
            'success': False,
            'error': 'MISSING_PARAMS',
            'message': 'daily, monthly ve yearly fiyatları gerekli'
        }), 400
    
    db = firebase_service.db
    if not db:
        return jsonify({
            'success': False,
            'error': 'DATABASE_UNAVAILABLE',
            'message': 'Firebase bağlantısı yok'
        }), 500
    
    from datetime import datetime
    from firebase_admin import firestore
    
    db.collection('config').document('pricing').set({
        'daily': int(daily),
        'monthly': int(monthly),
        'yearly': int(yearly),
        'currency': data.get('currency', 'TRY'),
        'updated_at': firestore.SERVER_TIMESTAMP,
        'updated_by': session.get('admin_email', 'unknown'),
    })
    
    # Admin log
    db.collection('admin_logs').add({
        'action': 'pricing_update',
        'adminEmail': session.get('admin_email'),
        'details': {'daily': daily, 'monthly': monthly, 'yearly': yearly},
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    
    logger.info(f"Pricing updated by {session.get('admin_email')}: daily={daily}, monthly={monthly}, yearly={yearly}")
    
    return jsonify({
        'success': True,
        'message': 'Fiyatlar başarıyla güncellendi!'
    })


# ═══════════════════════════════════════════════════════════════
# AI PROVIDER AYARLARI
# ═══════════════════════════════════════════════════════════════

@admin_bp.route('/api/ai-settings', methods=['GET'])
@admin_required
@handle_errors("AI ayarları alınamadı")
def get_ai_settings():
    """Firestore'dan AI provider ayarlarını getir"""
    db = firebase_service.db
    if not db:
        return jsonify({
            'success': False,
            'error': 'DATABASE_UNAVAILABLE',
            'message': 'Firebase bağlantısı yok'
        }), 500

    doc = db.collection('config').document('ai_settings').get()

    if doc.exists:
        data = doc.to_dict()
        return jsonify({
            'success': True,
            'data': data
        })

    # Varsayılan
    return jsonify({
        'success': True,
        'data': {
            'providers': [],
            'active_provider': '',
            'backup_1': '',
            'backup_2': '',
            'backup_3': '',
        }
    })


@admin_bp.route('/api/ai-settings', methods=['POST'])
@admin_required
@handle_errors("AI ayarları güncellenemedi")
def update_ai_settings():
    """Firestore'a AI provider ayarlarını kaydet"""
    data = request.get_json() or {}
    db = firebase_service.db
    if not db:
        return jsonify({
            'success': False,
            'error': 'DATABASE_UNAVAILABLE',
            'message': 'Firebase bağlantısı yok'
        }), 500

    from datetime import datetime
    from firebase_admin import firestore

    providers = data.get('providers', [])
    active_provider = (data.get('active_provider') or '').strip()
    # Eğer aktif seçilmemişse ama provider varsa ilkini aktif yap
    if not active_provider and providers:
        active_provider = (providers[0].get('name') or '').strip()

    doc_data = {
        'providers': providers,
        'active_provider': active_provider,
        'backup_1': (data.get('backup_1') or '').strip(),
        'backup_2': (data.get('backup_2') or '').strip(),
        'backup_3': (data.get('backup_3') or '').strip(),
        'updated_at': firestore.SERVER_TIMESTAMP,
        'updated_by': session.get('admin_email', 'unknown'),
    }

    db.collection('config').document('ai_settings').set(doc_data)

    # Admin log
    db.collection('admin_logs').add({
        'action': 'ai_settings_update',
        'adminEmail': session.get('admin_email'),
        'details': {'active_provider': active_provider},
        'timestamp': firestore.SERVER_TIMESTAMP
    })

    logger.info(f"AI settings updated by {session.get('admin_email')}: active={active_provider}")

    return jsonify({
        'success': True,
        'message': 'AI yapılandırması başarıyla güncellendi!'
    })


@admin_bp.route('/api/ai-settings/test', methods=['POST'])
@admin_required
@handle_errors("AI test başarısız")
def test_ai_provider():
    """Provider'ı test et - basit bir API çağrısı yap"""
    data = request.get_json() or {}
    base_url = (data.get('base_url') or '').strip().rstrip('/')
    api_key = (data.get('api_key') or '').strip()
    model = (data.get('model') or '').strip()
    name = (data.get('name') or 'Test').strip()

    if not api_key:
        return jsonify({'success': False, 'error': 'API Key gerekli'}), 400

    # base_url normalizasyonu: chat/completions çift eklenmesini önle
    if not base_url:
        url = "https://api.openai.com/v1/chat/completions"
    elif base_url.endswith('/chat/completions'):
        url = base_url
    elif base_url.endswith('/v1'):
        url = f"{base_url}/chat/completions"
    else:
        url = f"{base_url}/chat/completions"

    import aiohttp
    import asyncio

    async def test():
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        # Test icin yeterli token ve anlamli prompt
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Kisa cevap ver."},
                {"role": "user", "content": "1+1 kac eder?"}
            ],
            "max_tokens": 50,
            "temperature": 0.1,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    raw_text = await resp.text()
                    if resp.status == 200:
                        try:
                            res_json = json.loads(raw_text)
                            # Farkli API formatlarini dene
                            content = ""
                            choices = res_json.get('choices', [])
                            if choices:
                                msg = choices[0].get('message', {}) or choices[0].get('delta', {})
                                content = msg.get('content', '')
                            if not content:
                                content = res_json.get('response', '') or res_json.get('text', '')
                            if not content:
                                content = f"Yanit alindi (format: {list(res_json.keys())[:3]})"
                            return {'success': True, 'response': content.strip(), 'status': resp.status}
                        except json.JSONDecodeError:
                            # Bazi API'ler duz text doner
                            return {'success': True, 'response': raw_text[:200], 'status': resp.status, 'format': 'raw_text'}
                    else:
                        return {'success': False, 'error': f'HTTP {resp.status}: {raw_text[:200]}'}
        except asyncio.TimeoutError:
            return {'success': False, 'error': 'Timeout · 15sn'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:200]}

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(lambda: asyncio.run(test())).result(timeout=20)
        else:
            result = asyncio.run(test())
    except Exception as e:
        result = {'success': False, 'error': str(e)[:200]}

    logger.info(f"[AI Test] {name}: {'✅' if result.get('success') else '❌'} {result.get('error', '')}")
    return jsonify(result)


# ═══════════════════════════════════════════════════════════════
# CANLI METRIKLER - Son Login & Online Kullanicilar
# ═══════════════════════════════════════════════════════════════

@admin_bp.route('/api/stats/online', methods=['GET'])
@admin_required
@handle_errors("Online kullanicilar alinamadi")
def get_online_users():
    """Son 5 dakikada heartbeat atan kullanicilar"""
    from services.stats_counter import stats_counter
    users = stats_counter.get_online_users(within_minutes=5)
    return jsonify({
        'success': True,
        'data': {
            'online_count': len(users),
            'users': users,
        }
    })
