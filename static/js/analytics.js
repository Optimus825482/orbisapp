/**
 * ORBIS Analytics — GA4 + KVKK consent
 * Web PWA + landing'de çalışır. Mobile WebView gtag'ı native plugin üzerinden yapar.
 *
 * Flow:
 *  1. localStorage 'orbis_ga_consent' kontrol et.
 *  2. Yoksa banner göster ("İzin Ver" / "Reddet").
 *  3. İzin varsa gtag snippet yükle, page view + custom events push.
 *  4. Consent değişince sayfayı yenile (cookie state reset).
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'orbis_ga_consent';
  var MEASUREMENT_ID = window.ORBIS_GA4_ID || null;

  function hasConsent() {
    try { return localStorage.getItem(STORAGE_KEY) === 'granted'; }
    catch (e) { return false; }
  }

  function setConsent(state) {
    try { localStorage.setItem(STORAGE_KEY, state); } catch (e) {}
  }

  function loadGA4() {
    if (!MEASUREMENT_ID) return;
    if (typeof window.gtag === 'function') return; // already loaded

    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', MEASUREMENT_ID, {
      send_page_view: true,
      anonymize_ip: true,
      cookie_flags: 'SameSite=None;Secure',
    });

    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(MEASUREMENT_ID);
    s.onerror = function () { console.warn('[analytics] gtag load failed'); };
    document.head.appendChild(s);
  }

  function ensureBanner() {
    if (document.getElementById('orbis-cookie-banner')) return;
    var banner = document.createElement('div');
    banner.id = 'orbis-cookie-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Çerez tercihleri');
    banner.style.cssText = [
      'position: fixed', 'bottom: 16px', 'left: 16px', 'right: 16px',
      'max-width: 520px', 'margin: 0 auto',
      'background: var(--surface, #1a1a24)',
      'color: var(--ink, #f5f5f8)',
      'border: 1px solid var(--border, #2a2a3a)',
      'border-radius: 14px',
      'padding: 16px 20px',
      'display: flex', 'align-items: center', 'gap: 16px',
      'box-shadow: 0 12px 32px rgba(0,0,0,0.4)',
      'z-index: 1100',
      'font: 14px/1.5 Inter, system-ui, sans-serif',
    ].join(';');
    banner.innerHTML =
      '<div style="flex:1;">' +
        '<strong style="display:block;margin-bottom:2px;font-size:14px;">Çerez & Analitik</strong>' +
        '<span style="font-size:13px;opacity:0.8;">Google Analytics 4 ile anonimleştirilmiş kullanım verisi topluyoruz. İzin veriyor musun? (KVKK uyumlu)</span>' +
      '</div>' +
      '<button data-consent="denied" type="button" style="' +
        'background:transparent;color:inherit;border:1px solid currentColor;' +
        'padding:6px 12px;border-radius:8px;font-size:13px;cursor:pointer;">Reddet</button>' +
      '<button data-consent="granted" type="button" style="' +
        'background:#5b2bee;color:#fff;border:0;padding:6px 14px;' +
        'border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;">İzin Ver</button>';
    document.body.appendChild(banner);
    banner.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-consent]');
      if (!btn) return;
      var state = btn.getAttribute('data-consent');
      setConsent(state);
      banner.remove();
      if (state === 'granted') loadGA4();
    });
  }

  // Public API
  window.OrbisAnalytics = {
    /** Custom event gönder (consent granted ise). */
    event: function (name, params) {
      if (!hasConsent() || !MEASUREMENT_ID) return;
      if (typeof window.gtag === 'function') {
        window.gtag('event', name, params || {});
      }
    },
    /** Page view (SPA navigasyon). */
    pageview: function (path, title) {
      if (!hasConsent() || !MEASUREMENT_ID) return;
      if (typeof window.gtag === 'function') {
        window.gtag('event', 'page_view', {
          page_path: path || location.pathname,
          page_title: title || document.title,
        });
      }
    },
    /** Consent durumunu değiştir (örn. footer linki). */
    revoke: function () {
      setConsent('denied');
      // reload to drop gtag state
      location.reload();
    },
    /** True if user granted analytics consent. */
    hasConsent: hasConsent,
  };

  // Boot
  document.addEventListener('DOMContentLoaded', function () {
    if (hasConsent()) {
      loadGA4();
    } else {
      // Banner'ı sayfa yüklendikten 1.5s sonra göster (UX)
      setTimeout(ensureBanner, 1500);
    }
  });
})();
