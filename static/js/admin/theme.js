/**
 * ORBIS Admin — Theme toggle
 * localStorage('orbis-theme') | OS preference (prefers-color-scheme)
 * No-flash: <head> inline script sets data-theme before this loads.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'orbis-theme';
  var root = document.documentElement;
  var btn = document.getElementById('theme-toggle');
  var icon = document.getElementById('theme-icon');

  function current() {
    return root.getAttribute('data-theme') || 'light';
  }

  function apply(theme) {
    root.setAttribute('data-theme', theme);
    root.style.colorScheme = theme;
    try { localStorage.setItem(STORAGE_KEY, theme); } catch (e) {}
    if (icon) {
      icon.textContent = theme === 'dark' ? 'light_mode' : 'dark_mode';
    }
    if (btn) {
      btn.setAttribute('aria-label', theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç');
    }
    // Notify charts (re-render with new theme colors)
    document.dispatchEvent(new CustomEvent('orbis:themechange', { detail: { theme: theme } }));
  }

  // Initialize icon + label for the current theme
  apply(current());

  if (btn) {
    btn.addEventListener('click', function () {
      apply(current() === 'dark' ? 'light' : 'dark');
    });
  }

  // OS preference change — only if user hasn't set explicit override
  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var listener = function (e) {
      var hasOverride = false;
      try { hasOverride = !!localStorage.getItem(STORAGE_KEY); } catch (err) {}
      if (!hasOverride) {
        apply(e.matches ? 'dark' : 'light');
      }
    };
    if (mq.addEventListener) mq.addEventListener('change', listener);
    else if (mq.addListener) mq.addListener(listener);
  }
})();
