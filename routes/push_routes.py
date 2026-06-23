"""
ORBIS Push Notification Routes
FCM token kaydetme ve push gönderme endpoint'leri.
Auth: topic subscribe/unsubscribe Firebase ID token gerekir; premium_users topic için
server-side premium check. register-token opsiyonel auth (public kayıt).
"""

from flask import Blueprint, request, jsonify
from services.firebase_service import firebase_service
import os
import logging

logger = logging.getLogger(__name__)

push_bp = Blueprint('push', __name__, url_prefix='/api')


def _verify_id_token(req):
    """Firebase ID token verify et, uid döndür. Fail-closed: hata → 401."""
    auth = req.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None, ('missing Bearer token', 401)
    token = auth[len('Bearer '):]
    try:
        from firebase_admin import auth as fb_auth
        decoded = fb_auth.verify_id_token(token)
        return decoded['uid'], None
    except Exception as e:
        logger.warning(f"[Push] verify_id_token failed: {e}")
        return None, ('invalid token', 401)


def _is_premium(uid):
    """Server-side premium check Admin SDK ile (read-only)."""
    try:
        doc = firebase_service.db.collection('users').document(uid).get()
        if doc.exists:
            return bool(doc.to_dict().get('isPremium'))
    except Exception as e:
        logger.warning(f"[Push] premium check failed: {e}")
    return False


def _token_belongs(uid, token):
    """Token sahipliği: users/{uid}.fcmTokens içinde mi?"""
    try:
        doc = firebase_service.db.collection('users').document(uid).get()
        if doc.exists:
            tokens = doc.to_dict().get('fcmTokens', [])
            return any(t.get('token') == token for t in tokens if isinstance(t, dict))
    except Exception as e:
        logger.warning(f"[Push] token ownership check failed: {e}")
    return False


@push_bp.route('/fcm/register', methods=['POST'])
@push_bp.route('/push/register-token', methods=['POST'])
def register_token():
    """FCM token kaydet — Firebase ID token zorunlu.
    userId client-supplied DEĞİL, token'dan türetilir (token impersonation önlem).
    register-token sadece herkese açık topic'lere (all_users/daily/weekly) abone;
    premium_users topic premium check'li subscribe-topic ile ayrılır."""
    uid, err = _verify_id_token(request)
    if uid is None:
        # Geriye uyumlu: token olmadan sadece public topic aboneliğine izin ver
        # ama user doc'a kayıt YAPMA — sahiplilik doğrulanmadan.
        data = request.get_json(silent=True) or {}
        token = data.get('token')
        if not token:
            return jsonify({'success': False, 'error': 'token gerekli'}), 400
        allowed_public = ['all_users', 'daily_horoscope', 'weekly_horoscope']
        topics = [t for t in data.get('topics', ['all_users']) if t in allowed_public]
        subbed = []
        for topic in topics:
            if firebase_service.subscribe_to_topic([token], topic):
                subbed.append(topic)
        return jsonify({
            'success': True,
            'authenticated': False,
            'message': 'Public topic aboneliği (kayıtsız)',
            'subscribedTopics': subbed,
        })

    data = request.get_json()
    token = data.get('token')
    platform = data.get('platform', 'android')
    # premium_users hariç — premium check subscribe-topic'te
    topics = [t for t in data.get('topics', ['all_users']) if t != 'premium_users']

    if not token:
        return jsonify({'success': False, 'error': 'token gerekli'}), 400

    # uid token'dan — client-supplied userId güvenilmez, yok say.
    firebase_service.save_fcm_token(uid, token, platform)

    subscribed_topics = []
    allowed_topics = ['all_users', 'daily_horoscope', 'weekly_horoscope']

    for topic in topics:
        if topic in allowed_topics:
            success = firebase_service.subscribe_to_topic([token], topic)
            if success:
                subscribed_topics.append(topic)

    return jsonify({
        'success': True,
        'authenticated': True,
        'message': 'Token kaydedildi',
        'subscribedTopics': subscribed_topics
    })


@push_bp.route('/push/subscribe-topic', methods=['POST'])
def subscribe_topic():
    """Topic'e abone et — auth zorunlu. premium_users için server-side premium check."""
    uid, err = _verify_id_token(request)
    if err:
        return jsonify({'success': False, 'error': err[0]}), err[1]

    data = request.get_json()
    token = data.get('token')
    topic = data.get('topic')

    if not token or not topic:
        return jsonify({'success': False, 'error': 'token ve topic gerekli'}), 400

    allowed_topics = ['all_users', 'daily_horoscope', 'weekly_horoscope', 'premium_users']
    if topic not in allowed_topics:
        return jsonify({'success': False, 'error': 'Geçersiz topic'}), 400

    # premium_users topic için server-side premium kontrol
    if topic == 'premium_users' and not _is_premium(uid):
        return jsonify({'success': False, 'error': 'Premium gerekli'}), 403

    # Token sahipliği — kullanıcı token'a sahip olmalı
    if not _token_belongs(uid, token):
        return jsonify({'success': False, 'error': 'Token sahipliği doğrulanamadı'}), 403

    success = firebase_service.subscribe_to_topic([token], topic)
    return jsonify({
        'success': success,
        'message': f"{topic} topic'ine abone olundu" if success else 'Abone olunamadı'
    })


@push_bp.route('/push/unsubscribe-topic', methods=['POST'])
def unsubscribe_topic():
    """Topic'ten çıkar — auth zorunlu, sahiplilik kontrolü."""
    uid, err = _verify_id_token(request)
    if err:
        return jsonify({'success': False, 'error': err[0]}), err[1]

    data = request.get_json()
    token = data.get('token')
    topic = data.get('topic')

    if not token or not topic:
        return jsonify({'success': False, 'error': 'token ve topic gerekli'}), 400

    if not _token_belongs(uid, token):
        return jsonify({'success': False, 'error': 'Token sahipliği doğrulanamadı'}), 403

    success = firebase_service.unsubscribe_from_topic([token], topic)
    return jsonify({'success': success})