# ORBIS APP — Push Komutları

Bu repo'ya push'lamak için aşağıdaki adımları sırayla takip et.

## 0) Önce GitHub'da Yeni Repo Oluştur

`https://github.com/Optimus825482/orbisapp` → Settings → **Visibility: Private** ✅ (production'da public olabilir, ama secret'ler .env'de olduğu için yine de private önerilir)

## 1) Lokalde Repo Başlat + Commit

Terminal: `cmd.exe` veya PowerShell, `D:\astro-ai-predictor\separate-repos\orbisapp\` dizinine geç:

```bash
cd D:\astro-ai-predictor\separate-repos\orbisapp

# 1) Git başlat
git init -b main

# 2) .gitignore ve .gitattributes hazırla
# (zaten eklenmiş)

# 3) Remote ekle
git remote add origin https://github.com/Optimus825482/orbisapp.git

# 4) İlk commit
git add .
git status    # kontrol: gizli dosya (.env, .jks, *_adminsdk*.json) OLMAMALI
git commit -m "feat(app): initial commit — ORBIS Flask backend + PWA + admin panel

- Python 3.13 + Flask 3 + Redis + Firestore
- Mobile WebView paylaşımlı: mobile-bridge.js, firebase-config.js, admob-config.js, analytics.js
- Admin panel: impeccable design system (OKLCH, dark/light, design tokens)
- Dashboard: KPI + 4 charts + AdMob + activity feed
- Admin PWA: manifest + service worker + offline
- Monetization: IAP verify (Google Play), usage tracking, premium gating
- Push notification: FCM subscribe with premium check
- Firebase Admin SDK + Google Play Developer API
- Google Analytics 4 + AdMob API integration
- Keyboard shortcuts, theme toggle (light/dark)
- KVKK cookie consent for GA4 tracking"

# 5) Push
git push -u origin main
```

## 2) GitHub'da Repo Ayarları

Push sonrası `https://github.com/Optimus825482/orbisapp/settings`:

### Branch protection (main)
- Settings → Branches → Add rule
- Branch name pattern: `main`
- ☑ Require a pull request before merging
- ☑ Require approvals: 1 (sen onaylarsın)
- ☑ Dismiss stale pull requests
- ☐ Allow force pushes: NO

### Secrets (CI yok, deploy Coolify'dan)
Şu an bu repo için GitHub Actions CI'a gerek yok — Coolify web hook ile push'ta deploy tetikleniyor.

Ama `orbis-mobile` repo'su için (Plan 7) şu secret'lar gerek:
- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_PASSWORD`
- `GOOGLE_SERVICES_JSON`
- `ORBISAPP_PAT` (orbisapp'den shared JS çekmek için)
- `GA4_MEASUREMENT_ID`
- `PLAY_SERVICE_ACCOUNT_KEY`

### Topics (keşfedilebilirlik)
Repo sayfasında ⚙️ → Topics:
`flask`, `python`, `firebase`, `pwa`, `astrology`, `ai`, `admin`, `coolify`, `capacitor`

## 3) Coolify'a Webhook Ekle (otomatik deploy)

Coolify → `orbisapp` projesi → **Webhooks** sekmesi:

GitHub'dan → Coolify'ın verdiği webhook URL'i kopyala (örn. `https://coolify.com/api/v1/webhooks/...`).

GitHub → `orbisapp` repo → **Settings** → **Webhooks** → **Add webhook**:
- Payload URL: Coolify'ın webhook URL'i
- Content type: `application/json`
- Events: ☑ **Just the push event**
- Active: ✅

Push → Coolify otomatik build alır.

## 4) Coolify'da Source Güncelle (Eğer Henüz Yapılmadıysa)

Coolify → `orbisapp` → **Source**:
- Type: **Public/Private Repository**
- Repository: `Optimus825482/orbisapp`
- Branch: `main`
- **Save** → Coolify'ın GitHub deploy key'ini al

GitHub'da:
- Repo → Settings → **Deploy keys** → **Add deploy key**
- Title: `Coolify orbisapp`
- Key: Coolify'ın verdiği public SSH key
- ☑ Allow write access (NO — read-only)
- Add

## 5) Coolify'da Env Variables (Geri Kalanlar)

Coolify → `orbisapp` → **Environment Variables** → henüz set etmediysen:

```
GA4_MEASUREMENT_ID=G-PLJEZCGT27BU
GA4_PROPERTY_ID=123456789
GA4_SERVICE_ACCOUNT_JSON={"type":"service_account",...}  # JSON içerik
ADMOB_CLIENT_ID=xxx.apps.googleusercontent.com
ADMOB_CLIENT_SECRET=GOCSPX-xxx
ADMOB_REFRESH_TOKEN=1//0e-xxx
ADMOB_PUBLISHER_ID=pub-2444093901783574
# Diğer env'ler (OPENAI, DEEPSEEK, vs.) zaten mevcut
```

**Save** + **Redeploy**.

## 6) İlk Deploy Sonrası Doğrula

```bash
# VPS'te
ssh user@vps
cd /path/to/orbisapp
python3 scripts/validate-credentials.py
```

✅ Tüm credentials hazırsa admin dashboard'da GA4 + AdMob verileri görünür.

## 7) İlk Admin Claim Atama

```bash
# VPS'te
python3 scripts/set-admin.sh admin@orbisastro.online
```

## 8) Firestore Rules Deploy

```bash
# Lokalde
cd D:\astro-ai-predictor\separate-repos\orbisapp
firebase login
firebase use orbis-ffa9e
bash scripts/deploy-firestore-rules.sh
```

## 9) Domain'i Coolify'a Bağla

Coolify → `orbisapp` → **Domains**:
- Add: `app.orbisastro.online`
- Coolify otomatik Let's Encrypt SSL alır
- Cloudflare DNS: `app` CNAME → Coolify sunucu IP

## 10) Mobile CI İçin orbis-mobile Repo Hazırla

`orbis-mobile/.github/workflows/build-mobile.yml` dosyasını `D:\astro-ai-predictor\separate-repos\orbis-app-workflows\build-mobile.yml`'den kopyala (zaten yazdık).

---

## 🆘 Sorun Giderme

| Hata | Çözüm |
|---|---|
| `git push rejected: non-fast-forward` | `git pull --rebase origin main` sonra push |
| `Permission denied (publickey)` | Coolify deploy key'i GitHub'a ekle |
| `large files detected` | .gitignore'a büyük asset ekle (mp4, icons) |
| Admin panel 500 hatası | Log kontrol: `docker logs orbisapp-...` |
| GA4 verisi boş | `validate-credentials.py` çalıştır, JSON env kontrol |

---

## Sonraki: orbis-landing

Aynı adımlar — bu sefer dosyalar `D:\astro-ai-predictor\separate-repos\orbis-landing\`'da, GitHub repo `https://github.com/Optimus825482/orbis-landing.git`.
