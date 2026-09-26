(function () {
  'use strict';

  var root = document.documentElement;
  var body = document.body;

  function storageGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function storageSet(key, value) {
    try { window.localStorage.setItem(key, value); } catch (e) { /* storage unavailable */ }
  }

  /* ---------- Theme toggle ---------- */
  function effectiveTheme() {
    var set = root.getAttribute('data-theme');
    if (set === 'light' || set === 'dark') return set;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function syncThemeButtons() {
    var dark = effectiveTheme() === 'dark';
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', String(dark));
      btn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
      btn.setAttribute('title', dark ? 'Light theme' : 'Dark theme');
      var sun = btn.querySelector('[data-icon="sun"]');
      var moon = btn.querySelector('[data-icon="moon"]');
      if (sun) sun.style.display = dark ? '' : 'none';
      if (moon) moon.style.display = dark ? 'none' : '';
    });
  }
  document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var next = effectiveTheme() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      storageSet('theme', next);
      syncThemeButtons();
    });
  });
  syncThemeButtons();

  /* ---------- Mobile sidebar drawer ---------- */
  var sidebar = document.getElementById('sidebar');
  var openers = document.querySelectorAll('[data-sidebar-open]');
  var closers = document.querySelectorAll('[data-sidebar-close]');
  function setSidebar(open) {
    body.classList.toggle('sidebar-open', open);
    openers.forEach(function (b) { b.setAttribute('aria-expanded', String(open)); });
    if (open && sidebar) {
      var first = sidebar.querySelector('a, button');
      if (first) first.focus();
    }
  }
  openers.forEach(function (b) { b.addEventListener('click', function () { setSidebar(true); }); });
  closers.forEach(function (b) { b.addEventListener('click', function () { setSidebar(false); }); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && body.classList.contains('sidebar-open')) {
      setSidebar(false);
      if (openers[0]) openers[0].focus();
    }
  });

  /* ---------- Toasts ---------- */
  function dismiss(toast) {
    if (!toast || toast.classList.contains('is-leaving')) return;
    toast.classList.add('is-leaving');
    window.setTimeout(function () { toast.remove(); }, 260);
  }
  document.querySelectorAll('.toast').forEach(function (toast) {
    var close = toast.querySelector('.toast-close');
    if (close) close.addEventListener('click', function () { dismiss(toast); });
    // Errors stay until dismissed; everything else fades on its own.
    if (!toast.classList.contains('toast-error')) {
      var timer = window.setTimeout(function () { dismiss(toast); }, 6000);
      toast.addEventListener('mouseenter', function () { window.clearTimeout(timer); });
    }
  });

  /* ---------- Avatars: initials + stable tone from the name ---------- */
  function hash(str) {
    var h = 0;
    for (var i = 0; i < str.length; i++) { h = (h * 31 + str.charCodeAt(i)) | 0; }
    return Math.abs(h);
  }
  document.querySelectorAll('[data-name]').forEach(function (el) {
    var name = (el.getAttribute('data-name') || '').trim();
    if (!name) return;
    el.setAttribute('data-tone', String((hash(name) % 5) + 1));
    if (el.hasAttribute('data-initials')) {
      var parts = name.split(/[\s._-]+/).filter(Boolean);
      var initials = parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2);
      el.textContent = initials.toUpperCase();
    }
  });

  /* ---------- Submit feedback: spinner + no double submits ---------- */
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (form.hasAttribute('data-no-loading')) return;
    if (form.dataset.submitting === '1') { e.preventDefault(); return; }
    form.dataset.submitting = '1';
    var btn = e.submitter || form.querySelector('button[type="submit"], button:not([type])');
    if (btn && btn.classList.contains('btn')) btn.classList.add('is-loading');
    // Re-enable if the page is restored from the back/forward cache.
    window.addEventListener('pageshow', function () {
      form.dataset.submitting = '';
      if (btn) btn.classList.remove('is-loading');
    }, { once: true });
  });

  /* ---------- Native <dialog> helpers ---------- */
  document.querySelectorAll('[data-dialog-open]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var dialog = document.getElementById(btn.getAttribute('data-dialog-open'));
      if (!dialog || typeof dialog.showModal !== 'function') return;
      dialog.showModal();
      var focusTarget = dialog.querySelector('[autofocus], textarea, input:not([type="hidden"])');
      if (focusTarget) focusTarget.focus();
    });
  });
  document.querySelectorAll('dialog').forEach(function (dialog) {
    dialog.querySelectorAll('[data-dialog-close]').forEach(function (btn) {
      btn.addEventListener('click', function () { dialog.close(); });
    });
    // Click on the backdrop closes the dialog.
    dialog.addEventListener('click', function (e) {
      if (e.target === dialog) dialog.close();
    });
  });

  /* ---------- Auto-submit selects ---------- */
  document.querySelectorAll('select[data-autosubmit]').forEach(function (select) {
    select.addEventListener('change', function () {
      if (select.form) select.form.requestSubmit ? select.form.requestSubmit() : select.form.submit();
    });
  });

  /* ---------- Chat: scroll to latest, Cmd/Ctrl+Enter to send, autogrow ---------- */
  var thread = document.querySelector('[data-chat-thread]');
  if (thread) thread.scrollTop = thread.scrollHeight;
  document.querySelectorAll('[data-composer] textarea').forEach(function (ta) {
    function grow() {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
    }
    ta.addEventListener('input', grow);
    ta.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && ta.form) {
        e.preventDefault();
        ta.form.requestSubmit ? ta.form.requestSubmit() : ta.form.submit();
      }
    });
  });
})();
