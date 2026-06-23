# ORBIS Production Setup Rehberi

Bu doküman tüm production credential'larını, nereden alınacağını, nereye ekleneceğini **tek tek** anlatır. Sırayla takip et.

**Toplam süre: 1-2 saat** (credential'ları toplamak için, çoğu adım 5-10 dk).

## 🚀 Quick Start (5 adım)

Sırasıyla:

```bash
# 1) VPS'te secrets dizinini hazırla + JSON dosyalarını yerleştir
#    (lokalde /tmp/'ye scp et, sonra VPS'te:)
ssh user@coolify-vps
bash setup-coolify-storage.sh

# 2) Coolify Directories tab'ında 3 satır ekle (script yazdıracak)
#    ... (script çıktısı zaten talimat veriyor)

# 3) Coolify → orbisapp → Environment Variables'a ekle:
#    GA4_MEASUREMENT_ID, GA4_PROPERTY_ID, GA4_SERVICE_ACCOUNT_PATH,
#    ADMOB_CLIENT_ID, ADMOB_CLIENT_SECRET, ADMOB_REFRESH_TOKEN, ADMOB_PUBLISHER_ID

# 4) Lokalde: Firestore rules deploy + admin claim atama
firebase login
bash scripts/deploy-firestore-rules.sh
bash scripts/set-admin.sh admin@orbisastro.online

# 5) Doğrula
python scripts/validate-credentials.py
```

---

## 0. Başlamadan Önce — Hesap Listesi

Şu hesaplara erişimin olmalı:

- [ ] **Google Analytics 4** — analytics.google.com (mülk ID alınacak)
- [ ] **Google Cloud Console** — console.cloud.google.com (service account + AdMob OAuth client)
- [ ] **Google AdMob** — admob.google.com (Publisher ID + OAuth user invite)
- [ ] **Firebase Console** — console.firebase.google.com (admin custom claim)
- [ ] **Coolify** — proje ayarları (env + storage mounts)
- [ ] **GitHub** — orbis-mobile repo Secrets (CI build için)

### Yardımcı Scriptler (`scripts/`)

| Script | Ne Yapar | Nerede |
|---|---|---|
| `setup-coolify-storage.sh` | VPS'te secrets klasörü oluşturur, JSON dosyalarını mount noktasına taşır | VPS'te çalıştır |
| `deploy-firestore-rules.sh` | Firebase rules + indexes deploy | Lokalde |
| `set-admin.sh` | Admin custom claim atar (email ile) | VPS veya lokal |
| `set_admin_claim.py` | Python claim script (set-admin.sh wrapper'ı) | VPS veya lokal |
| `get_admob_token.py` | AdMob OAuth2 refresh token üretir | Lokalde (tek seferlik) |
| `validate-credentials.py` | Tüm env'lerin doğru set edilip edilmediğini kontrol eder | VPS veya lokal |

---

## ADIM 1 — Google Analytics 4 (Web + Landing)

### 1a) Measurement ID al

1. https://analytics.google.com/ → **Yönetici** (⚙️)
2. **Hesap** sütununda: hesabını seç (yoksa oluştur)
3. **Mülk** sütununda: mülkünü seç (yoksa oluştur)
4. Sol menü: **Veri akışları** (Data Streams)
5. Mevcut **Web** akışı varsa tıkla → sağ üstte **Ölçüm Kimliği** (Measurement ID): `G-XXXXXXXXXX`
6. Yoksa: **Akış ekle** → **Web** → URL: `https://app.orbisastro.online` → akış adı: `ORBIS Web` → **Oluştur** → ID çıkar

**Format:** `G-` + 10 karakter (örn. `G-PLJEZCGT27BU`)

### 1b) Nereye ekle

| Konum | Değişken |
|---|---|
| Coolify → `orbisapp` → **Environment** | `GA4_MEASUREMENT_ID=G-XXXXXXXXXX` |
| Coolify → `orbis-landing` → **Build Args** | `GA4_MEASUREMENT_ID=G-XXXXXXXXXX` |

### Doğrulama

- `https://app.orbisastro.online` → DevTools → Network → `gtag/js?id=G-...` isteği
- analytics.google.com → **Raporlar** → **Realtime** → 1 aktif kullanıcı (kendin)

---

## ADIM 2 — GA4 Property ID + Service Account (Admin Dashboard)

### 2a) Property ID (numeric) bul

1. analytics.google.com → **Yönetici** → Mülk sütunu → mülkünü seç
2. Sol menü: **Mülk ayarları** → **Mülk bilgileri**
3. En üstte **Mülk Kimliği**: `123456789` (numeric, sadece rakam)

### 2b) Service Account JSON oluştur

1. https://console.cloud.google.com/iam-admin/serviceaccounts
2. Üstte proje seçici: **orbis-ffa9e** (Firebase projenle aynı)
3. **+ Service Account Oluştur**:
   - İsim: `ga4-reader`
   - ID: otomatik gelir
4. **Rol seç** → **Basic** → **Viewer** (veya custom: `roles/firebaseanalyticsviewer`)
5. **Bitti**
6. Listedeki `ga4-reader@orbis-ffa9e.iam.gserviceaccount.com` → ⋮ → **Anahtarları yönet** → **Anahtar ekle** → **Yeni anahtar** → **JSON** → **Oluştur**
7. `.json` dosyası iner — **güvenli yere kaydet** (örn. `~/.secrets/`)

### 2c) Service account'a GA4 Property erişimi ver

1. analytics.google.com → **Yönetici** → **Mülk erişim yönetimi**
2. **+** → **Kullanıcı ekle**
3. E-posta: `ga4-reader@orbis-ffa9e.iam.gserviceaccount.com`
4. Rol: **Görüntüleyici** → **Ekle**

### 2d) JSON dosyasını Coolify'a yükle — İKİ YOL VAR

#### Yol A) Env Variable (ÖNERİLEN — Coolify 4 Dockerfile modunda daha kolay)

Coolify → `orbisapp` → **Environment Variables** → yeni satır:

- **Key**: `GA4_SERVICE_ACCOUNT_JSON`
- **Value**: JSON dosyasının **tüm içeriğini tek satır olarak** yapıştır

Lokal makinede JSON'ı tek satıra çevir:
```bash
cat ~/Downloads/orbis-ffa9e-xxxxx.json | jq -c . > ga4-oneline.json
# Bu içeriği kopyala
```

Coolify **textarea**'ya yapıştır, **multiline destekler** (json ortasında \n olabilir, `services/google_analytics.py` `json.loads()` ile okur).

> ✅ Bu yol **restart-safe** (env kalıcı). Container restart'ta dosya kaybolmaz.

#### Yol B) VPS'te Dosya + Coolify Directories Mount (Eski yöntem)

Coolify 4'te **Dockerfile modunda** directory mount **yok** (Compose mode gerekir). Eğer mount istiyorsan: **docker-compose mode'a migrate et** veya Yol A'yı kullan.

Eğer yine de VPS'te dosya yöntemi:

```bash
# Lokalden VPS'e
scp ~/Downloads/orbis-ffa9e-xxxxx.json user@vps:/tmp/ga4-service-account.json

# VPS'te
ssh user@vps
mkdir -p /data/coolify/applications/df6f8aww5jif21e364yd0dtw/secrets
mv /tmp/ga4-service-account.json /data/coolify/applications/df6f8aww5jif21e364yd0dtw/secrets/ga4-service-account.json
chmod 600 /data/coolify/applications/df6f8aww5jif21e364yd0dtw/secrets/ga4-service-account.json
ls -la /data/coolify/applications/df6f8aww5jif21e364yd0dtw/secrets/
```

Coolify Dockerfile modda directory mount **yok**. Alternatifler:
- (1) **docker-compose mode'a migrate et** (Compose'da volume tanımla)
- (2) **Container'a `docker cp` ile kopyala** (restart'ta kaybolur)
- (3) **Yol A** (env variable) — kalıcı, önerilen

### 2e) Nereye ekle

Coolify → `orbisapp` → **Environment Variables**:

```
GA4_PROPERTY_ID=123456789
# YA: Dosya yolu (mount varsa)
GA4_SERVICE_ACCOUNT_PATH=/app/ga4-service-account.json
# YA: Env-JSON (ÖNERİLEN)
GA4_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"orbis-ffa9e",...}
```

**İkisini de set etmeyin** — biri yeterli. Kod `GA4_SERVICE_ACCOUNT_JSON` varsa onu kullanır, yoksa `GA4_SERVICE_ACCOUNT_PATH`'e bakar.

### Doğrulama

- Redeploy
- `https://app.orbisastro.online/admin/dashboard` aç
- Log'larda `[GA4] client init failed` yoksa OK
- `/admin/api/analytics/overview?range=7d` → 200 OK, JSON içinde `totalUsers, totalSessions` sayıları
- Veya: `python scripts/validate-credentials.py` çalıştır — ✅ veya ⚠️ gösterir

---

## ADIM 3 — Google AdMob API OAuth2 (Admin Reklam Raporları)

### 3a) OAuth consent screen + Client oluştur

1. https://console.cloud.google.com/apis/credentials
2. **+ Credentials Oluştur** → **OAuth client ID**
3. **Önce "Configure consent screen"**:
   - User Type: **External**
   - App name: `ORBIS Admin`
   - User support email: senin email
   - Developer email: senin email
   - **Save and Continue**
4. **Scopes** → **Add or Remove Scopes** → `https://www.googleapis.com/auth/admob.readonly` ekle → **Update** → **Save and Continue**
5. **Test users** → senin email → **Save and Continue** → **Back to Dashboard**
6. Şimdi tekrar **+ Credentials** → **OAuth client ID**:
   - Type: **Desktop app**
   - Name: `ORBIS Admin AdMob`
   - **Create**
7. Ekranda **Client ID** + **Client Secret** görünür → **ikisini de kopyala** (tekrar gösterilmez)

### 3b) Refresh Token al (OAuth2 flow)

```bash
# Lokalde
pip install google-auth-oauthlib

export ADMOB_CLIENT_ID="xxx.apps.googleusercontent.com"
export ADMOB_CLIENT_SECRET="GOCSPX-xxxxx"

python scripts/get_admob_token.py
```

Tarayıcı açılır → Google hesabınla giriş → "Allow" → Terminal'de:
```
ADMOB_REFRESH_TOKEN=1//0e-xxxxxx
```

**Bu değeri kopyala.**

### 3c) AdMob hesabında OAuth kullanıcısını yetkilendir

1. https://admob.google.com/ → ⚙️ → **Kullanıcılar** (veya **Team**)
2. **Kullanıcı ekle** → senin Google email → Rol: **Admin** veya **Reports** → **Davet et**
3. Email'ine gelen daveti kabul et

### 3d) AdMob Publisher ID bul

1. https://admob.google.com/ → sol menü **Uygulamalar** veya **Settings**
2. En üstte **Publisher ID**: `pub-XXXXXXXXXXXXXX`

### 3e) Service account JSON (AdMob publisher) — opsiyonel

AdMob API OAuth user bazlı çalışır, ayrı service account gerekmez. Bu adım **opsiyonel**.

### 3f) Nereye ekle

Coolify → `orbisapp` → **Environment Variables**:

```
ADMOB_CLIENT_ID=xxx.apps.googleusercontent.com
ADMOB_CLIENT_SECRET=GOCSPX-xxxxx
ADMOB_REFRESH_TOKEN=1//0e-xxxxx
ADMOB_PUBLISHER_ID=pub-2444093901783574
```

### Doğrulama

- Redeploy
- `https://app.orbisastro.online/admin/dashboard`
- "AdMob Performans" kartında sayılar (revenue, impressions, eCPM)
- `/admin/api/admob/overview?range=30d` → 200 OK

---

## ADIM 4 — Firebase Admin Custom Claim (Firestore Rules için)

### 4a) Admin UID'lerini bul

1. https://console.firebase.google.com/ → **Authentication** → **Users**
2. Admin email'ini bul → UID'yi kopyala (28 karakter)

### 4b) Custom claim ekle (localden veya VPS'den)

VPS'de (Firebase credentials zaten mount edilmiş):

```bash
# Tek UID
python scripts/set_admin_claim.py --uid <UID>

# Email ile
python scripts/set_admin_claim.py --email admin@orbisastro.online

# Çoklu
python scripts/set_admin_claim.py --email admin@orbisastro.online,owner@orbisastro.online

# Mevcut adminleri listele
python scripts/set_admin_claim.py --list

# Claim kaldır
python scripts/set_admin_claim.py --uid <UID> --remove
```

**Script:** `scripts/set_admin_claim.py` (zaten yazıldı, FIREBASE_CREDENTIALS_PATH env'den okur)

### Doğrulama

- Custom claim sonrası kullanıcının ID token'ı çözümlenince `admin: true` claim'i görünmeli
- Firestore'da `users/{uid}` doc'una client SDK ile erişim artık mümkün

---

## ADIM 5 — Firestore Rules Deploy

### 5a) Firebase CLI kur + login

Lokal makinede:

```bash
npm install -g firebase-tools
firebase login
```

### 5b) Proje seç + rules deploy

```bash
cd D:/astro-ai-predictor/backend/flask_app
firebase use orbis-ffa9e
firebase deploy --only firestore:rules
```

Mevcut rules (`firebase/firestore.rules`) Plan 4'te güncellenmişti:
- `|| true` backdoor KAPALI
- `isPremium, premiumExpiry, premiumPackageId, credits, premiumActivatedAt` sadece Admin SDK yazabilir
- `request.auth.token.admin == true` olan herkes tüm `users/{uid}` okuyabilir

### Doğrulama

- Firebase Console → **Firestore** → **Rules** → son published version tarihi
- Test: client ile `users/{uid}.isPremium` yaz → "permission-denied"

---

## ADIM 6 — Coolify Persistent Directories (S3 veya Volume)

Bu zaten Adım 2'de (`ga4-service-account.json`) yapıldı. Aynı pattern:

### Mevcut Yapı (Coolify orbisapp → Storage)

| Type | Source | Destination |
|---|---|---|
| Directory | `/data/coolify/applications/.../firebase-credentials.json` | `/app/firebase-credentials.json` |
| Directory | `/data/coolify/applications/.../ephe` | `/app/ephe` |
| Directory | (yeni) `.../secrets/ga4-service-account.json` | `/app/ga4-service-account.json` |
| Directory | (yeni) `.../secrets/play-service-account.json` | `/app/play-service-account.json` |
| Volume | `redis-data` | `/data` |

JSON dosyaları `chmod 600` ile okunabilir ama yazılamaz olmalı (güvenlik).

### S3 Alternatifi (Çoklu Coolify node varsa)

Eğer birden fazla Coolify node'un varsa, S3 ortak storage daha iyi:

1. Coolify → **Storages** (sol menü) → **+ Add** → **S3**
2. **MinIO** (Coolify built-in) veya harici S3 (AWS, DO Spaces, Backblaze B2)
3. Bucket: `orbis-secrets`
4. JSON dosyalarını upload et
5. Coolify → orbisapp → Storage → **Add Storage** → **S3 Bucket** → mount `/secrets/`

---

## ADIM 7 — Mobile CI (orbis-mobile GitHub Actions)

### 7a) Workflow dosyası

`orbis-mobile/.github/workflows/build-mobile.yml` zaten yazıldı:

```yaml
# Bu workflow shared JS sync + Android build + Play Store upload yapar.
# 4 GitHub Secret gerekir:
#   1. ANDROID_KEYSTORE_BASE64 — base64(jks dosyası)
#   2. ANDROID_KEYSTORE_PASSWORD
#   3. ANDROID_KEY_PASSWORD
#   4. GOOGLE_SERVICES_JSON — JSON dosyanın içeriği (raw)
#   5. ORBISAPP_PAT — orbisapp repo için read-only PAT
#   6. GA4_MEASUREMENT_ID
#   7. PLAY_SERVICE_ACCOUNT_KEY — Play Console service account JSON
```

### 7b) GitHub Secrets set et

`https://github.com/Optimus825482/orbis-mobile/settings/secrets/actions/new`

| Secret | Değer |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | `base64 -i orbis-release-key.jks` çıktısı |
| `ANDROID_KEYSTORE_PASSWORD` | keystore password |
| `ANDROID_KEY_PASSWORD` | jks key password |
| `GOOGLE_SERVICES_JSON` | JSON dosyanın raw içeriği (tüm JSON'ı yapıştır) |
| `ORBISAPP_PAT` | GitHub PAT: https://github.com/settings/tokens/new → repo (orbisapp) read-only |
| `GA4_MEASUREMENT_ID` | `G-XXXXXXXXXX` |
| `PLAY_SERVICE_ACCOUNT_KEY` | Play Console service account JSON (Google Cloud'dan indir) |

### 7c) Yeni keystore üret (production)

Eski keystore repo'da (Plan 1.1'de not düşüldü). **Production için yeni keystore üret:**

```bash
keytool -genkey -v \
  -keystore orbis-release-key.jks \
  -alias orbis-key \
  -keyalg RSA -keysize 2048 -validity 25000 \
  -storepass <GÜÇLÜ ŞİFRE> \
  -keypass <GÜÇLÜ ŞİFRE> \
  -dname "CN=ORBIS, OU=Mobile, O=ORBIS Inc, L=Istanbul, S=Istanbul, C=TR"

# Base64'e çevir
base64 -i orbis-release-key.jks > keystore.b64
# Bu içeriği ANDROID_KEYSTORE_BASE64 secret'ına yapıştır
```

### 7d) google-services.json secret'tan inject

`google-services.json` zaten repo'da (gitignore'da olmasına rağmen eski commit'te tracked). Production CI için:

```bash
# git'ten kaldır
cd orbis-mobile
git rm --cached android/app/google-services.json
git commit -m "fix(security): untrack google-services.json"
```

Workflow'daki `Restore google-services.json from secret` step'i GitHub Secret'tan inject eder.

---

## ✅ Doğrulama Checklist

Tüm 7 adım tamamlandıktan sonra:

- [ ] `https://app.orbisastro.online` → GA4 Realtime'da 1 aktif kullanıcı
- [ ] `https://orbisastro.online` → GA4'te 1 sayfa view
- [ ] `https://app.orbisastro.online/admin/dashboard` → KPI kartlar dolu
- [ ] AdMob Performans kartında revenue/impression/eCPM sayıları
- [ ] Admin claim atanan kullanıcı Firestore `users/{uid}` okuyabiliyor
- [ ] `isPremium` client SDK ile yazılamıyor (permission-denied)
- [ ] Mobile CI workflow main branch'e push'ta tetikleniyor, AAB üretiliyor
- [ ] Tag push (v1.0.0) Play Store internal track'e yükleniyor

---

## 🆘 Sorun Giderme

| Hata | Çözüm |
|---|---|
| `[GA4] client init failed` | Service account JSON dosya yolunu kontrol: `ls /app/ga4-service-account.json` |
| `permission-denied` Firestore | Admin claim atanmamış → Adım 4 tekrarla |
| `ADMOB_NOT_CONFIGURED 503` | OAuth credentials yanlış → Adım 3b, 3c kontrol |
| Tailwind CDN warning | Production için Tailwind CLI/PostCSS pipeline gerek (TODO) |
| `gtag/js 404` | GA4_MEASUREMENT_ID env'de yok |

---

## 📞 Bonus: Offline (Credentials Yoksa) Çalışma

Tüm credential'lar OLMADAN bile uygulama çalışır:

- GA4 yok → Admin dashboard'da KPI/AdMob kartları boş, KVKK banner gizli
- AdMob yok → AdMob kartı boş
- Firebase admin custom claim yok → admin yetkisi yok, ama normal kullanıcı işlemleri çalışır
- google-services.json yok → sadece mobil build kırılır, web PWA çalışır

**İlk etapta yalnızca GA4 Measurement ID + Firebase credentials yeterli. Geri kalanı zamanla ekleyebilirsin.**
