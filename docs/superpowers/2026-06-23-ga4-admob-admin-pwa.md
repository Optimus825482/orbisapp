# Plan 4: GA4 + AdMob + Admin Dashboard PWA + Dark/Light Theme

**Tarih:** 2026-06-23
**Hedef:** Tüm 3 yere (orbis-landing, orbisapp, orbis-mobile) Google Analytics 4; AdMob rapor verisini admin dashboard'da göster; admin'i impeccable standardında PWA + dark/light tema ile yeniden kur.
**Tasarım:** PRODUCT.md + DESIGN.md (yazıldı) → product register, pre-dawn observatory mood, OKLCH palette, no cosmic cliché.

## Global Constraints

- GA4 Measurement ID: `G-XXXXXXXXXX` (kullanıcı sağlar)
- AdMob publisher ID: `pub-XXXXXXXXXXXXXX` (kullanıcı sağlar)
- GA4 Service Account JSON → Coolify secret mount (env: `GA4_SERVICE_ACCOUNT_PATH`)
- AdMob API OAuth: refresh token → Coolify secret mount (env: `ADMOB_REFRESH_TOKEN`, `ADMOB_CLIENT_ID`, `ADMOB_CLIENT_SECRET`)
- Flask → `google-analytics-data` + `google-auth` (yeni deps)
- Flask → `google-ads-admob` veya `google-api-python-client` (AdMob API)
- Admin PWA: Service Worker, manifest.json, offline shell
- Theme: localStorage + OS preference + no-flash inline script
- PWA installable: manifest + icons (mevcut `static/all-icons/`)

## File Structure

### Modify
- `templates/admin/layout.html` — sidebar + topbar + theme toggle + impeccable layout
- `templates/admin/dashboard.html` — KPI row + ChartCard + ActivityFeed
- `templates/admin/users.html` — DataTable + filters
- `templates/admin/user_detail.html` — kullanıcı detay
- `templates/admin/pricing.html` — fiyat CRUD
- `templates/admin/push.html` — push kampanyası
- `templates/admin/stats.html` — analytics detail
- `templates/admin/ai_settings.html` — AI config
- `templates/admin/login.html` — light/dark aware
- `templates/layout.html` — GA4 web + mobile
- `static/css/admin/*` — yeniden yaz
- `static/js/admin/*` — yeniden yaz
- `static/js/analytics.js` — GA4 events (yeni)
- `static/manifest-admin.json` — admin PWA
- `static/sw-admin.js` — admin service worker
- `static/all-icons/admin-*.png` — admin PWA icons
- `services/google_analytics.py` — GA4 Data API wrapper (yeni)
- `services/admob.py` — AdMob API wrapper (yeni)
- `routes/admin.py` — GA + AdMob endpoint'leri, tema-agnostik
- `app.py` — admin PWA route'ları
- `requirements.txt` — google-analytics-data, google-auth, google-ads-admob
- `env.example` — GA4 + AdMob env'leri
- `orbis-landing/index.html` — GA4 snippet
- `orbis-landing/script.js` — GA4 events
- `mobile/www/index.html` — GA4 Capacitor plugin init
- `mobile/capacitor.config.ts` — GA4 plugin
- `mobile/package.json` — GA4 Capacitor plugin ekle
- `firebase/firestore.rules` — admin collection role check (admin only)

### Create
- `static/css/admin/tokens.css` — CSS custom properties
- `static/css/admin/base.css` — reset + typography + focus
- `static/css/admin/layout.css` — sidebar + topbar + grid
- `static/css/admin/components.css` — metric card + chart card + table
- `static/css/admin/motion.css` — transitions + reduced motion
- `static/js/admin/theme.js` — toggle + localStorage
- `static/js/admin/shortcuts.js` — keyboard shortcuts
- `static/js/admin/charts.js` — vanilla SVG sparkline + chart
- `templates/admin/components/*.html` — Jinja macros
- `docs/superpowers/plans/2026-06-23-ga4-admob-admin-pwa.md` — bu plan

## Tasks

### Task 4.1: GA4 — Web (orbisapp + orbis-landing) 🔥
**Files:** `orbis-landing/index.html`, `static/js/analytics.js`, `templates/layout.html`
**Why:** Kullanıcı yolculuğu, dönüşüm hunisi, retention izleme.
**Action:**
- GA4 Measurement ID env: `GA4_MEASUREMENT_ID` (kullanıcı sağlar)
- `static/js/analytics.js` — `gtag` setup; page view otomatik; custom events: `sign_up`, `login`, `premium_purchase`, `chart_generated`, `ad_watched`, `push_received`
- Layout: `<script async src="https://www.googletagmanager.com/gtag/js?id=GA4_MEASUREMENT_ID">` + config
- orbis-landing: aynı snippet
- `noscript` iframe fallback
- **Cookie consent:** TR KVKK uyumlu — `localStorage.orbis_ga_consent` flag; banner "İzin ver / Reddet" gerek
- **Commit:** `feat(analytics): GA4 web tracking (orbisapp + orbis-landing) + KVKK consent`

### Task 4.2: GA4 — Mobile (orbis-mobile) 🔥
**Files:** `mobile/package.json`, `mobile/capacitor.config.ts`, `mobile/www/js/analytics.js`
**Why:** Native app analytics.
**Action:**
- Plugin: `@capacitor-community/gtag` (yoksa) veya `capacitor-plugin-appcenter-analytics` → **Öneri:** vanilla gtag injection
  - Native: `gtag` Capacitor WebView içinde çalışır (aynı JS), `cordova-plugin-google-analytics` ek plugin
  - **Daha basit:** Web PWA gibi `gtag` WebView üzerinden, aynı Measurement ID
- `mobile/www/js/analytics.js` (yeni) — `gtag` event'leri: `app_open`, `iap_initiated`, `iap_completed`, `restore_purchases`, `notification_allowed`
- `capacitor.config.ts` — server `cleartext: false` zaten (güvenli)
- **Commit:** `feat(mobile): GA4 webview tracking — events for IAP, push, app lifecycle`

### Task 4.3: GA4 Data API — Backend Service 🔥
**File:** `services/google_analytics.py` (new)
**Why:** Admin dashboard GA verisini çekecek.
**Action:**
- Service Account JSON: `GA4_SERVICE_ACCOUNT_PATH` env
- `from google.analytics.data_v1beta import BetaAnalyticsDataClient`
- `from google.oauth2 import service_account`
- Method `get_metrics(property_id, date_range)` → page_views, sessions, users, conversions
- Method `get_top_pages()` → sayfa bazlı
- Method `get_traffic_sources()` → source/medium
- **Cache:** Redis 1 saat TTL (GA API rate limit 10k req/gün, hızlı tüketir)
- **Commit:** `feat(services): google_analytics GA4 Data API wrapper + Redis cache`

### Task 4.4: AdMob API — Backend Service 🔥
**File:** `services/admob.py` (new)
**Why:** Admin dashboard gelir/impression/eCPM gösterecek.
**Action:**
- OAuth: `ADMOB_REFRESH_TOKEN`, `ADMOB_CLIENT_ID`, `ADMOB_CLIENT_SECRET`, `ADMOB_PUBLISHER_ID` env
- `google-ads-admob` paketi (yoksa manual `google-api-python-client`)
- Method `get_network_report(month)` → impressions, eCPM, revenue (USD/TRY)
- Method `get_app_report(app_id, date_range)` → per-app breakdown
- **Cache:** Redis 6 saat TTL (AdMob data 24h gecikme)
- **Commit:** `feat(services): admob API wrapper + Redis cache (revenue, impressions, eCPM)`

### Task 4.5: Admin Routes — GA + AdMob
**File:** `routes/admin.py`
**Why:** Admin dashboard data endpoint'leri.
**Action:**
- `GET /api/admin/analytics/overview?range=7d` → users, sessions, page_views, conversions
- `GET /api/admin/analytics/traffic?range=7d` → source/medium breakdown
- `GET /api/admin/analytics/top-pages?range=7d` → page list
- `GET /api/admin/admob/overview?range=30d` → total revenue, impressions, eCPM
- `GET /api/admin/admob/apps?range=30d` → per-app breakdown
- Auth: `routes/admin.py` mevcut admin auth (login gerekli) korunur
- **Commit:** `feat(admin): GA + AdMob data endpoints with Redis cache`

### Task 4.6: Admin Design System — CSS Tokens + Base 🔥
**Files:** `static/css/admin/{tokens,base}.css` (new)
**Why:** DESIGN.md OKLCH palette + typography + spacing.
**Action:**
- `tokens.css` — `:root` + `[data-theme="dark"]` + `[data-theme="light"]` + `@media (prefers-color-scheme)` default light
- Tailwind config: yeni `theme.extend.colors` mevcut `#5b2bee` → `oklch(0.48 0.20 270)` (Tailwind OKLCH 3.4+ destekli)
- `base.css` — reset, `font-feature-settings: "tnum" 1` (tabular nums), focus ring, scrollbar custom
- **Commit:** `feat(admin): design tokens + base — OKLCH palette, dark/light themes`

### Task 4.7: Admin Layout — Sidebar + Topbar 🔥
**File:** `templates/admin/layout.html`
**Why:** Yeni layout (mevcut cosmic-glow + side-stripe = anti-ref, YASAK).
**Action:**
- Sidebar 240px (lg) / 64px icon-only (sm) / bottom-sheet (mobile)
- Topbar 56px sticky: breadcrumb + period selector + theme toggle + user menu
- Main: max-width 1440px, center, 24px padding
- Tailwind `class="dark"` → mevcut, **OK**; ek olarak `data-theme` attribute localStorage override için
- **Anti-pattern temizliği:** Mevcut `cosmic-glow` class kaldır, `linear-gradient(135deg, #0a0a12, ...)` YASAK
- **Commit:** `feat(admin): layout — sidebar + topbar, anti-pattern cleanup`

### Task 4.8: Admin Theme Toggle 🔥
**File:** `static/js/admin/theme.js` (new) + `templates/admin/layout.html`
**Why:** Dark/Light tema + no-flash.
**Action:**
- Inline `<head>` script: localStorage > OS preference; `<html>` class'ı set et (no-flash)
- `theme.js`: toggle button (sun/moon icon), localStorage write, OS change listener
- Transition: 200ms `bg, color` crossfade (CSS)
- **Commit:** `feat(admin): theme toggle with localStorage + OS preference + no-flash`

### Task 4.9: Admin Components — Metric Card + Chart + Table 🔥
**Files:** `static/css/admin/components.css`, `static/js/admin/charts.js`, `templates/admin/components/*.html`
**Why:** Impeccable standardı.
**Action:**
- `metric_card.html` — display sayı + trend pill + sparkline slot
- `chart_card.html` — başlık + period toggle + chart slot
- `data_table.html` — header + body + pagination
- `period_selector.html` — Bugün/7g/30g/90g (URL sync)
- `trend_pill.html` — ▲/▼ + % + renk + icon
- `kpi_row.html` — 4 metric wrapper
- Vanilla SVG sparkline (30-60px height, son nokta primary, diğerleri faint, gradient fade to bg)
- **Anti-cliché:** pie > 5 dilim YASAK, glow halo YASAK, gradient text YASAK
- **Commit:** `feat(admin): MetricCard/ChartCard/DataTable/PeriodSelector/TrendPill components + vanilla SVG sparkline`

### Task 4.10: Admin Dashboard Page — KPI + Charts + Activity
**File:** `templates/admin/dashboard.html`
**Why:** Tüm metrikler tek sayfada, PERIOD SELECTOR ile filtrelenebilir.
**Action:**
- KPI row: Total users, Active today, Premium users, Revenue (AdMob + IAP) — 4 MetricCard
- Charts: Signup trend (line), Premium conversion (area), AdMob revenue (area), Sessions by source (bar horizontal)
- Activity feed: son 10 olay (signup, premium activation, error)
- Period selector: 7d/30g/90g (URL: `?range=30d`)
- Tüm data `routes/admin.py` üzerinden AJAX (chart render client-side vanilla SVG)
- **Commit:** `feat(admin): dashboard — KPI row, 4 charts, activity feed, period selector`

### Task 4.11: Admin PWA — Manifest + Service Worker 🔥
**Files:** `static/manifest-admin.json`, `static/sw-admin.js`, `static/all-icons/admin-*.png`
**Why:** Admin offline çalışabilir (roaming için), installable.
**Action:**
- `manifest-admin.json` — name, short_name, icons (192, 512, maskable), theme_color, background_color, display: standalone, start_url: `/admin/dashboard`
- `sw-admin.js` — cache-first for `/static/admin/*`, network-first for API, offline fallback `/admin/offline`
- `templates/admin/layout.html` — `<link rel="manifest" href="/static/manifest-admin.json">`, register SW
- Iconlar: mevcut `static/all-icons/` adapte et (PWA için 192x192 + 512x512 + maskable)
- **Commit:** `feat(admin): PWA — manifest, service worker, icons`

### Task 4.12: Admin Keyboard Shortcuts
**File:** `static/js/admin/shortcuts.js` (new)
**Why:** Power user (admin sık girip çıkar).
**Action:**
- `g d` → dashboard
- `g u` → users
- `g p` → pricing
- `g s` → stats
- `?` → cheatsheet modal
- `/` → search focus
- `t` → theme toggle
- Help modal: `templates/admin/components/shortcuts_modal.html`
- **Commit:** `feat(admin): keyboard shortcuts (g+d, g+u, ?, t)`

### Task 4.13: Admin Login
**File:** `templates/admin/login.html`
**Why:** Tema-agnostik, focus state impeccable.
**Action:**
- Centered card, brand monogram
- Email + password + "Şifremi unuttum"
- Theme toggle sağ-üst
- Anti-pattern: cosmic gradient YASAK, side-stripe YASAK
- **Commit:** `feat(admin): login — center card, brand monogram, theme-aware`

### Task 4.14: Admin Dark/Light QA
**File:** Tüm admin templates
**Why:** Her sayfa her iki temada.
**Action:**
- Tüm `text-white` → tema-agnostik (`text-ink` token)
- Tüm `bg-{color}-500` → `bg-{token}`
- Tüm gradient'ler → solid (impeccable SKILL ban)
- Tüm cosmic-glow kaldır
- **Commit:** `fix(admin): dark/light QA — remove cosmic-glow, gradient text, hardcoded white`

### Task 4.15: Firestore Admin Role Check
**File:** `firebase/firestore.rules`
**Why:** Admin dashboard veri okuması; rules server-side (admin SDK yazar zaten ama ek field-level read guard).
**Action:**
- `users/{userId}` admin read-only: `request.auth.token.admin == true`
- Bu Plan 1'in mevcut rules'ına ek
- Server-side (admin SDK) zaten bypass eder, ek rules sadece client SDK'ya özel
- **Commit:** `fix(firestore): admin role token check for client-side reads`

### Task 4.16: Build & Visual QA
**Action:**
- Local serve + admin dashboard aç
- Dark/light toggle test (konsolasız, localStorage persist)
- Lighthouse a11y score 95+
- `prefers-reduced-motion` test (DevTools → Rendering)
- Color blindness sim (DevTools → Rendering → Deficiency)
- Keyboard tab navigation test
- **Commit final:** `chore(admin): visual QA passed (a11y 95+, dark/light, reduced-motion)`

## Done Criteria

- [ ] GA4 her 3 yere (web app, landing, mobile webview) + KVKK consent
- [ ] GA4 Data API service + Redis cache
- [ ] AdMob API service + Redis cache
- [ ] Admin GA + AdMob endpoints
- [ ] OKLCH design tokens + dark/light tema + no-flash
- [ ] Admin layout (sidebar + topbar) anti-pattern temiz
- [ ] MetricCard + ChartCard + DataTable + PeriodSelector + TrendPill components
- [ ] Vanilla SVG sparkline + chart
- [ ] Admin dashboard KPI + 4 charts + activity feed
- [ ] PWA: manifest + service worker + icons
- [ ] Keyboard shortcuts (g+d, g+u, ?, t)
- [ ] Login sayfa yeniden
- [ ] Tüm admin templates dark/light QA
- [ ] Firestore admin role guard
- [ ] Lighthouse a11y 95+

## Dependencies

- Kullanıcı sağlar: GA4 Measurement ID, AdMob publisher ID + OAuth credentials
- Plan 1-3 tamamlandı
- DESIGN.md + PRODUCT.md yazıldı
- Redis mevcut
- google-analytics-data, google-ads-admob, google-auth pip install

## Test Plan

1. **Theme:** LocalStorage `orbis-theme=dark|light` set et, reload, no-flash doğrula
2. **GA4 web:** `gtag` debug mode aç, page view + custom event gönder, GA4 DebugView'da gör
3. **GA4 mobile:** Capacitor WebView, console'da `dataLayer.push({event: 'app_open'})`, GA4'te gör
4. **AdMob API:** Mock publisher_id ile revenue döner; Redis cache hit 2. istekte log
5. **A11y:** Lighthouse a11y 95+, axe DevTools clean
6. **Keyboard:** Tab navigation sırası mantıklı, `?` modal açılır
7. **Reduced motion:** OS preference `reduce` → animasyonlar instant

## Risks

- **GA4 Service Account** kullanıcı sağlar; `.gitignore` ekle
- **AdMob OAuth** refresh token + client secret; Coolify secret mount
- **Cookie consent** TR KVKK — sadece GA için değil, AdSense de kullanıyor landing
- **Real-time updates** — admin için overkill; 5dk polling (zaten heartbeat 5dk)
- **PWA service worker** — `/api/admin/*` cache YASAK, sadece static assets
- **Tailwind OKLCH** — Tailwind 3.4+ gerekli; CDN versiyonu yeterli

## Implementation Order

1. Plan 4.6 (design tokens) → 4.7 (layout) → 4.8 (theme toggle) → 4.9 (components) → 4.10 (dashboard) — **CSS + HTML foundation**
2. 4.3 (GA service) → 4.4 (AdMob service) → 4.5 (admin endpoints) — **backend data**
3. 4.1 (GA web) → 4.2 (GA mobile) — **frontend tracking**
4. 4.11 (PWA) → 4.12 (shortcuts) → 4.13 (login) → 4.14 (QA) → 4.15 (firestore) → 4.16 (build)

## Onay

Bu planı onaylarsan `ExitPlanMode` ile yürütmeye başlarım. Onay komutu: "evet başla" veya düzeltme iste.
