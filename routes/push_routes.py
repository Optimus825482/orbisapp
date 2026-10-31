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
    """FCM token kaydet — Auth'lu kullanıcılar için user dokümanı ve push_subscribers,
    anonim/misafir kullanıcılar için push_subscribers koleksiyonuna kaydeder."""
    import hashlib
    from firebase_admin import firestore

    uid, err = _verify_id_token(request)
    data = request.get_json(silent=True) or {}
    token = data.get('token')
    platform = data.get('platform', 'web')

    if not token:
        return jsonify({'success': False, 'error': 'token gerekli'}), 400

    doc_id = hashlib.sha256(token.encode('utf-8')).hexdigest()[:32]

    if uid is None:
        # Anonim veya henüz giriş yapmamış kullanıcı
        allowed_public = ['all_users', 'daily_horoscope', 'weekly_horoscope']
        topics = [t for t in data.get('topics', ['all_users']) if t in allowed_public]
        subbed = []
        for topic in topics:
            if firebase_service.subscribe_to_topic([token], topic):
                subbed.append(topic)

        if firebase_service.db:
            try:
                firebase_service.db.collection('push_subscribers').document(doc_id).set({
                    'token': token,
                    'platform': platform,
                    'deviceId': data.get('device_id'),
                    'topics': subbed,
                    'userId': None,
                    'email': None,
                    'displayName': None,
                    'active': True,
                    'updatedAt': firestore.SERVER_TIMESTAMP,
                }, merge=True)
            except Exception as e:
                logger.warning(f"[Push] Error saving guest push subscriber: {e}")

        return jsonify({
            'success': True,
            'authenticated': False,
            'message': 'Cihaz bildirim aboneliği başarıyla kaydedildi',
            'subscribedTopics': subbed,
        })

    # Giriş yapmış kullanıcı
    topics = [t for t in data.get('topics', ['all_users']) if t != 'premium_users']

    # 1. users koleksiyonuna kaydet
    firebase_service.save_fcm_token(uid, token, platform)

    # 2. Topic abonelikleri
    subscribed_topics = []
    allowed_topics = ['all_users', 'daily_horoscope', 'weekly_horoscope']

    for topic in topics:
        if topic in allowed_topics:
            success = firebase_service.subscribe_to_topic([token], topic)
            if success:
                subscribed_topics.append(topic)

    # 3. push_subscribers koleksiyonuna kaydet (Admin listelemesi için)
    if firebase_service.db:
        try:
            user_doc = firebase_service.db.collection('users').document(uid).get()
            u_email = None
            u_name = None
            if user_doc.exists:
                udata = user_doc.to_dict() or {}
                u_email = udata.get('email')
                u_name = udata.get('displayName')

            firebase_service.db.collection('push_subscribers').document(doc_id).set({
                'token': token,
                'platform': platform,
                'deviceId': data.get('device_id'),
                'topics': subscribed_topics,
                'userId': uid,
                'email': u_email,
                'displayName': u_name,
                'active': True,
                'updatedAt': firestore.SERVER_TIMESTAMP,
            }, merge=True)
        except Exception as e:
            logger.warning(f"[Push] Error saving auth push subscriber: {e}")

    return jsonify({
        'success': True,
        'authenticated': True,
        'message': 'Token kaydedildi ve kullanıcıyla eşleştirildi',
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


@push_bp.route('/notifications/in-app', methods=['GET', 'POST'])
def get_in_app_notifications():
    """Kullanıcı için bekleyen uygulama içi (in-app) bildirimleri getirir ve okundu işaretler."""
    if not firebase_service.db:
        return jsonify({'success': False, 'notifications': []})

    user_id = request.args.get('userId') or request.args.get('uid')
    email = request.args.get('email')

    if not user_id and not email:
        uid, _ = _verify_id_token(request)
        user_id = uid

    if not user_id and not email:
        return jsonify({'success': True, 'notifications': []})

    notifications = []
    try:
        from firebase_admin import firestore
        db = firebase_service.db
        
        # 1. Doğrudan in_app_notifications koleksiyonu
        docs = []
        if user_id:
            docs = list(db.collection('in_app_notifications')
                        .where('userId', '==', user_id)
                        .where('read', '==', False)
                        .limit(5).stream())
        if not docs and email:
            docs = list(db.collection('in_app_notifications')
                        .where('email', '==', str(email).lower())
                        .where('read', '==', False)
                        .limit(5).stream())

        for d in docs:
            nd = d.to_dict() or {}
            notifications.append({
                'id': d.id,
                'title': nd.get('title'),
                'body': nd.get('body'),
                'data': nd.get('data', {}),
            })
            d.reference.update({'read': True, 'readAt': firestore.SERVER_TIMESTAMP})
    except Exception as e:
        logger.warning(f"[Push] In-app notifications fetch error: {e}")

    return jsonify({
        'success': True,
        'notifications': notifications
    })
