"""
Monetization API Routes
"""
import logging
from flask import Blueprint, request, jsonify
from monetization.usage_tracker import UsageTracker
from monetization.subscription import SubscriptionService

logger = logging.getLogger(__name__)

monetization_bp = Blueprint("monetization", __name__, url_prefix="/api/monetization")

usage_tracker = UsageTracker()
subscription_service = SubscriptionService()


def _verify_id_token(req):
    """Firebase ID token verify et → uid. Fail-closed: hata → 401."""
    auth = req.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None, ('missing Bearer token', 401)
    token = auth[len('Bearer '):]
    try:
        from firebase_admin import auth as fb_auth
        decoded = fb_auth.verify_id_token(token)
        return decoded['uid'], None
    except Exception as e:
        logger.warning(f"[monetization] verify_id_token failed: {e}")
        return None, ('invalid token', 401)

def _optional_email_from_token(req):
    """Bearer token varsa Firebase user email'ini server-side al.
    Client-supplied email override güvenlik açığı — admin bypass önlem.
    Token yoksa None (device_id fallback yine çalışır, ama email-bazlı admin bypass yok)."""
    auth = req.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[len('Bearer '):]
    try:
        from firebase_admin import auth as fb_auth
        decoded = fb_auth.verify_id_token(token)
        return decoded.get('email')
    except Exception as e:
        logger.debug(f"[monetization] optional email token failed: {e}")
        return None


@monetization_bp.route("/check-usage", methods=["POST"])
def check_usage():
    """Kullanıcının kullanım durumunu kontrol et.
    Email: Bearer token varsa server-side Firebase user email; yoksa client-supplied
    yalnızca gösterim amaçlı — admin bypass yalnızca ADMIN_EMAILS env ile, token email'i."""
    data = request.get_json()
    device_id = data.get("device_id")
    email = _optional_email_from_token(request) or data.get("email")

    if not device_id:
        return jsonify({"error": "device_id gerekli"}), 400

    usage = usage_tracker.get_user_usage(device_id, email)
    can_use = usage_tracker.can_use_feature(device_id, email=email)

    return jsonify({
        "usage": usage,
        "can_use": can_use,
        "show_ads": usage.get("show_ads", True)
    })

@monetization_bp.route("/record-usage", methods=["POST"])
def record_usage():
    """Kullanımı kaydet. Email token'dan tercih edilir (admin bypass güvenliği)."""
    data = request.get_json()
    device_id = data.get("device_id")
    feature = data.get("feature", "interpretation")
    email = _optional_email_from_token(request) or data.get("email")

    if not device_id:
        return jsonify({"error": "device_id gerekli"}), 400

    result = usage_tracker.record_usage(device_id, feature, email)
    return jsonify(result)

@monetization_bp.route("/plans", methods=["GET"])
def get_plans():
    """Abonelik planlarını getir"""
    plans = subscription_service.get_plans()
    return jsonify({"success": True, "data": plans})

@monetization_bp.route("/verify-purchase", methods=["POST"])
def verify_purchase():
    """Google Play satın alma doğrula — Firebase ID token zorunlu."""
    uid, err = _verify_id_token(request)
    if err:
        return jsonify({"error": err[0]}), err[1]

    data = request.get_json()
    purchase_token = data.get("purchaseToken") or data.get("purchase_token")
    product_id = data.get("productId") or data.get("product_id")

    if not all([purchase_token, product_id]):
        return jsonify({"error": "Eksik parametreler"}), 400

    result = usage_tracker.verify_purchase(uid, purchase_token, product_id)
    return jsonify(result)

@monetization_bp.route("/premium-status", methods=["POST"])
def premium_status():
    """Premium durumunu kontrol et.
    Email: Bearer token'dan server-side (admin bypass güvenliği); client-supplied fallback."""
    data = request.get_json()
    device_id = data.get("device_id")
    email = _optional_email_from_token(request) or data.get("email")

    if not device_id:
        return jsonify({"error": "device_id gerekli"}), 400

    usage = usage_tracker.get_user_usage(device_id, email)
    return jsonify({
        "is_premium": usage["is_premium"],
        "is_admin": usage.get("is_admin", False),
        "premium_until": usage["premium_until"],
        "show_ads": usage.get("show_ads", True)
    })
