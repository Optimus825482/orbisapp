#!/usr/bin/env python
"""
ORBIS Credentials Validator
.env'de credential'ların doğru set edilip edilmediğini kontrol eder.
Hangi endpoint'lerin çalışıp hangilerinin boş döneceğini söyler.

Kullanım:
    python scripts/validate-credentials.py
"""
import os
import sys
import json
from pathlib import Path

# .env dosyasını yükle (varsa)
ENV_PATH = Path(__file__).resolve().parent.parent / '.env'
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def status(label, value, ok, hint=''):
    icon = '✅' if ok else '⚠️ '
    val = value if value else '(tanımsız)'
    print(f'  {icon} {label}: {val}')
    if hint and not ok:
        print(f'      → {hint}')
    return ok


def file_status(label, path, ok, hint=''):
    icon = '✅' if ok else '⚠️ '
    if path and Path(path).exists():
        size = Path(path).stat().st_size
        return status(label, f'{path} ({size} bytes)', True)
    return status(label, path or '(tanımsız)', False, hint)


def main():
    print('══════════════════════════════════════════════════════════════')
    print('  ORBIS Credentials Validator')
    print('══════════════════════════════════════════════════════════════')
    print()

    all_ok = True

    # ── 1. GA4 Web Tracking ──
    print('[1] Google Analytics 4 — Web Tracking')
    all_ok &= status(
        'GA4_MEASUREMENT_ID',
        os.environ.get('GA4_MEASUREMENT_ID', ''),
        bool(os.environ.get('GA4_MEASUREMENT_ID', '').startswith('G-')),
        'https://analytics.google.com/ → Yönetici → Veri akışları'
    )
    print()

    # ── 2. GA4 Admin Dashboard ──
    print('[2] GA4 Admin Dashboard Data')
    all_ok &= status(
        'GA4_PROPERTY_ID',
        os.environ.get('GA4_PROPERTY_ID', ''),
        os.environ.get('GA4_PROPERTY_ID', '').isdigit(),
        'analytics.google.com → Yönetici → Mülk bilgileri'
    )
    all_ok &= file_status(
        'GA4_SERVICE_ACCOUNT_PATH',
        os.environ.get('GA4_SERVICE_ACCOUNT_PATH', ''),
        Path(os.environ.get('GA4_SERVICE_ACCOUNT_PATH', '')).exists() if os.environ.get('GA4_SERVICE_ACCOUNT_PATH') else False,
        'VPS\'e service account JSON upload et, Coolify Directories\'a mount et (ya da GA4_SERVICE_ACCOUNT_JSON env ile gönder)'
    )
    all_ok &= status(
        'GA4_SERVICE_ACCOUNT_JSON',
        '***' + os.environ.get('GA4_SERVICE_ACCOUNT_JSON', '')[-30:] if os.environ.get('GA4_SERVICE_ACCOUNT_JSON') else '',
        bool(os.environ.get('GA4_SERVICE_ACCOUNT_JSON', '')),
        'JSON dosyanın içeriğini raw paste (tek satır)'
    )
    print()

    # ── 3. AdMob API ──
    print('[3] AdMob API (Admin)')
    all_ok &= status(
        'ADMOB_CLIENT_ID',
        os.environ.get('ADMOB_CLIENT_ID', '')[:30] + '...' if os.environ.get('ADMOB_CLIENT_ID') else '',
        bool(os.environ.get('ADMOB_CLIENT_ID', '').endswith('.apps.googleusercontent.com')),
        'console.cloud.google.com/apis/credentials → OAuth client ID'
    )
    all_ok &= status(
        'ADMOB_CLIENT_SECRET',
        '***' + os.environ.get('ADMOB_CLIENT_SECRET', '')[-6:] if os.environ.get('ADMOB_CLIENT_SECRET') else '',
        bool(os.environ.get('ADMOB_CLIENT_SECRET', '')),
        'OAuth client secret'
    )
    all_ok &= status(
        'ADMOB_REFRESH_TOKEN',
        '1//0e...' if os.environ.get('ADMOB_REFRESH_TOKEN', '').startswith('1//') else '',
        os.environ.get('ADMOB_REFRESH_TOKEN', '').startswith('1//'),
        'python scripts/get_admob_token.py'
    )
    all_ok &= status(
        'ADMOB_PUBLISHER_ID',
        os.environ.get('ADMOB_PUBLISHER_ID', ''),
        os.environ.get('ADMOB_PUBLISHER_ID', '').startswith('pub-'),
        'admob.google.com → Ayarlar → Publisher info'
    )
    print()

    # ── 4. Firebase ──
    print('[4] Firebase Admin SDK')
    fb_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', '/app/firebase-credentials.json')
    all_ok &= file_status(
        'FIREBASE_CREDENTIALS_PATH',
        fb_path,
        Path(fb_path).exists() if fb_path else False,
        'Coolify Directories mount: /app/firebase-credentials.json'
    )
    print()

    # ── Sonuç ──
    print('══════════════════════════════════════════════════════════════')
    if all_ok:
        print('  ✅ Tüm credentials hazır — production ready!')
    else:
        print('  ⚠️  Bazı credentials eksik. Uygulama çalışır (boş veri döner),')
        print('     ama admin dashboard\'da GA4/AdMob verileri görünmez.')
    print('══════════════════════════════════════════════════════════════')
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
