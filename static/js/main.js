(function () {
  'use strict';

  function initMobileDrawer() {
    var drawer = document.querySelector('[data-mobile-drawer]');
    var toggleBtn = document.querySelector('[data-mobile-menu-toggle]');
    if (!drawer || !toggleBtn) return;
    var mobile = window.matchMedia('(max-width: 720px)');
    var siteBrand = document.querySelector('.site-brand');

    toggleBtn.addEventListener('click', function () {
      drawer.showModal();
      toggleBtn.setAttribute('aria-expanded', 'true');
    });

    drawer.addEventListener('click', function (event) {
      if (event.target === drawer || event.target.closest('[data-mobile-drawer-close], .mobile-nav-link')) {
        drawer.close();
      }
    });

    drawer.addEventListener('close', function () {
      toggleBtn.setAttribute('aria-expanded', 'false');
      if (!mobile.matches && !document.querySelector('[data-search-modal][open]')) {
        siteBrand.focus({ preventScroll: true });
      }
    });

    mobile.addEventListener('change', function () {
      if (!mobile.matches && drawer.open) drawer.close();
    });
  }

  function parseTagsCsv(raw) {
    if (!raw) return [];
    return raw
      .split(',')
      .map(function (t) {
        return t.trim();
      })
      .filter(Boolean);
  }

  function initArticleTagFilter() {
    var listContainer = document.querySelector('[data-articles-list]');
    if (!listContainer) return;

    var rows = Array.prototype.slice.call(listContainer.querySelectorAll('[data-tags]'));
    var filterButtons = Array.prototype.slice.call(document.querySelectorAll('.filter-pills [data-filter-tag]'));
    var countEl = document.querySelector('[data-articles-count]') || document.querySelector('.articles-count');
    var emptyEl = document.querySelector('[data-articles-empty]');

    function syncUrlQuery(tag) {
      if (!window.history || typeof window.history.replaceState !== 'function') {
        return;
      }
      var url = new URL(window.location.href);
      if (!tag || tag === 'all') {
        url.searchParams.delete('tag');
      } else {
        url.searchParams.set('tag', tag);
      }
      window.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }

    function applyFilter(rawTag, shouldSyncUrl) {
      var activeTag = (rawTag || 'all').trim() || 'all';
      var visibleCount = 0;

      rows.forEach(function (row) {
        var rowTags = parseTagsCsv(row.dataset.tags);
        var matched = activeTag === 'all' || rowTags.indexOf(activeTag) !== -1;
        row.classList.toggle('is-hidden', !matched);
        row.hidden = !matched;
        if (matched) {
          visibleCount++;
        }
      });

      filterButtons.forEach(function (btn) {
        var btnTag = (btn.dataset.filterTag || '').trim();
        var isCurrent = btnTag === activeTag;
        btn.classList.toggle('is-active', isCurrent);
        btn.setAttribute('aria-pressed', isCurrent ? 'true' : 'false');
      });

      if (countEl) {
        countEl.textContent = activeTag === 'all'
          ? '共 ' + visibleCount + ' 篇'
          : '「' + activeTag + '」· 共 ' + visibleCount + ' 篇';
      }

      if (emptyEl) {
        emptyEl.classList.toggle('is-hidden', visibleCount > 0);
      }

      if (shouldSyncUrl) {
        syncUrlQuery(activeTag);
      }
    }

    document.addEventListener('click', function (event) {
      var filterTrigger = event.target.closest('[data-filter-tag]');
      if (!filterTrigger) return;

      event.preventDefault();
      var selectedTag = filterTrigger.dataset.filterTag || 'all';
      applyFilter(selectedTag, true);
    });

    var params = new URLSearchParams(window.location.search);
    var initialTag = params.get('tag');
    if (initialTag && initialTag.trim()) {
      applyFilter(initialTag.trim(), false);
    } else {
      applyFilter('all', false);
    }
  }

  function initMain() {
    initMobileDrawer();
    initArticleTagFilter();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMain);
  } else {
    initMain();
  }
})();
