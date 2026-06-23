#!/usr/bin/env python
"""
ORBIS — Admin custom claim atama scripti (one-time).

Firebase Auth kullanıcısına `admin: True` custom claim ekler.
Firestore rules'taki `request.auth.token.admin == true` kontrolü için.

Usage:
    # Tek UID
    python scripts/set_admin_claim.py --uid <USER_UID>

    # Email ile (UID otomatik bulunur)
    python scripts/set_admin_claim.py --email admin@orbisastro.online

    # Çoklu (virgülle)
    python scripts/set_admin_claim.py --email admin@orbisastro.online,owner@orbisastro.online

    # Admin listesini gör
    python scripts/set_admin_claim.py --list

    # Claim'i kaldır
    python scripts/set_admin_claim.py --uid <USER_UID> --remove

Gereksinim:
    - FIREBASE_CREDENTIALS_PATH veya /app/firebase-credentials.json
    - firebase-admin (pip install firebase-admin)
"""
import os
import sys
import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('admin-claim')


def init_firebase():
    """Firebase Admin SDK başlat (env example ile)."""
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.error('firebase-admin gerekli: pip install firebase-admin')
        sys.exit(1)

    cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', '/app/firebase-credentials.json')
    if not os.path.exists(cred_path):
        logger.error('Firebase credentials bulunamadı: %s', cred_path)
        logger.error('FIREBASE_CREDENTIALS_PATH env veya /app/firebase-credentials.json')
        sys.exit(1)

    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    except ValueError:
        # Zaten başlatılmış olabilir
        pass
    return firebase_admin


def find_uid_by_email(fb, email):
    """Email ile UID bul."""
    from firebase_admin import auth
    try:
        user = auth.get_user_by_email(email)
        return user.uid
    except auth.UserNotFoundError:
        logger.error('Kullanıcı bulunamadı: %s', email)
        return None


def set_admin(fb, uid, is_admin=True):
    """Custom claim set/remove."""
    from firebase_admin import auth
    user = auth.get_user(uid)
    current_claims = user.custom_claims or {}
    if is_admin:
        current_claims['admin'] = True
    else:
        current_claims.pop('admin', None)
    auth.set_custom_user_claims(uid, current_claims)
    return user


def list_admins(fb):
    """Admin claim'li kullanıcıları listele."""
    from firebase_admin import auth
    count = 0
    for user in auth.list_users().iterate_all():
        if (user.custom_claims or {}).get('admin'):
            print(f'  • {user.email or "(no email)"} — uid={user.uid}')
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description='ORBIS admin custom claim yönetimi')
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--uid', help='Tek UID')
    g.add_argument('--email', help='Email veya virgüllü ayrılmış email listesi')
    g.add_argument('--list', action='store_true', help='Admin claim\'li kullanıcıları listele')
    parser.add_argument('--remove', action='store_true', help='Admin claim kaldır')
    args = parser.parse_args()

    fb = init_firebase()

    if args.list:
        count = list_admins(fb)
        print(f'\n{count} admin kullanıcı bulundu.')
        return

    is_admin = not args.remove

    uids = []
    if args.uid:
        uids = [u.strip() for u in args.uid.split(',')]
    elif args.email:
        for email in [e.strip() for e in args.email.split(',')]:
            uid = find_uid_by_email(fb, email)
            if uid:
                uids.append(uid)

    if not uids:
        logger.error('Hiçbir UID bulunamadı.')
        sys.exit(1)

    for uid in uids:
        try:
            user = set_admin(fb, uid, is_admin)
            action = 'eklendi' if is_admin else 'kaldırıldı'
            logger.info('OK: %s — %s (uid=%s)', user.email, action, uid)
        except Exception as e:
            logger.error('Hata (uid=%s): %s', uid, e)


if __name__ == '__main__':
    main()
