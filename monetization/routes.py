"""
Monetization API Routes - SADECE REKLAM TAKİBİ
Premium/abonelik sistemi tamamen kaldırıldı.
Tüm kullanıcılar ücretsiz, her analiz için rewarded ad zorunlu.
"""
import logging
from flask import Blueprint, request, jsonify
from monetization.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)

monetization_bp = Blueprint("monetization", __name__, url_prefix="/api/monetization")

usage_tracker = UsageTracker()


@monetization_bp.route("/check-usage", methods=["POST"])
def check_usage():
    """Kullanıcının kullanım durumunu kontrol et."""
    data = request.get_json()
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({"error": "device_id gerekli"}), 400

    usage = usage_tracker.get_user_usage(device_id)
    can_use = usage_tracker.can_use_feature(device_id)

    return jsonify({
        "usage": usage,
        "can_use": can_use,
        "show_ads": True
    })


@monetization_bp.route("/record-usage", methods=["POST"])
def record_usage():
    """Kullanımı kaydet (reklam izlendi)."""
    data = request.get_json()
    device_id = data.get("device_id")
    feature = data.get("feature", "interpretation")

    if not device_id:
        return jsonify({"error": "device_id gerekli"}), 400

    result = usage_tracker.record_usage(device_id, feature)
    return jsonify(result)
