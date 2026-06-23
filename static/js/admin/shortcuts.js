/**
 * ORBIS Admin — Keyboard shortcuts
 *   g d → dashboard
 *   g u → users
 *   g p → push notifications
 *   g s → statistics
 *   g i → pricing
 *   g a → AI settings
 *   ?   → cheatsheet modal
 *   t   → theme toggle
 *   /   → focus first input
 *   Esc → close modal / clear search
 */
(function () {
  'use strict';

  var ROUTES = {
    d: '/admin/dashboard',
    u: '/admin/users',
    p: '/admin/push',
    s: '/admin/stats',
    i: '/admin/pricing',
    a: '/admin/ai-settings'
  };

  var pendingPrefix = null;
  var prefixTimer = null;
  var PREFIX_TIMEOUT = 900;

  function isTyping(el) {
    if (!el) return false;
    var tag = el.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
  }

  function reset() {
    pendingPrefix = null;
    if (prefixTimer) { clearTimeout(prefixTimer); prefixTimer = null; }
  }

  function go(shortcut) {
    var path = ROUTES[shortcut];
    if (path) window.location.href = path;
  }

  function toggleTheme() {
    var btn = document.getElementById('theme-toggle');
    if (btn) btn.click();
  }

  function focusFirstInput() {
    var el = document.querySelector(
      'main input[type="search"], main input[type="text"], main input:not([type]), main textarea'
    );
    if (el) el.focus();
  }

  function showCheatsheet() {
    var existing = document.getElementById('cheatsheet-modal');
    if (existing) {
      existing.hidden = false;
      var closeBtn = existing.querySelector('button');
      if (closeBtn) closeBtn.focus();
      return;
    }
    var modal = document.createElement('div');
    modal.id = 'cheatsheet-modal';
    modal.className = 'modal-backdrop';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', 'Klavye kısayolları');
    modal.innerHTML =
      '<div class="modal" style="max-width: 480px;">' +
        '<div class="modal-head">' +
          '<h2 class="modal-title">Klavye kısayolları</h2>' +
          '<button class="icon-btn" data-close aria-label="Kapat"><span class="material-symbols-outlined">close</span></button>' +
        '</div>' +
        '<div class="modal-body">' +
          '<div class="stack-3">' +
            '<div class="row row--between"><kbd>g d</kbd><span class="text-muted" style="font-size: 13px;">Dashboard</span></div>' +
            '<div class="row row--between"><kbd>g u</kbd><span class="text-muted" style="font-size: 13px;">Kullanıcılar</span></div>' +
            '<div class="row row--between"><kbd>g p</kbd><span class="text-muted" style="font-size: 13px;">Push bildirimleri</span></div>' +
            '<div class="row row--between"><kbd>g s</kbd><span class="text-muted" style="font-size: 13px;">İstatistikler</span></div>' +
            '<div class="row row--between"><kbd>g i</kbd><span class="text-muted" style="font-size: 13px;">Fiyatlandırma</span></div>' +
            '<div class="row row--between"><kbd>g a</kbd><span class="text-muted" style="font-size: 13px;">AI ayarları</span></div>' +
            '<div class="divider"></div>' +
            '<div class="row row--between"><kbd>t</kbd><span class="text-muted" style="font-size: 13px;">Tema değiştir</span></div>' +
            '<div class="row row--between"><kbd>/</kbd><span class="text-muted" style="font-size: 13px;">Aramaya odaklan</span></div>' +
            '<div class="row row--between"><kbd>?</kbd><span class="text-muted" style="font-size: 13px;">Bu pencere</span></div>' +
            '<div class="row row--between"><kbd>Esc</kbd><span class="text-muted" style="font-size: 13px;">Kapat</span></div>' +
          '</div>' +
        '</div>' +
      '</div>';
    document.body.appendChild(modal);
    var closeFn = function () { modal.remove(); };
    modal.querySelector('[data-close]').addEventListener('click', closeFn);
    modal.addEventListener('click', function (e) { if (e.target === modal) closeFn(); });
    setTimeout(function () { var b = modal.querySelector('[data-close]'); if (b) b.focus(); }, 50);
  }

  document.addEventListener('keydown', function (e) {
    // Esc — close any open modal or clear pending prefix
    if (e.key === 'Escape') {
      var ch = document.getElementById('cheatsheet-modal');
      if (ch) { ch.remove(); return; }
      var topmost = document.querySelector('.modal-backdrop, .panel-backdrop');
      if (topmost) {
        var modal = topmost.querySelector('.modal, .panel');
        if (modal) {
          topmost.remove();
          return;
        }
      }
      reset();
      return;
    }

    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (isTyping(e.target)) return;

    if (e.key === '?') { e.preventDefault(); showCheatsheet(); return; }
    if (e.key === 't') { e.preventDefault(); toggleTheme(); return; }
    if (e.key === '/') { e.preventDefault(); focusFirstInput(); return; }
    if (e.key === 'b') {
      e.preventDefault();
      var btn = document.getElementById('sidebar-toggle');
      if (btn) btn.click();
      return;
    }

    if (pendingPrefix === 'g' && ROUTES[e.key]) {
      e.preventDefault();
      go(e.key);
      reset();
      return;
    }
    if (e.key === 'g') {
      pendingPrefix = 'g';
      prefixTimer = setTimeout(reset, PREFIX_TIMEOUT);
      return;
    }
  });
})();
