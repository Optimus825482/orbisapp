# TODO — Kalan Admin Sayfası Yenileme (Sonraki Sprint)

**Tarih:** 2026-06-23
**Durum:** Plan 4.14 yarıda — layout/dashboard/login yenilendi; users/pricing/push/stats/ai_settings sayfaları eski hâliyle (cosmic-glow + hardcoded slate-* class'ları).

## Yapılacaklar

Aşağıdaki 4 admin sayfası hâlâ eski design system kullanıyor. Layout.html yeni design tokens yüklüyor (`tokens.css`, `base.css`, `layout.css`, `components.css`) — bu sayfalarda cosmic-glow hardcoded olduğu için tema değişikliklerinde görsel bozulma olabilir.

### Etkilenen dosyalar
- `templates/admin/users.html` (508 → 200 satır, kırpılmış; yeniden yazılmalı)
- `templates/admin/pricing.html`
- `templates/admin/push.html`
- `templates/admin/stats.html`
- `templates/admin/ai_settings.html`
- `templates/admin/user_detail.html`

### Yapılması gereken
1. **users.html** — kırpılmış, komple yeniden yaz (yeni modal + table + filters).
2. **pricing.html / push.html / stats.html / ai_settings.html** — eski `glass-card` + `cosmic-glow` + `text-slate-*` Tailwind class'larını yeni `.card` + `.metric` + `.table` component class'larına çevir.
3. **user_detail.html** — `/admin/api/users/<id>` GET endpoint'i kullanır, içerik korunur; sadece görsel yenileme.

### Tahmini efor
~2-3 saat. Read/Write race condition (file-tool takılması) nedeniyle Python heredoc ile yazılması önerilir.

## Öncelik
Düşük — dashboard (en sık kullanılan sayfa) zaten yenilendi. Kalan sayfalar operatörün nadiren açtığı CRUD ekranları.

## Alternatif
Mevcut sayfalar Tailwind default `slate` paletini kullanıyor. Yeni layout body'si `bg: var(--bg)` (koyu lacivert) + `color: var(--ink)`. Slate-100 text eski `#f1f5f9` (Tailwind) — yeni `--ink` ise `oklch(0.96 0.005 260)` (çok yakın, hafif kobalt tint). **Pratikte sayfalar çalışır, sadece perfect harmony yok.** QA sonrası hızlı düzeltilebilir.
