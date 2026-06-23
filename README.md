# ORBIS APP — Flask Backend + PWA Web

**Domain:** `app.orbisastro.online`
**Coolify Proje:** #2
**Repo tipi:** Tek başına Flask backend, PWA web client, admin paneli

## Stack
- Python 3.13 + Flask 3
- Redis (session + cache)
- Firestore (user data, premium state)
- FCM (push)
- Google Play Developer API (IAP verify)
- Stripe/Coolify (hosting)

## Geliştirme

```bash
# Local
python -m venv env
source env/bin/activate
pip install -r requirements.txt
cp env.example .env  # düzenle
python app.py
# http://localhost:5000
```

## Deploy (Coolify)
- Source: `https://github.com/Optimus825482/orbisapp.git`
- Branch: `main`
- Build: Dockerfile (python:3.13-slim + gunicorn)
- Domain: `app.orbisastro.online`

## Endpoint'ler
- `GET  /` → Landing redirect (login/dashboard)
- `GET  /dashboard` → Ana PWA
- `POST /api/monetization/verify-purchase` → Firebase ID token auth
- `POST /api/monetization/check-usage` → Opsiyonel Bearer, client device_id
- `POST /api/push/subscribe-topic` → Firebase ID token + premium check
- `POST /api/admin/*` → Admin panel (subdomain `admin.orbisastro.online`)

## Shared JS (mobile ile)
`static/js/{mobile-bridge,firebase-config,admob-config}.js` mobile WebView ile paylaşılır.
Source of truth: bu repo. `scripts-shared/sync-shared-js.sh` orbis-mobile CI'ında koşar.

## Mimari Detay
Bkz: `../ARCHITECTURE.md` (ana proje kökünde)

## Secrets (Coolify mount)
- `firebase-adminsdk.json` → `/secrets/firebase-adminsdk.json`
- `play-service-account.json` → `/secrets/play-service-account.json`
- `.env` (Coolify UI'dan, env.example baz alınır)
