(function () {
  'use strict';

  function prefersReducedMotion() {
    return Boolean(
      window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

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

  function initArchiveFilters() {
    var tabsContainer = document.querySelector('[data-category-tabs]');
    var listContainer = document.querySelector('[data-articles-list]');
    if (!tabsContainer && !listContainer) return;

    var indicator = tabsContainer ? tabsContainer.querySelector('[data-category-indicator]') : null;
    var categoryTabs = tabsContainer
      ? Array.prototype.slice.call(tabsContainer.querySelectorAll('[data-filter-category]'))
      : [];
    var rows = listContainer
      ? Array.prototype.slice.call(listContainer.querySelectorAll('article.post-row'))
      : [];
    var filterButtons = Array.prototype.slice.call(
      document.querySelectorAll('.filter-pills [data-filter-tag]')
    );
    var countEl = document.querySelector('[data-articles-count]') || document.querySelector('.articles-count');
    var emptyEl =
      document.querySelector('[data-articles-empty]') ||
      document.querySelector('.page-body .empty-stage');
    var emptyStageEl =
      document.querySelector('.page-body .empty-stage') ||
      (emptyEl && emptyEl.classList.contains('empty-stage') ? emptyEl : null);

    var activeCategory = 'all';
    var activeTag = 'all';
    var rowAnimTimers = new WeakMap();
    var emptyAnimTimer = null;

    function findCategoryTab(category) {
      for (var i = 0; i < categoryTabs.length; i++) {
        if ((categoryTabs[i].dataset.filterCategory || '').trim() === category) {
          return categoryTabs[i];
        }
      }
      return null;
    }

    function positionIndicator(tab, immediate, scrollTabIntoView) {
      if (!tabsContainer || !indicator || !tab) return;

      if (immediate) {
        tabsContainer.classList.add('is-initializing');
      }

      var left = tab.offsetLeft;
      var width = tab.offsetWidth;
      indicator.style.transform = 'translate3d(' + left + 'px, 0, 0)';
      indicator.style.width = width + 'px';
      indicator.classList.add('is-ready');
      tabsContainer.classList.add('has-indicator');

      if (immediate) {
        void indicator.offsetWidth;
        window.requestAnimationFrame(function () {
          tabsContainer.classList.remove('is-initializing');
        });
      }

      if (scrollTabIntoView && typeof tab.scrollIntoView === 'function') {
        tab.scrollIntoView({
          behavior: prefersReducedMotion() ? 'auto' : 'smooth',
          block: 'nearest',
          inline: 'nearest'
        });
      }
    }

    function triggerEmptyTransition() {
      if (!emptyStageEl || prefersReducedMotion()) return;
      if (emptyAnimTimer) {
        window.clearTimeout(emptyAnimTimer);
        emptyAnimTimer = null;
      }
      emptyStageEl.classList.remove('is-transitioning');
      void emptyStageEl.offsetWidth;
      emptyStageEl.classList.add('is-transitioning');
      emptyAnimTimer = window.setTimeout(function () {
        emptyStageEl.classList.remove('is-transitioning');
        emptyAnimTimer = null;
      }, 380);
    }

    function computeTagCountsForCategory(category) {
      var counts = Object.create(null);
      var totalInCategory = 0;

      rows.forEach(function (row) {
        var rowCat = (row.dataset.category || '').trim();
        if (category !== 'all' && rowCat !== category) {
          return;
        }
        totalInCategory++;
        var rowTags = parseTagsCsv(row.dataset.tags);
        var seen = Object.create(null);
        rowTags.forEach(function (tag) {
          if (!seen[tag]) {
            seen[tag] = true;
            counts[tag] = (counts[tag] || 0) + 1;
          }
        });
      });

      return { total: totalInCategory, counts: counts };
    }

    function syncUrlQuery(category, tag) {
      if (!window.history || typeof window.history.replaceState !== 'function') {
        return;
      }
      var url = new URL(window.location.href);
      if (!category || category === 'all') {
        url.searchParams.delete('category');
      } else {
        url.searchParams.set('category', category);
      }
      if (!tag || tag === 'all') {
        url.searchParams.delete('tag');
      } else {
        url.searchParams.set('tag', tag);
      }
      window.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }

    function applyFilters(nextCategory, nextTag, options) {
      var opts = options || {};
      var shouldSyncUrl = Boolean(opts.syncUrl);
      var shouldAnimate = Boolean(opts.animate);
      var immediateIndicator = Boolean(opts.immediateIndicator);
      var shouldScrollTab = Boolean(opts.scrollTabIntoView);

      var resolvedCategory = (nextCategory || 'all').trim() || 'all';
      if (categoryTabs.length && !findCategoryTab(resolvedCategory)) {
        resolvedCategory = 'all';
      }

      var categoryStats = computeTagCountsForCategory(resolvedCategory);
      var resolvedTag = (nextTag || 'all').trim() || 'all';
      if (rows.length && resolvedTag !== 'all' && !(categoryStats.counts[resolvedTag] > 0)) {
        resolvedTag = 'all';
      }

      activeCategory = resolvedCategory;
      activeTag = resolvedTag;

      // 1. Update Category Tabs & Sliding Indicator
      var activeTab = findCategoryTab(activeCategory) || categoryTabs[0] || null;
      categoryTabs.forEach(function (tab) {
        var isCurrent = tab === activeTab;
        tab.classList.toggle('is-active', isCurrent);
        tab.setAttribute('aria-selected', isCurrent ? 'true' : 'false');
      });
      if (activeTab) {
        positionIndicator(activeTab, immediateIndicator, shouldScrollTab);
      }

      // 2. Empty Archive (0 total posts)
      if (!listContainer) {
        if (shouldAnimate) {
          triggerEmptyTransition();
        }
        if (shouldSyncUrl) {
          syncUrlQuery(activeCategory, 'all');
        }
        return;
      }

      // 3. Update Fine Tag Pills (counts & availability within activeCategory)
      filterButtons.forEach(function (btn) {
        var btnTag = (btn.dataset.filterTag || '').trim();
        var countSpan = btn.querySelector('.filter-pill-count');
        var availableCount = btnTag === 'all'
          ? categoryStats.total
          : (categoryStats.counts[btnTag] || 0);

        if (countSpan) {
          countSpan.textContent = String(availableCount);
        }

        var isAvailable = btnTag === 'all' || availableCount > 0;
        btn.classList.toggle('is-hidden', !isAvailable);
        btn.hidden = !isAvailable;

        var isCurrent = btnTag === activeTag && isAvailable;
        btn.classList.toggle('is-active', isCurrent);
        btn.setAttribute('aria-pressed', isCurrent ? 'true' : 'false');
      });

      // 4. Filter Article Rows & Trigger Staggered Entrance
      var matchedRows = [];
      rows.forEach(function (row) {
        var rowCat = (row.dataset.category || '').trim();
        var rowTags = parseTagsCsv(row.dataset.tags);
        var catOk = activeCategory === 'all' || rowCat === activeCategory;
        var tagOk = activeTag === 'all' || rowTags.indexOf(activeTag) !== -1;

        var prevTimer = rowAnimTimers.get(row);
        if (prevTimer) {
          window.clearTimeout(prevTimer);
          rowAnimTimers.delete(row);
        }
        row.classList.remove('is-entering');

        if (catOk && tagOk) {
          row.classList.remove('is-hidden');
          row.hidden = false;
          matchedRows.push(row);
        } else {
          row.style.removeProperty('--stagger-index');
          row.classList.add('is-hidden');
          row.hidden = true;
        }
      });

      var visibleCount = matchedRows.length;

      if (visibleCount > 0 && shouldAnimate && !prefersReducedMotion()) {
        void listContainer.offsetWidth;
        matchedRows.forEach(function (row, idx) {
          row.style.setProperty('--stagger-index', String(idx));
          row.classList.add('is-entering');
          var timer = window.setTimeout(function () {
            row.classList.remove('is-entering');
            row.style.removeProperty('--stagger-index');
            rowAnimTimers.delete(row);
          }, 760);
          rowAnimTimers.set(row, timer);
        });
      }

      // 5. Update Count Display & Empty State
      if (countEl) {
        if (activeCategory === 'all' && activeTag === 'all') {
          countEl.textContent = '共 ' + visibleCount + ' 篇';
        } else if (activeCategory !== 'all' && activeTag === 'all') {
          countEl.textContent = activeCategory + ' · 共 ' + visibleCount + ' 篇';
        } else if (activeCategory === 'all' && activeTag !== 'all') {
          countEl.textContent = '「' + activeTag + '」· 共 ' + visibleCount + ' 篇';
        } else {
          countEl.textContent = activeCategory + ' · 「' + activeTag + '」· 共 ' + visibleCount + ' 篇';
        }
      }

      listContainer.classList.toggle('is-hidden', visibleCount === 0);
      listContainer.hidden = visibleCount === 0;

      if (emptyEl) {
        var shouldShowEmpty = visibleCount === 0;
        emptyEl.classList.toggle('is-hidden', !shouldShowEmpty);
        emptyEl.hidden = !shouldShowEmpty;
        if (shouldShowEmpty && shouldAnimate) {
          triggerEmptyTransition();
        }
      }

      if (shouldSyncUrl) {
        syncUrlQuery(activeCategory, activeTag);
      }
    }

    // Event Delegation for Category Tabs, Inline Row Categories, and Tag Pills
    document.addEventListener('click', function (event) {
      var catTrigger = event.target.closest('[data-filter-category]');
      if (catTrigger) {
        event.preventDefault();
        var chosenCategory = (catTrigger.dataset.filterCategory || 'all').trim() || 'all';
        var catChanged = chosenCategory !== activeCategory;
        applyFilters(chosenCategory, activeTag, {
          syncUrl: true,
          animate: catChanged,
          immediateIndicator: false,
          scrollTabIntoView: true
        });
        return;
      }

      var tagTrigger = event.target.closest('[data-filter-tag]');
      if (tagTrigger) {
        event.preventDefault();
        var chosenTag = (tagTrigger.dataset.filterTag || 'all').trim() || 'all';
        var tagChanged = chosenTag !== activeTag;
        applyFilters(activeCategory, chosenTag, {
          syncUrl: true,
          animate: tagChanged,
          immediateIndicator: false,
          scrollTabIntoView: false
        });
      }
    });

    // WAI-ARIA Arrow Navigation for Category Tablist
    if (tabsContainer && categoryTabs.length) {
      tabsContainer.addEventListener('keydown', function (event) {
        var current = event.target.closest('[data-filter-category]');
        if (!current) return;

        var idx = categoryTabs.indexOf(current);
        if (idx === -1) return;

        var nextIdx = -1;
        if (event.key === 'ArrowRight') {
          nextIdx = (idx + 1) % categoryTabs.length;
        } else if (event.key === 'ArrowLeft') {
          nextIdx = (idx - 1 + categoryTabs.length) % categoryTabs.length;
        } else if (event.key === 'Home') {
          nextIdx = 0;
        } else if (event.key === 'End') {
          nextIdx = categoryTabs.length - 1;
        }

        if (nextIdx !== -1) {
          event.preventDefault();
          var nextTab = categoryTabs[nextIdx];
          nextTab.focus();
          applyFilters(nextTab.dataset.filterCategory || 'all', activeTag, {
            syncUrl: true,
            animate: true,
            immediateIndicator: false,
            scrollTabIntoView: true
          });
        }
      });
    }

    // Reposition Sliding Indicator on Resize / Font Load
    var repositionCurrent = function () {
      var currentTab = findCategoryTab(activeCategory) || categoryTabs[0];
      if (currentTab) {
        positionIndicator(currentTab, true, false);
      }
    };

    if (tabsContainer && 'ResizeObserver' in window) {
      var ro = new ResizeObserver(repositionCurrent);
      ro.observe(tabsContainer);
      categoryTabs.forEach(function (tab) {
        ro.observe(tab);
      });
    } else if (tabsContainer) {
      window.addEventListener('resize', repositionCurrent, { passive: true });
    }

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(repositionCurrent);
    }

    // Initial State from URL Query Parameters (?category=...&tag=...)
    var params = new URLSearchParams(window.location.search);
    var initialCategory = (params.get('category') || 'all').trim() || 'all';
    var initialTag = (params.get('tag') || 'all').trim() || 'all';

    applyFilters(initialCategory, initialTag, {
      syncUrl: false,
      animate: false,
      immediateIndicator: true,
      scrollTabIntoView: initialCategory !== 'all'
    });
  }

  function initMain() {
    initMobileDrawer();
    initArchiveFilters();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMain);
  } else {
    initMain();
  }
})();
