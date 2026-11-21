(function () {
  'use strict';

  var STORAGE_KEY = 'blog-theme';
  var DEFAULT_THEME = 'dark';
  var root = document.documentElement;

  function getStoredTheme() {
    try {
      var val = localStorage.getItem(STORAGE_KEY);
      return val === 'dark' || val === 'light' ? val : null;
    } catch (e) {
      return null;
    }
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      // Ignore storage errors in restricted browsing contexts
    }
  }

  function getCurrentTheme() {
    var current = root.dataset.theme;
    if (current === 'dark' || current === 'light') {
      return current;
    }
    return getStoredTheme() || DEFAULT_THEME;
  }

  function syncToggleButtons(theme) {
    var isDark = theme === 'dark';
    var buttons = document.querySelectorAll('[data-theme-toggle]');
    buttons.forEach(function (btn) {
      btn.setAttribute('aria-pressed', isDark ? 'true' : 'false');
      btn.setAttribute('aria-label', isDark ? '切换到浅色模式' : '切换到深色模式');
      btn.setAttribute('title', isDark ? '切换到浅色模式' : '切换到深色模式');
    });
  }

  function applyTheme(theme, persist) {
    var resolved = theme === 'light' ? 'light' : 'dark';
    root.dataset.theme = resolved;
    if (persist) {
      saveTheme(resolved);
    }
    syncToggleButtons(resolved);
  }

  function initTheme() {
    var initial = getStoredTheme() || getCurrentTheme() || DEFAULT_THEME;
    applyTheme(initial, false);

    document.addEventListener('click', function (event) {
      var toggle = event.target.closest('[data-theme-toggle]');
      if (!toggle) {
        return;
      }
      var nextTheme = getCurrentTheme() === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme, true);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme);
  } else {
    initTheme();
  }
})();
