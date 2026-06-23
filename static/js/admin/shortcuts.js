/**
 * ORBIS Admin — Keyboard shortcuts
 * g d  → dashboard
 * g u  → users
 * g p  → push notifications (and pricing short alias: g i)
 * g s  → statistics
 * ?    → cheatsheet modal
 * t    → theme toggle
 * /    → focus first input on page
 * Esc  → close any open modal
 */
(function () {
  'use strict';

  var ROUTES = {
    d: '/admin/dashboard',
    u: '/admin/users',
    p: '/admin/push',
    s: '/admin/statistics',
    i: '/admin/pricing',
    a: '/admin/ai-settings'
  };

  var pendingPrefix = null;
  var prefixTimer = null;

  function isTypingInForm(el) {
    if (!el) return false;
    var tag = el.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
  }

  function goto(shortcut) {
    var path = ROUTES[shortcut];
    if (path) window.location.href = path;
  }

  function toggleTheme() {
    var btn = document.getElementById('theme-toggle');
    if (btn) btn.click();
  }

  function focusFirstInput() {
    var el = document.querySelector('.admin-content input[type="text"], .admin-content input[type="search"], .admin-content input:not([type]), .admin-content textarea');
    if (el) el.focus();
  }

  function showCheatsheet() {
    var existing = document.getElementById('cheatsheet-modal');
    if (existing) {
      existing.classList.add('is-visible');
      existing.querySelector('button, [tabindex]')?.focus();
      return;
    }
    var modal = document.createElement('div');
    modal.id = 'cheatsheet-modal';
    modal.className = 'modal-backdrop';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-label', 'Klavye kısayolları');
    modal.innerHTML =
      '<div class="modal" style="max-width: 480px;">' +
        '<header class="modal-head">' +
          '<h2 class="modal-title">Klavye Kısayolları</h2>' +
          '<button class="icon-btn icon-btn--ghost" data-close type="button" aria-label="Kapat">' +
            '<span class="material-symbols-outlined">close</span>' +
          '</button>' +
        '</header>' +
        '<div class="modal-body">' +
          '<dl class="shortcut-list">' +
            shortcutsHtml() +
          '</dl>' +
        '</div>' +
      '</div>';
    document.body.appendChild(modal);
    // Trigger transition
    requestAnimationFrame(function () { modal.classList.add('is-visible'); });
    modal.addEventListener('click', function (e) {
      if (e.target === modal || e.target.hasAttribute('data-close')) {
        hideCheatsheet();
      }
    });
  }

  function shortcutsHtml() {
    var rows = [
      ['g d', 'Dashboard'],
      ['g u', 'Kullanıcılar'],
      ['g p', 'Push Bildirimleri'],
      ['g s', 'İstatistikler'],
      ['g i', 'Fiyat Yönetimi'],
      ['g a', 'AI Yapılandırma'],
      ['t', 'Tema değiştir'],
      ['/', 'Sayfadaki ilk input\'a odaklan'],
      ['?', 'Bu kısayollar listesi']
    ];
    return rows.map(function (r) {
      return '<div class="shortcut-row"><kbd>' + r[0] + '</kbd><span>' + r[1] + '</span></div>';
    }).join('');
  }

  function hideCheatsheet() {
    var m = document.getElementById('cheatsheet-modal');
    if (!m) return;
    m.classList.remove('is-visible');
    setTimeout(function () { m.remove(); }, 200);
  }

  document.addEventListener('keydown', function (e) {
    // Esc — always close modal
    if (e.key === 'Escape') {
      hideCheatsheet();
      return;
    }

    if (isTypingInForm(e.target)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;

    // Single-key shortcuts
    if (e.key === '?') {
      e.preventDefault();
      showCheatsheet();
      return;
    }
    if (e.key === 't') {
      e.preventDefault();
      toggleTheme();
      return;
    }
    if (e.key === '/') {
      e.preventDefault();
      focusFirstInput();
      return;
    }

    // Two-key sequences (g + letter)
    if (pendingPrefix === 'g') {
      if (ROUTES[e.key]) {
        e.preventDefault();
        goto(e.key);
      }
      pendingPrefix = null;
      if (prefixTimer) clearTimeout(prefixTimer);
      return;
    }

    if (e.key === 'g') {
      pendingPrefix = 'g';
      if (prefixTimer) clearTimeout(prefixTimer);
      prefixTimer = setTimeout(function () { pendingPrefix = null; }, 1200);
      return;
    }
  });
})();
