#!/usr/bin/env python
"""
ORBIS — AdMob OAuth2 refresh token alma (one-time).

Google API Console'daki OAuth2 client (Desktop app) için refresh token üretir.
.env'deki ADMOB_REFRESH_TOKEN alanına yazılır.

Önce: https://console.cloud.google.com/apis/credentials
  1. OAuth consent screen → External → ORBIS Admin
  2. Scope: https://www.googleapis.com/auth/admob.readonly
  3. + Credentials → OAuth client ID → Desktop app
  4. Client ID + Client Secret'i kopyala

Usage:
    pip install google-auth-oauthlib
    python scripts/get_admob_token.py
"""
import os
import sys

CLIENT_ID = os.environ.get('ADMOB_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('ADMOB_CLIENT_SECRET', '')

if not CLIENT_ID or not CLIENT_SECRET:
    print('HATA: ADMOB_CLIENT_ID ve ADMOB_CLIENT_SECRET env değişkenlerini set et,')
    print('       veya aşağıdaki kodu kendi değerlerinle düzenle.')
    sys.exit(1)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print('HATA: pip install google-auth-oauthlib')
    sys.exit(1)

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8089"],
        }
    },
    scopes=["https://www.googleapis.com/auth/admob.readonly"],
)

print('Tarayıcı açılacak — Google hesabınla giriş yap ve izin ver...')
creds = flow.run_local_server(port=8089, open_browser=True)

print('\n' + '=' * 60)
print('BAŞARILI! Aşağıdaki değerleri .env dosyana ekle:')
print('=' * 60)
print(f'\nADMOB_REFRESH_TOKEN={creds.refresh_token}\n')
print('=' * 60)
print('NOT: Refresh token kalıcıdır (iptal edilene kadar).')
print('     Bu scripti tekrar çalıştırmana gerek yok.')
print('=' * 60)
