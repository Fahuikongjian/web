(function () {
  'use strict';

  var GAMES = {
    '2048': 'game2048',
    snake: 'snake',
    minesweeper: 'minesweeper',
    breakout: 'breakout'
  };

  function prefersReducedMotion() {
    return Boolean(
      window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  function initGamesArcade() {
    var tabsContainer = document.querySelector('[data-game-tabs]');
    var stage = document.querySelector('[data-game-stage]');
    if (!tabsContainer || !stage) return;

    var indicator = tabsContainer.querySelector('[data-game-indicator]');
    var tabs = Array.prototype.slice.call(tabsContainer.querySelectorAll('[data-game-id]'));
    var activeId = '';
    var activeModule = null;

    function findTab(gameId) {
      for (var i = 0; i < tabs.length; i++) {
        if ((tabs[i].dataset.gameId || '').trim() === gameId) {
          return tabs[i];
        }
      }
      return null;
    }

    function positionIndicator(tab, immediate, scrollIntoView) {
      if (!indicator || !tab) return;
      if (immediate) {
        tabsContainer.classList.add('is-initializing');
      }
      indicator.style.transform = 'translate3d(' + tab.offsetLeft + 'px, 0, 0)';
      indicator.style.width = tab.offsetWidth + 'px';
      indicator.classList.add('is-ready');
      tabsContainer.classList.add('has-indicator');

      if (immediate) {
        void indicator.offsetWidth;
        window.requestAnimationFrame(function () {
          tabsContainer.classList.remove('is-initializing');
        });
      }
      if (scrollIntoView && typeof tab.scrollIntoView === 'function') {
        tab.scrollIntoView({
          behavior: prefersReducedMotion() ? 'auto' : 'smooth',
          block: 'nearest',
          inline: 'nearest'
        });
      }
    }

    function syncUrl(gameId) {
      if (!window.history || typeof window.history.replaceState !== 'function') return;
      var url = new URL(window.location.href);
      if (gameId === '2048') {
        url.searchParams.delete('game');
      } else {
        url.searchParams.set('game', gameId);
      }
      window.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }

    function selectGame(requestedId, options) {
      var opts = options || {};
      var gameId = Object.prototype.hasOwnProperty.call(GAMES, requestedId) ? requestedId : '2048';
      var tab = findTab(gameId) || tabs[0];
      if (!tab) return;

      tabs.forEach(function (item) {
        var isCurrent = item === tab;
        item.classList.toggle('is-active', isCurrent);
        item.setAttribute('aria-selected', isCurrent ? 'true' : 'false');
      });
      positionIndicator(tab, Boolean(opts.immediateIndicator), Boolean(opts.scrollIntoView));

      if (gameId !== activeId) {
        if (activeModule && typeof activeModule.unmount === 'function') {
          activeModule.unmount();
        }
        stage.replaceChildren();
        activeId = gameId;

        var registry = window.StarloopGames || {};
        var modKey = GAMES[gameId];
        var nextModule = registry[modKey] || null;
        activeModule = nextModule;
        if (nextModule && typeof nextModule.mount === 'function') {
          nextModule.mount(stage);
        }
      }

      if (opts.syncUrl) {
        syncUrl(gameId);
      }
    }

    tabsContainer.addEventListener('click', function (event) {
      var btn = event.target.closest('[data-game-id]');
      if (!btn) return;
      event.preventDefault();
      selectGame(btn.dataset.gameId || '2048', {
        syncUrl: true,
        immediateIndicator: false,
        scrollIntoView: true
      });
    });

    tabsContainer.addEventListener('keydown', function (event) {
      var current = event.target.closest('[data-game-id]');
      if (!current) return;
      var idx = tabs.indexOf(current);
      if (idx === -1) return;

      var nextIdx = -1;
      if (event.key === 'ArrowRight') {
        nextIdx = (idx + 1) % tabs.length;
      } else if (event.key === 'ArrowLeft') {
        nextIdx = (idx - 1 + tabs.length) % tabs.length;
      } else if (event.key === 'Home') {
        nextIdx = 0;
      } else if (event.key === 'End') {
        nextIdx = tabs.length - 1;
      }

      if (nextIdx !== -1) {
        event.preventDefault();
        var nextTab = tabs[nextIdx];
        nextTab.focus();
        selectGame(nextTab.dataset.gameId || '2048', {
          syncUrl: true,
          immediateIndicator: false,
          scrollIntoView: true
        });
      }
    });

    function repositionCurrent() {
      var currentTab = findTab(activeId) || tabs[0];
      if (currentTab) positionIndicator(currentTab, true, false);
    }

    if ('ResizeObserver' in window) {
      var ro = new ResizeObserver(repositionCurrent);
      ro.observe(tabsContainer);
      tabs.forEach(function (tab) { ro.observe(tab); });
    } else {
      window.addEventListener('resize', repositionCurrent, { passive: true });
    }

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(repositionCurrent);
    }

    if ('MutationObserver' in window) {
      var themeObserver = new MutationObserver(function () {
        if (activeModule && typeof activeModule.onThemeChange === 'function') {
          activeModule.onThemeChange();
        }
      });
      themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
      });
    }

    var params = new URLSearchParams(window.location.search);
    var initialGame = (params.get('game') || '2048').trim().toLowerCase();
    selectGame(initialGame, {
      syncUrl: false,
      immediateIndicator: true,
      scrollIntoView: initialGame !== '2048'
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGamesArcade);
  } else {
    initGamesArcade();
  }
})();
