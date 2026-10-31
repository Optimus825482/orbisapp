"""
Monetization API Routes - SADECE NATIVE (ANDROID) İÇİN
Premium/abonelik sistemi tamamen kaldırıldı.
Sadece native (Capacitor) istemcilerde reklam takibi yapılır.
PWA (web) istemcilerde bu endpoint'ler no-op döner — sınırsız erişim.
"""
import logging
from flask import Blueprint, request, jsonify
from monetization.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)

monetization_bp = Blueprint("monetization", __name__, url_prefix="/api/monetization")

usage_tracker = UsageTracker()


def _is_pwa_request() -> bool:
    """PWA (web) istemci mi tespit et. Capacitor header'ı yoksa PWA."""
    user_agent = request.headers.get('User-Agent', '').lower()
    client_platform = request.headers.get('X-Client-Platform', '').lower()
    is_pwa = (
        'capacitor' not in user_agent and
        client_platform != 'capacitor' and
        client_platform != 'native' and
        client_platform != 'android'
    )
    return is_pwa


@monetization_bp.route("/check-usage", methods=["POST"])
def check_usage():
    """Kullanıcının kullanım durumunu, Kozmik Kredi ve 24h Reklamsız Pass durumunu kontrol et."""
    data = request.get_json() or {}
    device_id = data.get("device_id")
    email = data.get("email")

    if _is_pwa_request():
        logger.info(f"[monetization] check-usage - PWA istemci, no-op (UA: {request.headers.get('User-Agent', '')[:50]})")
        return jsonify({
            "usage": {
                "is_premium": True,
                "is_admin": False,
                "remaining": "unlimited",
                "requires_ad": False,
                "show_ads": False,
                "cosmic_credits": 999,
                "is_ad_free": True
            },
            "can_use": {
                "allowed": True,
                "requires_ad": False,
                "remaining": "unlimited",
                "is_ad_free": True,
                "cosmic_credits": 999
            },
            "show_ads": False,
            "platform": "pwa",
            "message": "PWA istemci - sınırsız erişim"
        })

    if not device_id:
        return jsonify({"error": "device_id gerekli"}), 400

    usage = usage_tracker.get_user_usage(device_id, email)
    can_use = usage_tracker.can_use_feature(device_id, 'interpretation', email)

    return jsonify({
        "usage": usage,
        "can_use": can_use,
        "show_ads": usage.get("show_ads", True)
    })


@monetization_bp.route("/claim-reward", methods=["POST"])
def claim_reward():
    """Ödüllü reklam izlendikten sonra ödülü tanımla (credits veya ad_free_24h)."""
    data = request.get_json() or {}
    device_id = data.get("device_id")
    reward_type = data.get("reward_type", "credits")
    email = data.get("email")

    if not device_id:
        return jsonify({"error": "device_id gerekli"}), 400

    res = usage_tracker.claim_reward(device_id, reward_type, email)
    logger.info(f"[monetization] claim_reward - device_id: {device_id}, reward_type: {reward_type}, res: {res}")
    return jsonify(res)


@monetization_bp.route("/spend-credit", methods=["POST"])
def spend_credit():
    """Analiz veya özellik başlatırken Kozmik Kredi harca."""
    data = request.get_json() or {}
    device_id = data.get("device_id")
    amount = int(data.get("amount", 1))
    feature = data.get("feature", "analysis")
    email = data.get("email")

    if not device_id:
        return jsonify({"error": "device_id gerekli"}), 400

    res = usage_tracker.spend_credit(device_id, amount, feature, email)
    logger.info(f"[monetization] spend_credit - device_id: {device_id}, res: {res}")
    return jsonify(res)


@monetization_bp.route("/record-usage", methods=["POST"])
def record_usage():
    """Kullanımı kaydet (reklam izlendi).

    PWA (web) istemcilerde no-op — AdMob sadece native'de çalışır.
    """
    if _is_pwa_request():
        logger.info(f"[monetization] record-usage - PWA istemci, no-op")
        return jsonify({
            "success": True,
            "remaining": 999,
            "today_usage": 0,
            "platform": "pwa",
            "message": "PWA - reklam kaydedilmedi"
        })

    data = request.get_json() or {}
    device_id = data.get("device_id")
    feature = data.get("feature", "interpretation")
    email = data.get("email")

    if not device_id:
        return jsonify({"error": "device_id gerekli"}), 400

    result = usage_tracker.record_usage(device_id, feature, email)
    return jsonify(result)
