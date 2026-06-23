# Design

## Register

product (admin dashboard) — design serves the product.

## Brand

ORBIS Admin: **modern astrolojik operasyon aracı**. Mystic değil; pre-dawn observatory — koyu mavi-mor zemin, keskin veri noktaları, sıfır dekorasyon.

## Brand Seed

- **oklch(0.400 0.130 260.0)** — kobalt indigo, "cold instrument blue, star-chart precision"
- Primary hue **±10°** içinde (260 ± 10° = 250-270°, kobalt → indigo → ultramarin)

## Mood (1 cümle)

> Pre-dawn observatory; operatör tek başına, soğuk kahve yanında, monitör mavi-mor bir boşlukta. Veri noktaları yıldız gibi keskin, sıfır dekorasyon, her piksel iş başında.

## Color Strategy

**Restrained** — tinted neutrals + primary 30-60% yüzey + accent %5-10. Tinted chroma 0.005-0.015 toward brand hue (260°).

> Mevcut sistem primary `#5b2bee` (mor) + accent `#38bdf8` (cyan). Yeni palette bunları OKLCH'e taşır, chroma/luminance'i tighten eder. Mevcut cosmic-glow gradient YASAK (anti-ref: cosmic-astroloji klişesi).

## Palette (OKLCH)

### Light theme

| Role | OKLCH | Notlar |
|------|-------|--------|
| `bg` | `oklch(0.985 0.003 260)` | pure'a yakın, hafif kobalt tint |
| `surface` | `oklch(0.965 0.004 260)` | kart arka planı |
| `surface-2` | `oklch(0.940 0.005 260)` | hover, iç içe kart |
| `ink` | `oklch(0.180 0.020 260)` | ana metin — body |
| `ink-muted` | `oklch(0.460 0.010 260)` | açıklama, label |
| `ink-faint` | `oklch(0.620 0.008 260)` | placeholder, border |
| `primary` | `oklch(0.480 0.200 270)` | **action, link, focus** — kobalt-indigo |
| `primary-soft` | `oklch(0.940 0.040 270)` | primary tint bg |
| `accent` | `oklch(0.720 0.130 215)` | **trends, secondary highlight** — cyan |
| `success` | `oklch(0.620 0.150 145)` | +% artış |
| `warning` | `oklch(0.720 0.150 75)` | dikkat |
| `danger` | `oklch(0.560 0.200 25)` | düşüş, hata |
| `border` | `oklch(0.910 0.005 260)` | ince ayraç |
| `border-strong` | `oklch(0.840 0.006 260)` | tablo başlık altı |

### Dark theme

| Role | OKLCH | Notlar |
|------|-------|--------|
| `bg` | `oklch(0.140 0.010 260)` | koyu kobalt, "boşluk" |
| `surface` | `oklch(0.180 0.012 260)` | kart |
| `surface-2` | `oklch(0.220 0.014 260)` | hover |
| `ink` | `oklch(0.960 0.005 260)` | ana metin |
| `ink-muted` | `oklch(0.720 0.008 260)` | açıklama |
| `ink-faint` | `oklch(0.500 0.010 260)` | placeholder |
| `primary` | `oklch(0.640 0.180 270)` | **action** — biraz daha parlak |
| `primary-soft` | `oklch(0.260 0.080 270)` | tint bg |
| `accent` | `oklch(0.760 0.130 215)` | cyan |
| `success` | `oklch(0.720 0.160 145)` | |
| `warning` | `oklch(0.780 0.150 75)` | |
| `danger` | `oklch(0.660 0.200 25)` | |
| `border` | `oklch(0.280 0.012 260)` | |
| `border-strong` | `oklch(0.360 0.014 260)` | |

**Trend renkler hem şekil hem renk taşır:** ▲/▼ + icon + renk. Salt renk yasak (color-blind safe).

## Typography

### Font stacks
- **Display (başlık, hero):** `Space Grotesk` — geometric, cold, technical, orta-geniş (marka ruhu: instrument)
- **Sans (body, UI):** `Inter` — proven, okunaklı, 0.5-2.5x arası temiz (data-heavy UI için ideal)
- **Mono (sayı, kod, veri noktası):** `JetBrains Mono` — fixed-width, sayılar hizalanır (KRİTİK: tablo sayıları mono olmalı, Inter'da "1" ve "7" farklı genişlikte hizalanmaz)

Mevcut `Spline Sans` Display olarak var; Space Grotesk'a değiştir (daha technical, daha az "AI-yumuşak").

### Scale (clamp, mobile-first)

| Token | Light/Dark | Use |
|-------|-----------|-----|
| `text-xs` | 11px / 12px | micro label, badge |
| `text-sm` | 13px | tablo body, label |
| `text-base` | 14px | body |
| `text-md` | 15px | primary button |
| `text-lg` | 17px | section heading h4 |
| `text-xl` | 20px | card title h3 |
| `text-2xl` | 24px | h2 |
| `text-3xl` | clamp(1.5rem, 2vw, 1.875rem) | metric value (büyük sayı) |
| `text-display` | clamp(1.75rem, 3vw, 2.25rem) | page title h1 |

Display h1 `text-wrap: balance`, body `text-wrap: pretty`.

### Weights
- Body: 400
- Label: 500
- Sayı/başlık: 600 (tabular-nums aktif)
- Display: 700

## Spacing

4px grid. Tokenlar:
- `space-1` 4px
- `space-2` 8px
- `space-3` 12px
- `space-4` 16px (default)
- `space-5` 20px
- `space-6` 24px (card padding)
- `space-8` 32px (section gap)
- `space-10` 40px
- `space-12` 48px (page gap)

Section arası **8-12** (rhythm); card içi **6**; metin arası **2-3**.

## Radius

- `radius-sm` 6px (badge, tag)
- `radius-md` 10px (button, input)
- `radius-lg` 14px (card)
- `radius-xl` 18px (hero card)
- `radius-full` (avatar, dot)

Yumuşak köşe (10-14) — köşeli değil, ama "bebek yumuşak" da değil. Instrument tarzı.

## Border

1px, `border` token. Tablo hücreleri **sadece satır altı** ince border (vertical değil); kartlar **sadece üst + yan + alt** 1px (iç içe kart YASAK). Side-stripe border YASAK (impeccable SKILL absolute ban).

## Shadow (dark theme)

- `shadow-sm` — kartlar: `0 1px 2px rgba(0,0,0,0.4)`
- `shadow-md` — hover: `0 4px 12px rgba(0,0,0,0.5)`
- `shadow-lg` — modal: `0 12px 32px rgba(0,0,0,0.6)`
- `glow-primary` — primary button: `0 0 0 1px primary, 0 4px 16px primary/30`

Light theme:
- `shadow-sm` `0 1px 2px rgba(0,0,0,0.05)`
- `shadow-md` `0 4px 12px rgba(0,0,0,0.08)`

## Motion

- **Default easing:** `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out-quint, no bounce)
- **Default duration:** 180ms (UI), 320ms (page transition)
- **Reduced motion:** crossfade veya instant, `prefers-reduced-motion: reduce` zorunlu
- **Number animation:** tween 600ms (mevcut sayı → yeni sayı); sparkle yok, sadece smooth count
- **Stagger reveal:** her sayfa ilk açılışta card'lar **tek tek** 80ms stagger (uniform reflex YASAK — her card kendi delay'i)

## Layout

- **Grid:** `auto-fit minmax(280px, 1fr)` responsive (no breakpoint)
- **Page layout:** Sidebar 240px (lg) + main 1fr; topbar 56px sticky
- **Sidebar:** collapsible (default açık); mobile bottom-sheet
- **Density mode:** default **comfortable** (row 48px); **compact** toggle (row 36px) — power user için
- **Z-index scale:** dropdown 100, sticky 200, modal-backdrop 900, modal 1000, toast 1100, tooltip 1200. Keyfi 999 YASAK.

## Components (admin'e özel)

### MetricCard
- Büyük sayı (display font, tabular-nums, ink)
- Label üst (xs, ink-muted, uppercase, **trk-wider** — sadece label için OK)
- Trend pill: ▲/▼ + yüzde + accent/success/danger (şekil + renk)
- Sparkline (60px height) alt
- Hover: `surface-2` + shadow-md
- CTA: "Detay →" sağ-alt köşe, primary renkte

### ChartCard
- Başlık (md, ink)
- Subtitle (sm, ink-muted)
- Time-range toggle (Bugün/7g/30g/90g)
- Chart — Area + line, gradient fade to bg (anti-cliché: line + bar mix değil)
- Legend sağ-alt, dot + label, renkler primary/accent

### DataTable
- Header: sm, ink-muted, uppercase, ink-muted bg
- Row: 48px default, hover surface-2
- Cell: mono (sayı), sans (text)
- Satır altı 1px border (vertical YOK)
- Sortable: sütun başlığı tıklanabilir, ▼/▲ icon
- Pagination: 25/50/100, sık kullanılan 50 default
- Empty state: **görsel değil, bilgi** — neden boş + ne yapmalı

### PeriodSelector
- 4 segment: Bugün / 7g / 30g / 90g
- Aktif: surface-2 + ink
- Pasif: ink-muted, hover ink
- URL sync: `?range=7d` (deep link)

### TrendPill
- ▲/▼ + yüzde + sayı + accent (up) / danger (down)
- Mono font, tabular-nums
- **Renk + şekil + icon** (color-blind safe)

### KpiRow
- 4 MetricCard, grid 1fr 1fr 1fr 1fr (lg) → 2x2 (md) → 1x4 (sm)
- Card arası space-6

### Chart
- Recharts / ApexCharts (mobil PWA'da hafif — vanilla SVG tercih)
- Area + line + dot (last point primary, diğerleri faint)
- Y-axis: hidden, sadece ilk + son değer label
- X-axis: tarih, ink-faint, sm
- Hover: crosshair + tooltip (surface, shadow-lg)

## Data Viz Rules (anti-cliché)

- **Gradient text** YASAK
- **Glow halo** YASAK (sadece primary button focus glow OK)
- **Pie chart** YASAK (kafa karıştırır) — donut + sayı ortada OK
- **3D chart** YASAK
- **Pie / donut > 5 dilim** YASAK → "Diğer" birleştir
- **Sparkline minimum 30px height** (okunabilir trend)

## Reduced Motion

Tüm `transition` ve `animation` CSS'lerinde:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```
Number tween'ler **direkt instant set** (crossfade yeterli).

## Theme Toggle

- **localStorage** key: `orbis-theme` (`dark` | `light`)
- Default: `prefers-color-scheme` izle, override > default
- Toggle: topbar sağ, sun/moon icon
- Transition: 200ms bg + ink crossfade
- **No flash of wrong theme**: `<head>` inline script:
  ```js
  const t = localStorage.getItem('orbis-theme') ||
    (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.classList.add(t);
  ```

## Live Mode Config

`.impeccable/live/config.json` Step 6'da yazılacak (live mode browser iteration için). Şimdilik Step 6 atlandı (DESIGN.md yeterli init için).

## Accessibility

- **Focus ring:** `outline: 2px solid primary; outline-offset: 2px` (her interaktif element)
- **Skip link:** "İçeriğe geç" — ilk focus'ta
- **Landmarks:** `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>` semantik
- **Heading order:** h1 (page) → h2 (section) → h3 (card title) **asla atlama yok**
- **Table:** `<th scope="col">` zorunlu
- **Form:** her input'un label'ı, hata mesajı `aria-describedby` ile
- **Live region:** toast + metric update için `aria-live="polite"`

## File Structure (admin)

```
templates/admin/
├── layout.html              # base + sidebar + topbar + theme toggle
├── login.html
├── dashboard.html           # KPI row + charts + activity feed
├── users.html
├── user_detail.html
├── pricing.html
├── push.html
├── stats.html
├── ai_settings.html
└── components/
    ├── metric_card.html     # jinja macro
    ├── chart_card.html
    ├── data_table.html
    ├── period_selector.html
    ├── trend_pill.html
    └── kpi_row.html

static/css/admin/
├── tokens.css               # CSS custom properties (light + dark)
├── base.css                 # reset, typography, focus
├── layout.css               # sidebar, topbar, grid
├── components.css           # metric card, chart card, table
└── motion.css               # transitions, reduced motion

static/js/admin/
├── theme.js                 # toggle + localStorage + OS preference
├── shortcuts.js             # keyboard shortcuts
└── charts.js                # vanilla SVG sparkline + chart
```

## Out of Scope (anti-patterns YASAK)

- Mermaid diagram, NetworkX graph (admin sade, grafik değil)
- Confetti / sparkle (veri sayıları animasyonlu olur, eğlence değil)
- Tutorial overlay, coachmark (admin power user — feature discovery için, walkthrough değil)
- Notification bell (push notification farklı feature)
