"""
ORBIS Google Play Developer API wrapper.
Server-side satın alma token doğrulaması (fail-closed).
"""
import os
import logging

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/androidpublisher']
PACKAGE_NAME = 'com.orbisastro.orbis'


def _get_service():
    """Google Play Developer API servisi oluştur (lazy)."""
    path = os.getenv('PLAY_SERVICE_ACCOUNT_PATH')
    if not path:
        raise RuntimeError('PLAY_SERVICE_ACCOUNT_PATH env not set')
    if not os.path.exists(path):
        raise RuntimeError(f'Play service account file not found: {path}')

    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    return build('androidpublisher', 'v3', credentials=creds, cache_discovery=False)


def verify_purchase_token(purchase_token: str, product_id: str) -> dict:
    """
    Google Play subscription/product purchase token'ı server-side doğrula.
    Returns: {valid: bool, expiry_time: str|None, purchase_state: int|None}.
    Fail-closed: her hata → valid=False.
    """
    try:
        svc = _get_service()
        if product_id.endswith('_lifetime'):
            # Non-consumable / non-renewing product
            resp = svc.purchases().products().get(
                packageName=PACKAGE_NAME,
                productId=product_id,
                token=purchase_token,
            ).execute()
            state = resp.get('purchaseState', -1)
            # purchaseState 0 = Purchased
            return {
                'valid': state == 0,
                'expiry_time': resp.get('expiryTimeMillis'),
                'purchase_state': state,
            }
        else:
            # Subscription (renewing)
            resp = svc.purchases().subscriptions().get(
                packageName=PACKAGE_NAME,
                subscriptionId=product_id,
                token=purchase_token,
            ).execute()
            state = resp.get('paymentState', -1)
            # 1 = PaymentReceived, 2 = Pending
            return {
                'valid': state == 1,
                'expiry_time': resp.get('expiryTimeMillis'),
                'purchase_state': state,
            }
    except Exception:
        logger.exception('[GooglePlay] verify_purchase_token failed')
        return {'valid': False, 'expiry_time': None, 'purchase_state': -1}