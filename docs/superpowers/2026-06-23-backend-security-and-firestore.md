# Plan 2: Backend Security + Firestore Rules + Premium Tek Kaynak + Push Auth

**Date:** 2026-06-23
**Goal:** Backend `verify_purchase` gerçek Google Play API doğrulaması; Firestore rules `|| true` backdoor kapat; tek premium kaynağı (`users/{uid}.isPremium` — client yazamaz); push endpoint auth; FCM token cleanup.
**Architecture:** Google Play Developer API server-side token doğrulaması (service account). Firestore rules: protected alanlar sadece admin SDK yazabilir. Client Firestore'a doğrudan `isPremium` yazamaz → backend route tek kaynak.

## Global Constraints

- Google Play service account JSON path env `PLAY_SERVICE_ACCOUNT_PATH` (kullanıcı sağlar, git'e commitlenmez)
- Product ID'ler Play Console ile eşleşmeli — Plan 1 ile aynı: `astro_premium_monthly`, `astro_premium_yearly`, `astro_premium_lifetime`
- Dependency: `google-api-python-client`, `google-auth` (requirements.txt'e ekle)
- Backend Python 3.x + Flask 3.0 (mevcut)
- Firestore Admin SDK (mevcut `firebase_service.py`)

## File Structure

### Modify
- `firebase/firestore.rules` — `|| true` kaldır, premium alanları sadece server yazabilir
- `monetization/usage_tracker.py` — `verify_purchase` gerçek Google Play API, product map düzelt, boş `print`'ler → `logger`
- `monetization/routes.py` — `verify-purchase` + `premium-status` endpoint'lerine Firebase ID token auth
- `routes/push_routes.py` — `subscribe-topic`/`unsubscribe` auth (token sahipliği kontrolü)
- `services/firebase_service.py:321-323` — FCM token cleanup sorgusu (map field sorgusu yerine farklı yaklaşım)
- `static/js/firebase-config.js:441-457` — client `activatePremium` kaldır, backend route'a yönlendir
- `requirements.txt` — `google-api-python-client`, `google-auth`

### Create
- `services/google_play.py` — Google Play Developer API wrapper

## Tasks

### Task 2.1: firestore.rules Backdoor Kapat 🔥
**File:** `firebase/firestore.rules` (lines 16-24 — `|| true` branch)
**Why:** Test-mode backdoor açık — client `isPremium`/`credits` doğrudan yazabilir. Kötü niyetli kullanıcı premium kend atayabilir.
**Action:**
- `|| true` branch'i SİL
- Korumalı alanlar (`isPremium`, `premiumExpiry`, `premiumPackageId`, `credits`, `premiumActivatedAt`): sadece `request.auth.token.admin == true` yazabilir (Admin SDK her zaman allow — server-side route tek kaynak)
- Client izinli alanlar: `dailyUsage`, `totalAnalyses`, `fcmTokens`, `lastSeen`, `stats.heartbeats` (kullanıcı kendi doc'unu oku-yaz)
- Okuma: `request.auth != null && request.auth.uid == userId` (kullanıcı kendi doc'unu okur); admins her şeyi okur
- **Deploy:** `firebase deploy --only firestore:rules` (kullanıcı Firebase CLI ile yapar, env gerektirir)
- **Test:** client update dene → permission-denied; admin SDK update dene → success
- **Commit:** `fix(firestore): close test-mode backdoor — protected premium fields server-only`

### Task 2.2: google_play.py Service 🔥
**File:** `services/google_play.py` (create)
**Why:** Backend `verify_purchase` şu an self-asserted — herkes premium olabilir. Real token doğrulaması gerek.
**Action:**

```python
import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/androidpublisher']
PACKAGE_NAME = 'com.orbisastro.orbis'

def _get_service():
    path = os.getenv('PLAY_SERVICE_ACCOUNT_PATH')
    if not path:
        raise RuntimeError('PLAY_SERVICE_ACCOUNT_PATH env not set')
    creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    return build('androidpublisher', 'v3', credentials=creds, cache_discovery=False)

def verify_purchase_token(purchase_token: str, product_id: str) -> dict:
    """Verify a Google Play subscription purchase token server-side.
    Returns {valid: bool, expiry_time: str|None, purchase_state: int|None}.
    """
    try:
        svc = _get_service()
        if product_id.endswith('_lifetime'):
            # Non-consumable / non-renewing
            resp = svc.purchases().products().get(
                packageName=PACKAGE_NAME,
                productId=product_id,
                token=purchase_token
            ).execute()
            state = resp.get('purchaseState', -1)
            # purchaseState 0 = Purchased
            return {
                'valid': state == 0,
                'expiry_time': resp.get('expiryTimeMillis'),
                'purchase_state': state
            }
        else:
            # Subscription (renewing)
            resp = svc.purchases().subscriptions().get(
                packageName=PACKAGE_NAME,
                subscriptionId=product_id,
                token=purchase_token
            ).execute()
            state = resp.get('paymentState', -1)
            # 1 = PaymentReceived, 2 = Pending
            return {
                'valid': state == 1,
                'expiry_time': resp.get('expiryTimeMillis'),
                'purchase_state': state
            }
    except Exception as e:
        logger.exception('[GooglePlay] verify failed')
        return {'valid': False, 'expiry_time': None, 'purchase_state': -1}
```

- **Config:** env `PLAY_SERVICE_ACCOUNT_PATH` zorunlu — boşsa `RuntimeError` (fail-closed)
- **Test:** mock purchase_token → `valid=False`
- **Commit:** `feat(services): google_play verify_purchase_token via Play Developer API`

### Task 2.3: usage_tracker.verify_purchase Rewrite 🔥
**File:** `monetization/usage_tracker.py:344-358`
**Why:** Mevcut `verify_purchase` product ID'leri mobildeki ile eşleşmiyor + token doğrulaması YOK.
**Action:**
- `valid_products` map'i güncelle — Plan 1 ile aynı:
  ```python
  valid_products = {
      'astro_premium_monthly': 30,
      'astro_premium_yearly': 365,
      'astro_premium_lifetime': 36500
  }
  ```
- `verify_purchase(self, uid, purchase_token, product_id)`:
  1. Product ID map'te yok → `{"success": False, "error": "Unknown product"}`
  2. `from services.google_play import verify_purchase_token`
  3. `result = verify_purchase_token(purchase_token, product_id)`
  4. `valid=False` → `{"success": False, "error": "Invalid purchase token"}`
  5. `valid=True`:
     - `self.set_premium(device_id, valid_products[product_id])` (usage_tracking record)
     - `firebase_service.activate_premium(uid, valid_products[product_id], product_id)` (users/{uid} — tek kaynak)
     - return `{"success": True, "expiry": result['expiry_time']}`
- **Premium tek kaynak:** `users/{uid}.isPremium` — client yazamaz (rules Task 2.1), Admin SDK yazar (route üzerinden)
- **Commit:** `feat(monetization): verify_purchase real Google Play API + product map aligned`

### Task 2.4: usage_tracker Boş print'ler
**File:** `monetization/usage_tracker.py` (lines 94, 102, 114, 116, 149, 175, 324)
**Why:** `print(f"[UsageTracker] ")` boş context — debug imkansız, stdout şişiriyor.
**Action:**
- `print(f"[UsageTracker] ")` → `logger.debug("[UsageTracker] <context>")` (anlamlı içerikle)
- Dosya başında yoksa `import logging` + `logger = logging.getLogger(__name__)` ekle
- Veya kullanılmayanları sil.
- **Commit:** `fix(monetization): replace empty print with structured logger.debug`

### Task 2.5: verify-purchase Route Auth + uid 🔥
**File:** `monetization/routes.py:52`
**Why:** Route tam public — self-asserted `device_id`/`email`. Herkes premium atayabilir.
**Action:**
- Auth ekle: `Authorization: Bearer <Firebase ID token>` header'ı verify et, `uid` çıkar
  ```python
  from firebase_admin import auth as fb_auth
  def _verify_id_token(req):
      token = req.headers.get('Authorization', '').replace('Bearer ', '')
      if not token: abort(401, 'missing token')
      try:
          decoded = fb_auth.verify_id_token(token)
          return decoded['uid']
      except Exception:
          abort(401, 'invalid token')

  @bp.route('/verify-purchase', methods=['POST'])
  def verify_purchase():
      uid = _verify_id_token(request)
      data = request.get_json()
      result = tracker.verify_purchase(uid, data['purchaseToken'], data['productId'])
      return jsonify(result)
  ```
- **`device_id`:** client-supplied yerine `uid`-türevli veya `uid + device_id` ikisi de. İmza `verify_purchase(self, uid, purchase_token, product_id)` (Task 2.3).
- **Commit:** `fix(monetization): require Firebase ID token on verify-purchase route`

### Task 2.6: Client Premium Akışı → Backend 🔥
**File:** `static/js/firebase-config.js:441-457`
**Why:** Client Firestore'a doğrudan `isPremium=true` yazabiliyor — security risk (Task 2.1 rules ile kapatılsa bile tek akış olmalı).
**Action:**
- `activatePremium` fonksiyonu **client-side Firestore write KALDIR**
- Yerine: IAP `purchase()` (Plan 1 Task 1.9) `fetch('/api/monetization/verify-purchase', ...)` çağırıyor — bırakın öyle
- Firebase config'teki premium state kaynak değişikliği: `users/{uid}.isPremium`'ı backend yazıyor; client okuma-only.
- `restorePurchases` da backend route'a gitsin (Plan 1 Task 1.9 zaten yapıyor)
- **Commit:** `fix(js): remove client-side Firestore premium write — backend single source`

### Task 2.7: Push Route Auth 🔥
**File:** `routes/push_routes.py`
**Why:** Hiçbir auth yok — herkes `premium_users` topic'e abone olabilir, premium olmayanlar premium push'ları alır.
**Action:**
- **`POST /subscribe-topic`** (line 62):
  - `_verify_id_token(request)` ile `uid` alın
  - Topic `premium_users` ise `users/{uid}.isPremium == true` kontrolü server-side (Admin SDK okuma)
  - Premium değilse `403 Forbidden`
  - token sahipliği kontrolü: token'ın user'a ait olduğunu `users/{uid}.fcmTokens` içinde ara
- **`POST /unsubscribe-topic`** (line 98): aynı auth; sahiplilik yeterli
- **`POST /register-token`** (line 16): auth opsiyonel olabilir (public kayıt kabul) — ama topic aboneliği auth sonrası
- **Commit:** `fix(push): require Firebase auth + premium check on premium_users topic`

### Task 2.8: FCM Token Cleanup Sorgusu
**File:** `services/firebase_service.py:320-328`
**Why:** Firestore `array_contains` ile obje eşleştirme desteklemez — sorgu hiç sonuç döndürmez, geçersiz token'lar asla temizlenmiyor, push maliyeti artıyor.
**Action:**
- Mevcut `where('fcmTokens', 'array_contains', {'token': token})` KALDIR
- Yeni yaklaşım:
  ```python
  doc_ref = self.db.collection('users').document(uid)
  doc = doc_ref.get()
  if not doc.exists: return False
  tokens = doc.to_dict().get('fcmTokens', [])
  filtered = [t for t in tokens if t.get('token') != token]
  doc_ref.update({'fcmTokens': filtered})
  return len(filtered) < len(tokens)
  ```
- N+1 yavaş ama doğru. Belki `tokens` map field (`tokens.token` indexlenebilir) migrasyon için not düş.
- **Alternative:** `fcmTokens` yapısını `[{token, addedAt}]` yerine `{token: {addedAt, ...}}` map'e çevir — `createIndex` ile `tokens.<token>` field sorgusu. Daha ileri adım, opsiyonel.
- **Test:** mock `users` doc with stale token → cleanup removes it
- **Commit:** `fix(firebase): FCM token cleanup via doc read-filter instead of unsupported array_contains`

### Task 2.9: ai_service Gating Dokümantasyon
**File:** `services/ai_service.py` (no code change) + README
**Why:** Gating `usage_tracker` route layer'da — AI service neutral kalır. Karışıklık var.
**Action:**
- README'ye not: "Premium/free gating `usage_tracker` middleware'indedir; `ai_service` neutral'dır, doğrudan çağrılmaz."
- Kod değişiklik yok.
- **Commit:** `docs: note premium gating location in usage_tracker, not ai_service`

## Done Criteria

- [ ] firestore.rules `|| true` kapalı, protected fields server-only
- [ ] `google_play.verify_purchase_token` çalışır (mock test)
- [ ] `verify_purchase` gerçek token doğrulaması + product map aligned
- [ ] `print()` boşluklar `logger.debug` ile değiştirildi
- [ ] `verify-purchase` route Firebase ID token zorunlu
- [ ] Client `activatePremium` Firestore write kaldırıldı
- [ ] Push `premium_users` topic auth + premium check
- [ ] FCM token cleanup düzeltildi
- [ ] `requirements.txt` güncellendi
- [ ] README'ye gating notu

## Dependencies

- Plan 1 Task 1.9 (iap.js) — aynı product ID'ler (`astro_premium_*`); mobil verify-purchase route'a token gönderir
- Kullanıcı sağlar: Play Service account JSON (`PLAY_SERVICE_ACCOUNT_PATH`), Firebase CLI (rules deploy için)
- `google-api-python-client`, `google-auth` pip install gerekli

## Test Plan

1. Backend: mock purchase_token → `verify_purchase_token` returns `valid=False`
2. Backend: integration test with real service account (dev credentials) → subscribed user verify → `valid=True`
3. `pytest monetization/` — verify_purchase route auth test (no token → 401, valid token → ok)
4. Firestore rules emulator: client update `isPremium` → permission-denied
5. Push: non-premium user subscribe `premium_users` → 403

## Risks

- **Service account secret** — git'e commitlenmemeli (`.gitignore`)
- **Firestore rules deploy** — production'ı etkiler; emulator test önce
- **`array_contains` migration** — clientilerin `fcmTokens` formatı değişirse geçiş gerekir — opsiyonel map field migrasyonu not düştük