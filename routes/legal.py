"""
ORBIS Legal Routes
Gizlilik Politikası, Kullanım Şartları ve diğer yasal sayfalar
"""

from flask import Blueprint, render_template

legal_bp = Blueprint('legal', __name__, url_prefix='/legal')


@legal_bp.route('/privacy-policy')
@legal_bp.route('/privacy')
@legal_bp.route('/gizlilik')
def privacy_policy():
    """Gizlilik Politikası sayfası"""
    return render_template('legal/privacy-policy.html')


@legal_bp.route('/terms-of-service')
@legal_bp.route('/terms')
@legal_bp.route('/kullanim-sartlari')
def terms_of_service():
    """Kullanım Şartları sayfası"""
    return render_template('legal/terms-of-service.html')


@legal_bp.route('/kvkk')
@legal_bp.route('/gdpr')
def data_protection():
    """KVKK/GDPR Aydınlatma Metni"""
    return render_template('legal/kvkk.html')


@legal_bp.route('/cookie-policy')
@legal_bp.route('/cerez-politikasi')
def cookie_policy():
    """Çerez Politikası"""
    return render_template('legal/cookie-policy.html')
