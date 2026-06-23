# Plan 1: Mobile Security + IAP Implementation

**Date:** 2026-06-23
**Goal:** Close mobile security holes + make IAP actually work (real money flow)
**Architecture:** `@capacitor-community/billing` Capacitor plugin, uses existing `billingclient:7.1.1` gradle dep. Backend `verify_purchase` Google Play Developer API integration handled in **Plan 2**. This plan = mobile side only.

## Global Constraints

- `applicationId`: **`com.orbisastro.orbis`** (`mobile/android/app/build.gradle:7`) — DEĞIŞMEZ
- Real Google Play product IDs supplied by user via Play Console (`astro_premium_monthly`, `astro_premium_yearly`, `astro_premium_lifetime` — önerilen)
- Keystore password env **zorunlu**, fallback YOK
- `static/js/mobile-bridge.js` = `mobile/www/js/mobile-bridge.js` (web server.url ile paylaşılan) — tek dosya

## File Structure

### Modify
- `mobile/android/app/build.gradle` — signingConfigs fallback'leri kaldır, minSdk 23
- `mobile/android/app/src/main/AndroidManifest.xml` — cleartext false
- `mobile/capacitor.config.ts` — allowMixedContent false
- `mobile/android/app/google-services.json` — 2 eski client entry sil
- `mobile/package.json` — cap:init applicationId düzelt, cordova-plugin-purchase kaldır, @capacitor-community/billing ekle
- `mobile/android/app/capacitor.build.gradle` — billingclient dep doğru referans
- `mobile/www/js/app.js:110` — App.exitApp() → App.close()
- `mobile/android/app/src/main/java/com/orbisastro/orbis/MainActivity.java` — Firebase init
- `mobile/android/variables.gradle` — minSdkVersion 23
- `static/js/mobile-bridge.js:1035` — position: öneki ekle, Tailwind fix
- `.gitignore` (root) — append keystore + key store files

### Create
- `mobile/iap.js` rewrite (real billing flow)

## Tasks

### Task 1.1: Keystore Güvenliği 🔥
**File:** `mobile/android/app/build.gradle:27-29`
**Why:** Şifre git içinde plain-text. Keystore çalınırsa tüm APK'lar imzalanabilir.
**Action:**
- `storePassword System.getenv('ORBIS_KEYSTORE_PASSWORD') ?: 'Orbis2026!Secure'` → `storePassword System.getenv('ORBIS_KEYSTORE_PASSWORD')`
- `keyPassword System.getenv('ORBIS_KEY_PASSWORD') ?: 'Orbis2026!Secure'` → `keyPassword System.getenv('ORBIS_KEY_PASSWORD')`
- Boş env → build fail (gradle property required hata verir).
- **.gitignore** (root): append
  ```
  orbis-release-key.jks
  *.jks
  key.properties
  *.pem
  google-services.json
  ```
- **History temizliği:** Kullanıcıya `git filter-branch` veya BFG Repo-Cleaner öner (agent yapmaz, user kararı). En azından **yeni keystore** üret ve git'e eski hash'te kalsın bile kullanılmasın.
- **Commit:** `fix(mobile): remove hardcoded keystore password fallback — env required`

### Task 1.2: google-services.json Temizle
**File:** `mobile/android/app/google-services.json`
**Why:** 3 farklı package_name var, ikisi gereksiz. Yanlış `cap init` config bozar.
**Action:**
- `client[]` array'inden:
  - `com.orbis.astrology` (lines 11-50) SİL
  - `com.orbisapp.astrology` (lines 56-96) SİL
- Sadece `com.orbisastro.orbis` (lines 101+) kalsın.
- `mobile/package.json:8` `"cap:init": "npx cap init ORBIS com.orbis.astrology --web-dir=www"` → `"cap:init": "npx cap init ORBIS com.orbisastro.orbis --web-dir=www"`
- **Verify:** `npx cap sync android` fails-fast if json invalid.
- **Commit:** `fix(mobile): remove stale package entries from google-services.json`

### Task 1.3: Cleartext + MixedContent Kapat
**Files:**
- `mobile/android/app/src/main/AndroidManifest.xml:29`
- `mobile/capacitor.config.ts:46`
**Why:** MITM saldırı yüzeyi. Production'da kapatılmalı.
**Action:**
- Manifest: `android:usesCleartextTraffic="true"` → `android:usesCleartextTraffic="false"`
- capacitor.config.ts: `allowMixedContent: true` → `allowMixedContent: false`
- webDir bir dosya var mı kontrol et, hem kapı (config) hem çalışan Kaynaklar güvenli.
- **Commit:** `fix(mobile): disable cleartext traffic and mixed content`

### Task 1.4: minSdk 23 + versionCode Tutarsızlık
**Files:**
- `mobile/android/variables.gradle:2`
- `mobile/android/app/build.gradle:10`
**Why:** AdMob + Google Auth minSdk 23+ önerir. versionName "1.0.8" ile versionCode=9 uyumsuz görünse de Play Store versionCode monotonik ister; 9 yeterli (8 değil).
**Action:**
- `mobile/android/variables.gradle:2` `minSdkVersion = 22` → `minSdkVersion = 23`
- `build.gradle:10` `versionCode = 9` KALSIN (>= 8 yerine = 9, Play Store için doğru)
- **Commit:** `fix(mobile): bump minSdk to 23 for AdMob + Google Auth compat`

### Task 1.5: @capacitor-community/billing Ekle
**File:** `mobile/package.json`
**Why:** `cordova-plugin-purchase` listede ama kullanılmıyor — ölü dependency. Gerçek billing için Capacitor-native plugin gerek.
**Action:**
- `"cordova-plugin-purchase": "^13.12.1"` satırını SİL
- dependencies'e ekle: `"@capacitor-community/billing": "^6.0.0"` (Capacitor 6 uyumlu)
- `mobile/android/capacitor.build.gradle:20` `implementation "com.android.billingclient:billing:7.1.1"` KALSIN (plugin bunu kullanır, sorun değil)
- `pubspec.lock` / `package-lock.json` kontrol: `npm install` çalışınca sync et
- **Commit:** `feat(mobile): replace dead cordova-plugin-purchase with @capacitor-community/billing`

### Task 1.6: MainActivity Firebase Init
**File:** `mobile/android/app/src/main/java/com/orbisastro/orbis/MainActivity.java`
**Why:** Java boş — Firebase Analytics otomatik init için `FirebaseApp.initializeApp()` çağrısı yok, native crash riski.
**Action:**
- import: `import com.google.firebase.FirebaseApp;`
- `onCreate` içinde `super.onCreate(savedInstanceState)` sonrasına: `FirebaseApp.initializeApp(this);`
- **Commit:** `fix(mobile): explicit Firebase init in MainActivity`

### Task 1.7: app.js backButton Fix
**File:** `mobile/www/js/app.js:110`
**Why:** `App.exitApp()` Capacitor 6'da deprecated, `App.close()`.
**Action:**
- `App.exitApp()` → `App.close()`
- **Commit:** `fix(mobile): use App.close() instead of deprecated exitApp()`

### Task 1.8: mobile-bridge CSS Fix 🔥
**File:** `static/js/mobile-bridge.js:1035`
**Why:** `'fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm'` — `position:` öneki yok, Tailwind class'ları `style.cssText` içinde çalışmaz. Modal muhtemelen yanlış konumlanıyor.
**Action:**
- `modal.style.cssText = 'fixed inset-0 ...'` →
  ```js
  modal.style.cssText = 'position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.8);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px)';
  ```
- Audit: grep `style.cssText = '` ile mobile-bridge.js içindeki diğer Tailwind-in-cssText kullanımları; hepsini CSS property'e çevir.
- **Commit:** `fix(mobile): correct missing position: prefix and remove Tailwind classes from cssText`

### Task 1.9: iap.js Rewrite — Gerçek Billing 🔥🔥
**File:** `mobile/www/js/iap.js` (rewrite)
**Why:** Mevcut sadece Play Store sayfasını açıyor — kullanıcı ödeyemiyor. "Premium" tamamen sahte.
**Action:**

Production-ready skeleton (kullanıcı product ID'leri env/Play Console'dan):

```js
import { Billing } from '@capacitor-community/billing';

// Product ID'ler — Play Console ile eşleşmeli (Plan 2 Task 2.3 ile aynı)
const BILLING_PRODUCTS = {
  astro_premium_monthly:   { type: 'subs', months: 1 },
  astro_premium_yearly:    { type: 'subs', months: 12 },
  astro_premium_lifetime:  { type: 'subs', months: 120 } // lifetime = 10 yıl subs veya non-consumable
};

let billingReady = false;

export async function initIAP() {
  try {
    await Billing.initialize();
    // plugin auto-registers products — confirm available
    billingReady = true;
  } catch (e) {
    console.error('[IAP] init failed', e);
    billingReady = false;
  }
}

export async function purchase(productId) {
  if (!billingReady) { throw new Error('IAP not initialized'); }
  if (!BILLING_PRODUCTS[productId]) { throw new Error('Unknown product ' + productId); }

  try {
    const result = await Billing.purchaseProducts({ productId });
    const t = result.transaction || result;
    // Send to backend for verification (Plan 2 Task 2.3)
    const resp = await fetch('/api/monetization/verify-purchase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + (await getIdToken()) },
      body: JSON.stringify({
        purchaseToken: t.purchaseToken,
        productId,
        transactionId: t.id || t.transactionId,
        orderId: t.orderId
      })
    });
    const data = await resp.json();
    if (data.success === true) {
      // state isPremium set by backend — DON'T write Firestore directly
      return { success: true, expiry: data.expiry };
    } else {
      return { success: false, error: data.error || 'Verification failed' };
    }
  } catch (e) {
    console.error('[IAP] purchase failed', e);
    return { success: false, error: e.message };
  }
}

export async function restorePurchases() {
  if (!billingReady) { return; }
  try {
    const rest = await Billing.restorePurchases();
    for (const t of (rest.transactions || [])) {
      const resp = await fetch('/api/monetization/verify-purchase', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + (await getIdToken()) },
        body: JSON.stringify({ purchaseToken: t.purchaseToken, productId: t.productId })
      });
      const data = await resp.json();
      if (data.success === true) { return { success: true }; }
    }
    return { success: false, error: 'No valid purchases' };
  } catch (e) {
    return { success: false, error: e.message };
  }
}
```

- `getIdToken()` — Firebase Auth current user ID token (firebase-config.js içinde var).
- **Fail-closed:** backend success:false → premium verme.
- **Memory:** `state.isPremium=true` client-side güvenli çünkü backend tek kaynak; çift-truth yok.
- **Commit:** `feat(mobile): implement real IAP with @capacitor-community/billing`

### Task 1.10: Build Test
**Action:**
- `cd mobile && npx cap sync android`
- `cd android && ./gradlew assembleRelease` (env şifrelerle: `ORBIS_KEYSTORE_PASSWORD=... ORBIS_KEY_PASSWORD=... ./gradlew assembleRelease`)
- Build success verify et. APK imzalı üret.
- **Commit final:** `chore(mobile): verified release build passes`

## Done Criteria

- [ ] Keystore şifresi git'te plain-text değil, env zorunlu
- [ ] google-services.json tek client
- [ ] cleartext/mixedContent kapalı
- [ ] minSdk 23
- [ ] @capacitor-community/billing çalışır
- [ ] MainActivity Firebase init
- [ ] backButton close()
- [ ] mobile-bridge cssText düzeltilmiş
- [ ] iap.js gerçek billing akışı (backend verify)
- [ ] `./gradlew assembleRelease` success

## Dependencies

- Plan 2 Task 2.3 (verify_purchase) — aynı product ID'ler kullanılmalı: `astro_premium_monthly`, `astro_premium_yearly`, `astro_premium_lifetime`
- Kullanıcı sağlar: env şifreleri, Play Console service account (Plan 2 için), product ID'ler

## Risks

- **`@capacitor-community/billing` v6 sürüm kontrolü** — Capacitor 6 ile uyumlu olduğunu npm page'den verify et (yazımda ^6.0.0 önerildi, npm'de gerçek sürümü kontrol et).
- **Play Service account** — Plan 2 gerekli. Plan 1 tek başına backend verify eksik, ama mobil akış çalışır (backend placeholder dönerse false).
- **History temizliği** — eski commit hash'inde şifre hâlâ var. Yeni keystore üret şart.