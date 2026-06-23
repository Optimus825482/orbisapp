/**
 * ORBIS Admin — Theme (light only)
 * Glassmorphism sadece light tema destekler (cam efekt light'ta daha iyi).
 * - No-flash: <head> inline script data-theme=light yapıyor
 * - Fires 'orbis:themechange' event for chart re-render
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'orbis-theme';
  var root = document.documentElement;

  function apply(theme) {
    root.setAttribute('data-theme', theme);
    root.style.colorScheme = theme;
    try { localStorage.setItem(STORAGE_KEY, theme); } catch (e) {}
    var meta = document.querySelector('meta[name="theme-color"]:not([data-keep])');
    if (!meta) {
      meta = document.createElement('meta');
      meta.setAttribute('name', 'theme-color');
      meta.setAttribute('data-keep', '1');
      document.head.appendChild(meta);
    }
    meta.setAttribute('content', theme === 'dark' ? '#0E0E10' : '#FAFAF7');
    document.dispatchEvent(new CustomEvent('orbis:themechange', { detail: { theme: theme } }));
  }

  // Init: light-only (modern glassmorphism aesthetic)
  apply('light');
})();
