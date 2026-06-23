# Product

## Register

product

## Users

**Birincil:** ORBIS ekibi — geliştirici + operatör + içerik yöneticisi (1-5 kişilik ekip). Admin paneline sıklıkla giriyor; hızlı triyaj, doğru sayı, anında aksiyon istiyor.

**Bağlam:** Ofiste, dizüstü bilgisayardan; sabah-akşam arası 3-8 kez giriş. Hızlı bakış için 30 saniyeden kısa süre derin dalış için 5-15 dakika harcıyor.

**İş:** Kullanıcı sağlığını izlemek (aktif/premium/düşmüş), ödeme akışını doğrulamak, içerik/itiraz triage etmek, fiyatlandırmayı güncellemek, push kampanyaları göndermek, AI davranışını ayarlamak.

**İkincil:** Potansiyel yatırımcı/danışman — admin linki geçici paylaşılabilir, ürünün durumunu tek bakışta anlamak istiyor.

## Product Purpose

ORBIS'in Türkiye'deki astroloji + AI yorum servisinin operasyonel beyni. "Sağlıklı mı?" sorusuna 5 saniyede cevap: kullanıcı büyümesi, gelir (premium + IAP + AdMob), retention, içerik durumu.

**Başarı metrikleri:**
- Admin her sabah dashboard'u 30 saniyede okuyabilmeli
- Anomali (premium drop, error spike) ilk gün fark edilmeli
- Fiyat değişikliği / push kampanyası 30 saniyede yayına alınabilmeli

## Brand Personality

**3 kelime:** Precision · Insight · Command.

Precision — her sayı net, her grafik tutarlı renk skalası, her tablo doğru hizalanmış. "Yaklaşık" yok.
Insight — ham sayı değil, hikâye. "Bugün 12 yeni premium, son 7 günün %30 üstünde" gibi.
Command — admin kontrol hissetmeli; her eylem onaylı, geri alınabilir, audit log'lu. Uçuş kokpiti; gözlem + aksiyon, "bak ve unut" değil.

**Ton:** Astrolog operatörü düşün — gece çalışan bir gözlemci. Hızlı, sessiz, kararlı. "Tebrikler!" kutlamaları yerine sade bilgi.

**Referanslar:**
- **Linear** — sayı kartlarının ritmi, satır yoğunluğu, hotkey ağırlıklı UX
- **Stripe Dashboard** — para + gelir grafiği, metric detayı, sparkline ile trend
- **Vercel Analytics** — real-time pulse, dark/light temiz geçiş, minimal chrome
- **Astronomy tools** (Stellarium, Sky & Telescope) — koyu mavi-mor arka plan üzerinde keskin veri noktaları (referans olarak BİLİN, taklit etme)

## Anti-references

- **SaaS klişeleri YASAK:** Hero metric template (büyük sayı + küçük etiket + destekçi stats + gradient accent), gradient text, side-stripe colored border, glassmorphism default, "Tebrikler!" empty state kutlaması, 01/02/03 numbered section markers, identical card grid. İmpeccable SKILL.md'de zaten yasaklı.
- **Cosmic-astroloji klişeleri YASAK:** Yıldızlı arka plan, parlak glow halo, "mistik" nebula gradient, parlak nebula renk paleti (pembe-mor gradient), spiritüel emoji süsleme, horoscope-style "✨ Yıldızlar konuşuyor" mikro-kopya. Marka mystic değil, **modern astrolojik operasyon aracı**. Cosmic ton sadece subtle: çok koyu mavi-mor bg, keskin veri noktaları, nötr chrome.
- **Bootstrap-tarzı default admin:** Çok satırlı info banner'lar, korkunç border, generic iconlar, table overflow, 12px yazı + cramped row'lar.

## Design Principles

1. **Veri yoğunluğu = yoğunluk, çöp değil.** Bilgi hiyerarşisi net olmalı; 30 saniyede 5 metrik + trend okunabilmeli. Veri azaldığında değil arttığında kazandırır.
2. **Grafik + dinamik alanlar statik yüzeyi kırar.** Trend sparkline'lar, real-time pulse dot, mini chart'lar, status badge'ler — amaç: sayı canlı hissettirmeli. Statik kart = ölü.
3. **Hafıza yükü = 0.** Kullanıcı geçen haftaki state'i hatırlamamalı. Period seçici (Bugün/7g/30g/90g) her bölümde aynı. Karşılaştırma (vs önceki dönem) default.
4. **Profesyonel = törpülenmiş.** Mikro-kopya net, hiçbir yerde emoji süsleme yok, hiçbir yerde "magic" kelimesi yok. Bilim/operasyon dili.
5. **Aksiyon her zaman bir tık uzakta.** Her metriğin yanında "neden?" (segment drilldown) ve "ne yapmalı?" (CTA) hazır. Dashboard sadece bilgi değil, **operasyon yüzeyi**.

## Accessibility & Inclusion

- **WCAG AA** zorunlu (admin erişilebilirliği kritik, iç ekip için de gerekli)
- **Reduced motion** (prefers-reduced-motion): animasyonları crossfade/instant'a indir, sayılar yine değişir (animasyon değil, veri)
- **Color blindness:** trend yukarı/aşağı için renk + şekil (▲/▼) kombinasyonu, salt renk YASAK
- **Keyboard navigation** primary (admin sık girip çıkar, mouse yavaş)
- **Dark + light tema** eşit ağırlıkta; localStorage + OS preference (prefers-color-scheme) saygı
- **Klavye shortcut'lar:** `g d` (dashboard), `g u` (users), `g p` (pricing), `?` (cheatsheet)

## Accessibility-level WCAG AA, dark+light, color blindness safe, keyboard-first.
