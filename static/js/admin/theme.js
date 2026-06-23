/**
 * ORBIS Admin — Theme (light/dark)
 * - No-flash: <head> inline script sets data-theme before this loads
 * - localStorage('orbis-theme') | OS preference
 * - Fires 'orbis:themechange' event for chart re-render
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'orbis-theme';
  var root = document.documentElement;

  function current() {
    return root.getAttribute('data-theme') || 'light';
  }

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

  // Init icon/label
  function syncToggleUI(theme) {
    var btn = document.getElementById('theme-toggle');
    var icon = document.getElementById('theme-icon');
    if (icon) icon.textContent = theme === 'dark' ? 'light_mode' : 'dark_mode';
    if (btn) {
      btn.setAttribute('aria-label', theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç');
      btn.setAttribute('title', theme === 'dark' ? 'Açık tema' : 'Koyu tema');
    }
  }

  apply(current());
  syncToggleUI(current());

  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', function () {
        var next = current() === 'dark' ? 'light' : 'dark';
        apply(next);
        syncToggleUI(next);
      });
    }
  });

  // OS preference change — only if user hasn't set explicit override
  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var onOSChange = function (e) {
      var override = false;
      try { override = !!localStorage.getItem(STORAGE_KEY); } catch (err) {}
      if (!override) {
        var next = e.matches ? 'dark' : 'light';
        apply(next);
        syncToggleUI(next);
      }
    };
    if (mq.addEventListener) mq.addEventListener('change', onOSChange);
    else if (mq.addListener) mq.addListener(onOSChange);
  }
})();
