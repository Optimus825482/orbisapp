# Plan 3: AdMob Config Tek Kaynak + Düşük Öncelikli Temizlik

**Date:** 2026-06-23
**Goal:** AdMob config tek kaynağa topla (mobile + web import) + düşük öncelikli temizlik (lint deprecation, inline handlers, duplicate config, manifest targetApi).
**Architecture:** Tek `admob-config.js` module; `mobile/www/js/admob.js` + `static/js/mobile-bridge.js` import eder. Test/prod flag tek yerde.

## File Structure

### Create
- `static/js/admob-config.js` — tek ad unit ID kaynağı

### Modify
- `mobile/www/js/admob.js` — import config, hardcoded IDler kaldır
- `static/js/mobile-bridge.js` — import config, `ADMOB_TEST`/`ADMOB_PROD` blokları kaldır
- `mobile/capacitor.config.ts` — `initializeForTesting: false` zaten doğru, `testingDevices: []` ok
- `static/js/firebase-config.js:773` — `substring` → `slice`
- `static/js/mobile-bridge.js:515,518,651` — inline `onclick` → `addEventListener`
- `mobile/android/app/src/main/AndroidManifest.xml:30` — `tools:targetApi="31"` → `"35"`

### Delete
- `mobile/android/capacitor.config.ts` (cap sync üretir, root tek kaynak)

## Tasks

### Task 3.1: admob-config.js Tek Kaynak
**Files:** `static/js/admob-config.js` (create), `mobile/www/js/admob.js`, `static/js/mobile-bridge.js`
**Why:** Config dağınık:
- `mobile-bridge.js:38-45` — production ID'ler (farklı `REWARDED_ANALIZ`)
- `admob.js:13-17` — `REWARDED_INTERSTITIAL` ve `REWARDED_ANALYSIS` aynı ID (`9994253824`) ama birim adları farklı
- `capacitor.config.ts:31-32` — `testingDevices: []`, `initializeForTesting: false`
Tek kaynak olmalı, ayklar ve test flag tek yerde.
**Action:**

`static/js/admob-config.js`:
```js
// Tek AdMob config kaynağı — hem mobile (www) hem web (static/js) import eder
const IS_TEST = false; // production false

export const AD_UNITS = {
  banner: {
    prod: 'ca-app-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX',
    test: 'ca-app-pub-3940256099942544/6300978111'
  },
  interstitial: {
    prod: 'ca-app-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX',
    test: 'ca-app-pub-3940256099942544/1033173712'
  },
  rewardedInterstitial: {
    prod: 'ca-app-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX',
    test: 'ca-app-pub-3940256099942544/5224354917'
  },
  rewardedAnalysis: {
    prod: 'ca-app-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX', // Kullanıcı AdMob panelinden AYRI birim açsın
    test: 'ca-app-pub-3940256099942544/5224354917'
  },
  appId: 'ca-app-pub-XXXXXXXXXXXXXXXX~XXXXXXXXXX'
};

export function unit(key) {
  return AD_UNITS[key][IS_TEST ? 'test' : 'prod'];
}
```

- `mobile/www/js/admob.js:11-17`: hardcoded `REWARDED_INTERSTITIAL` ve `REWARDED_ANALYSIS` sabitlerini `import { AD_UNITS, unit } from './admob-config.js'` ile değiştir
  - `REWARDED_INTERSTITIAL` ve `REWARDED_ANALYSIS` **ayrı** ID'ler kullan (kullanıcı AdMob panelinden iki ayrı birim açsın — şu an 9994253824 ikisi de, ayrılması önerilir ama zorunlu değil; doğru raporlama için ayrılması önerilir)
- `static/js/mobile-bridge.js:29-45`: `ADMOB_TEST`/`ADMOB_PROD` blokları kaldır, `import { AD_UNITS, unit }` kullan
- `capacitor.config.ts:31-32`: `initializeForTesting: false`, `testingDevices: []` KALSIN (doğru)
- **Note:** `mobile/www/js/` ve `static/js/` aynı dosyaları paylaşır — tek path'e sembolik link veya kopyala; build/Coolifycdn ile senkron tutulmalı (mevcut akış zaten böyle, sim değişiklik yok).
- **Commit:** `refactor(admob): single config source for mobile and web`

### Task 3.2: token.substring Fix
**File:** `static/js/firebase-config.js:773`
**Why:** `token.substring(0, 20)` — modern JS'te lint deprecation uyarısı.
**Action:**
- `token.substring(0, 20)` → `token.slice(0, 20)`
- **Commit:** `fix(js): use slice instead of deprecated substring`

### Task 3.3: inline onclick → addEventListener
**File:** `static/js/mobile-bridge.js:515,518,651`
**Why:** `onclick="OrbisBridge.acceptNotifications()"` inline script. CSP `None` olduğu için çalışıyor ama CSP tighten edilirse kırılır — CSP-uyumlu değil.
**Action:**
- Somut satırlar:
  - `:515` button → `id="accept-notif-btn"`, `onclick` attribute KALDIR
  - `:518` button → `id="decline-notif-btn"`, `onclick` KALDIR
  - `:651` button → `id="notif-close-btn"`, `onclick` KALDIR
- Kodun sonuna:
  ```js
  document.getElementById('accept-notif-btn')?.addEventListener('click', () => OrbisBridge.acceptNotifications());
  document.getElementById('decline-notif-btn')?.addEventListener('click', () => OrbisBridge.declineNotifications());
  document.getElementById('notif-close-btn')?.addEventListener('click', () => OrbisBridge.closeNotification());
  ```
- fonksiyon isimleri `OrbisBridge.*` ile mevcut method adlarına uy — method adları eşleşmezse ayarla.
- **Commit:** `fix(mobile): replace inline onclick with addEventListener for CSP compliance`

### Task 3.4: capacitor.config.ts Dedup
**Files:** `mobile/capacitor.config.ts`, `mobile/android/capacitor.config.ts`
**Why:** Root `mobile/capacitor.config.ts` tek kaynak olmalı — android'deki `cap sync` tarafından üretilen duplicate tutulur ama manuel editleme çakışır.
**Action:**
- `mobile/android/capacitor.config.ts` SİL (cap sync üretir — auto-generated)
- Root `mobile/capacitor.config.ts` tek kaynak; `cap sync` regen yapsın
- **Note:** `cap sync` çalıştırınca android altında yeniden üretilir — doğru davranış.
- **Commit:** `chore(mobile): remove generated capacitor.config.ts in android — root is single source`

### Task 3.5: manifest targetApi
**File:** `mobile/android/app/src/main/AndroidManifest.xml:30`
**Why:** `tools:targetApi="31"` — compileSdk 35 olmalı `targetApi`. Android 12+ Bluetooth/arka plan location için yanlış.
**Action:**
- `tools:targetApi="31"` → `tools:targetApi="35"`
- **Commit:** `fix(mobile): manifest targetApi 35 matches compileSdk`

### Task 3.6: Heartbeat (opsiyonel)
**File:** `static/js/firebase-config.js:873-875` (heartbeat 60s)
**Why:** Rapor yanlıştı — heartbeat Firestore'a doğrudan yazmıyor, backend `/api/stats/heartbeat` POST atıyor. Maliyet düşük. Loglama batching isteyebilir ama kritik değil.
**Action:**
- Backend `/api/stats/heartbeat` endpoint'inde batching yoksa 60-aktif-user = 60 req/dak = 86k req/gün — Flask sunucu için sorun değil, 5 dk'ya çıkar yeter.
- Client 60s → 300s if bottleneck visibly otherwise skip.
- **Kod değişiklik opsiyonel** — sadece gözlem sonrası.
- **Commit (opsiyonel):** `perf(stats): increase heartbeat interval to 5min to reduce backend load`

## Done Criteria

- [ ] `admob-config.js` tek kaynak
- [ ] `admob.js` + `mobile-bridge.js` import ediyor
- [ ] AdMob ayrı birim ID'leri ayrılandır (kullanıcı panel açar)
- [ ] `token.slice` ile düzeltildi
- [ ] Inline `onclick` → `addEventListener` (3 yer)
- [ ] `mobile/android/capacitor.config.ts` silindi
- [ ] Manifest `targetApi="35"`
- [ ] (opsiyonel) heartbeat interval tuned

## Dependencies

- Plan 1, Plan 2 tamamlandıktan sonra yapılabilir (bağımsız ama sonda daha temiz)
- Kullanıcı sağlar (opsiyonel): AdMob üretim birim ID'leri (ayrı iki rewarded birim)

## Test Plan

1. Build: `cd mobile && npx cap sync android` success
2. Mobil: app aç → AdMob birim request üretiliyor mu control (AdMob dashboard log)
3. Notification modal → button tıklama çalışıyor (addEventListener)
4. `console.log` ile `unit('banner')` üretim/test ID'sini confirm

## Risks

- **AdMob test ID'leri** — Google'ın official `ca-app-pub-3940256099942544/...` her zaman kullanılabilir; production ID'ler boş bırakılırsa test mode yeterli
- **Cap sync** — `mobile/android/capacitor.config.ts` silindikten sonra regenerated, manuel edit kaybı yok (root'ta tutuyoruz)