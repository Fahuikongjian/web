(function () {
  'use strict';

  var activeLightboxCloser = null;

  function prefersReducedMotion() {
    return Boolean(
      window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  function fallbackCopyText(text) {
    var textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.top = '-9999px';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, text.length);
    var ok = false;
    try {
      ok = document.execCommand('copy');
    } catch (e) {
      ok = false;
    }
    document.body.removeChild(textarea);
    return ok;
  }

  function copyTextToClipboard(text) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      return navigator.clipboard.writeText(text).catch(function () {
        if (!fallbackCopyText(text)) {
          throw new Error('Clipboard copy failed');
        }
      });
    }
    if (fallbackCopyText(text)) {
      return Promise.resolve();
    }
    return Promise.reject(new Error('Clipboard copy failed'));
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
    var listContainer = document.querySelector('[data-filter-list], [data-articles-list]');
    if (!tabsContainer && !listContainer) return;

    var indicator = tabsContainer ? tabsContainer.querySelector('[data-category-indicator]') : null;
    var categoryTabs = tabsContainer
      ? Array.prototype.slice.call(tabsContainer.querySelectorAll('[data-filter-category]'))
      : [];
    var items = listContainer
      ? Array.prototype.slice.call(listContainer.querySelectorAll('[data-filter-item], article.post-row'))
      : [];
    var filterButtons = Array.prototype.slice.call(
      document.querySelectorAll('.filter-pills [data-filter-tag]')
    );
    var countEl = document.querySelector('[data-filter-count], [data-articles-count], .articles-count');
    var countUnit = listContainer && listContainer.dataset.countUnit ? listContainer.dataset.countUnit : '篇';
    var emptyEl =
      document.querySelector('[data-filter-empty], [data-articles-empty]') ||
      document.querySelector('.page-body .empty-stage');
    var emptyStageEl =
      document.querySelector('.page-body .empty-stage') ||
      (emptyEl && emptyEl.classList.contains('empty-stage') ? emptyEl : null);

    var activeCategory = 'all';
    var activeTag = 'all';
    var itemAnimTimers = new WeakMap();
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

      items.forEach(function (item) {
        var itemCat = (item.dataset.category || '').trim();
        if (category !== 'all' && itemCat !== category) {
          return;
        }
        totalInCategory++;
        var itemTags = parseTagsCsv(item.dataset.tags);
        var seen = Object.create(null);
        itemTags.forEach(function (tag) {
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
      if (items.length && resolvedTag !== 'all' && !(categoryStats.counts[resolvedTag] > 0)) {
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

      // 2. Empty Archive / Empty Catalog (0 total items)
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

      // 4. Filter Items & Trigger Staggered Entrance
      var matchedItems = [];
      items.forEach(function (item) {
        var itemCat = (item.dataset.category || '').trim();
        var itemTags = parseTagsCsv(item.dataset.tags);
        var catOk = activeCategory === 'all' || itemCat === activeCategory;
        var tagOk = activeTag === 'all' || itemTags.indexOf(activeTag) !== -1;

        var prevTimer = itemAnimTimers.get(item);
        if (prevTimer) {
          window.clearTimeout(prevTimer);
          itemAnimTimers.delete(item);
        }
        item.classList.remove('is-entering');

        if (catOk && tagOk) {
          item.classList.remove('is-hidden');
          item.hidden = false;
          matchedItems.push(item);
        } else {
          item.style.removeProperty('--stagger-index');
          item.classList.add('is-hidden');
          item.hidden = true;
        }
      });

      if (listContainer.classList.contains('projects-grid--catalog')) {
        listContainer.classList.toggle('is-filtered', activeCategory !== 'all' || activeTag !== 'all');
      }

      var visibleCount = matchedItems.length;

      if (visibleCount > 0 && shouldAnimate && !prefersReducedMotion()) {
        void listContainer.offsetWidth;
        matchedItems.forEach(function (item, idx) {
          item.style.setProperty('--stagger-index', String(idx));
          item.classList.add('is-entering');
          var timer = window.setTimeout(function () {
            item.classList.remove('is-entering');
            item.style.removeProperty('--stagger-index');
            itemAnimTimers.delete(item);
          }, 760);
          itemAnimTimers.set(item, timer);
        });
      }

      // 5. Update Count Display & Empty State
      if (countEl) {
        var totalPhrase = '共 ' + visibleCount + ' ' + countUnit;
        if (activeCategory === 'all' && activeTag === 'all') {
          countEl.textContent = totalPhrase;
        } else if (activeCategory !== 'all' && activeTag === 'all') {
          countEl.textContent = activeCategory + ' · ' + totalPhrase;
        } else if (activeCategory === 'all' && activeTag !== 'all') {
          countEl.textContent = '「' + activeTag + '」· ' + totalPhrase;
        } else {
          countEl.textContent = activeCategory + ' · 「' + activeTag + '」· ' + totalPhrase;
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

    // Event Delegation for Category Tabs, Inline Badges, Lightbox Badges, and Tag Pills
    document.addEventListener('click', function (event) {
      var catTrigger = event.target.closest('[data-filter-category]');
      if (catTrigger) {
        event.preventDefault();
        if (catTrigger.closest('[data-gallery-lightbox]') && typeof activeLightboxCloser === 'function') {
          activeLightboxCloser(false);
        }
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
        if (tagTrigger.closest('[data-gallery-lightbox]') && typeof activeLightboxCloser === 'function') {
          activeLightboxCloser(false);
        }
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

  function initGalleryInteractions() {
    var galleryPage = document.querySelector('[data-gallery-list], [data-gallery-lightbox]');
    if (!galleryPage) return;

    var copyTimers = new WeakMap();

    function resetCopyButton(btn) {
      if (!btn) return;
      var prev = copyTimers.get(btn);
      if (prev) {
        window.clearTimeout(prev);
        copyTimers.delete(btn);
      }
      btn.classList.remove('is-copied', 'is-copy-error');
      if (btn.dataset.originalLabel) {
        btn.textContent = btn.dataset.originalLabel;
      }
    }

    function runCopyFeedback(btn, text) {
      if (!btn.dataset.originalLabel) {
        btn.dataset.originalLabel = btn.textContent.trim() || '复制';
      }
      var prev = copyTimers.get(btn);
      if (prev) {
        window.clearTimeout(prev);
        copyTimers.delete(btn);
      }

      copyTextToClipboard(text || '')
        .then(function () {
          btn.classList.remove('is-copy-error');
          btn.classList.add('is-copied');
          btn.textContent = '已复制';
          var timer = window.setTimeout(function () {
            resetCopyButton(btn);
          }, 1800);
          copyTimers.set(btn, timer);
        })
        .catch(function () {
          btn.classList.remove('is-copied');
          btn.classList.add('is-copy-error');
          btn.textContent = '复制失败';
          var timer = window.setTimeout(function () {
            resetCopyButton(btn);
          }, 1800);
          copyTimers.set(btn, timer);
        });
    }

    // Card prompt copy buttons
    document.addEventListener('click', function (event) {
      var copyBtn = event.target.closest('.prompt-copy-btn[data-copy-prompt]');
      if (!copyBtn) return;

      event.preventDefault();
      event.stopPropagation();

      var card = copyBtn.closest('.gallery-card');
      if (!card) return;
      runCopyFeedback(copyBtn, card.dataset.prompt || '');
    });

    // Lightbox dialog
    var lightbox = document.querySelector('[data-gallery-lightbox]');
    if (!lightbox) return;

    var imgEl = lightbox.querySelector('[data-lightbox-image]');
    var titleEl = lightbox.querySelector('[data-lightbox-title]');
    var metaEl = lightbox.querySelector('[data-lightbox-meta]');
    var promptSection = lightbox.querySelector('[data-lightbox-prompt-section]');
    var promptEl = lightbox.querySelector('[data-lightbox-prompt]');
    var negSection = lightbox.querySelector('[data-lightbox-negative-section]');
    var negEl = lightbox.querySelector('[data-lightbox-negative]');
    var tagsEl = lightbox.querySelector('[data-lightbox-tags]');
    var lbCopyPromptBtn = lightbox.querySelector('[data-lightbox-copy-prompt]');
    var lbCopyNegBtn = lightbox.querySelector('[data-lightbox-copy-negative]');

    var lastTrigger = null;
    var shouldRestoreFocus = true;

    function closeLightbox(restoreFocus) {
      if (!lightbox.open) return;
      shouldRestoreFocus = restoreFocus !== false;
      lightbox.close();
    }

    activeLightboxCloser = closeLightbox;

    function openLightboxFromCard(card, triggerEl) {
      if (!card) return;

      lastTrigger = triggerEl || card.querySelector('.gallery-media-btn');
      shouldRestoreFocus = true;

      var title = card.dataset.title || '';
      var cardImg = card.querySelector('.gallery-media-btn img');
      var imageSrc = card.dataset.image || (cardImg ? cardImg.getAttribute('src') : '') || '';
      var promptText = card.dataset.prompt || '';
      var negText = card.dataset.negativePrompt || '';
      var modelText = card.dataset.model || '';
      var paramsText = card.dataset.params || '';
      var dateText = card.dataset.date || '';
      var categoryText = card.dataset.category || '';
      var tagsList = parseTagsCsv(card.dataset.tags);

      if (imgEl) {
        if (imageSrc) {
          imgEl.setAttribute('src', imageSrc);
        } else {
          imgEl.removeAttribute('src');
        }
        imgEl.alt = title;
      }

      if (titleEl) {
        titleEl.textContent = title;
      }

      if (metaEl) {
        metaEl.textContent = '';
        if (categoryText) {
          var catBtn = document.createElement('button');
          catBtn.type = 'button';
          catBtn.className = 'gallery-category-badge';
          catBtn.dataset.filterCategory = categoryText;
          catBtn.textContent = categoryText;
          metaEl.appendChild(catBtn);
        }
        if (modelText) {
          var modelSpan = document.createElement('span');
          modelSpan.className = 'gallery-model-chip';
          modelSpan.textContent = modelText;
          metaEl.appendChild(modelSpan);
        }
        if (paramsText) {
          var paramsSpan = document.createElement('span');
          paramsSpan.className = 'gallery-param-chip';
          paramsSpan.textContent = paramsText;
          metaEl.appendChild(paramsSpan);
        }
        if (dateText) {
          var dateSpan = document.createElement('span');
          dateSpan.className = 'gallery-date-chip';
          dateSpan.textContent = dateText;
          metaEl.appendChild(dateSpan);
        }
        var hasMeta = metaEl.childElementCount > 0;
        metaEl.classList.toggle('is-hidden', !hasMeta);
        metaEl.hidden = !hasMeta;
      }

      if (promptEl && promptSection) {
        promptEl.textContent = promptText;
        promptSection.classList.toggle('is-hidden', !promptText);
        promptSection.hidden = !promptText;
      }

      if (negEl && negSection) {
        negEl.textContent = negText;
        negSection.classList.toggle('is-hidden', !negText);
        negSection.hidden = !negText;
      }

      if (tagsEl) {
        tagsEl.textContent = '';
        tagsList.forEach(function (tag) {
          var tagBtn = document.createElement('button');
          tagBtn.type = 'button';
          tagBtn.className = 'tag-pill';
          tagBtn.dataset.filterTag = tag;
          tagBtn.textContent = tag;
          tagsEl.appendChild(tagBtn);
        });
        var hasTags = tagsList.length > 0;
        tagsEl.classList.toggle('is-hidden', !hasTags);
        tagsEl.hidden = !hasTags;
      }

      resetCopyButton(lbCopyPromptBtn);
      resetCopyButton(lbCopyNegBtn);

      if (!lightbox.open) {
        lightbox.showModal();
      }
    }

    document.addEventListener('click', function (event) {
      var openTrigger = event.target.closest('[data-gallery-open], .gallery-media-btn');
      if (!openTrigger) return;
      if (event.target.closest('.prompt-copy-btn')) return;

      event.preventDefault();
      var card = openTrigger.closest('.gallery-card');
      if (!card && openTrigger.dataset.galleryOpen) {
        var cards = document.querySelectorAll('.gallery-card[data-gallery-id]');
        for (var i = 0; i < cards.length; i++) {
          if (cards[i].dataset.galleryId === openTrigger.dataset.galleryOpen) {
            card = cards[i];
            break;
          }
        }
      }
      if (card) {
        openLightboxFromCard(card, openTrigger);
      }
    });

    if (lbCopyPromptBtn) {
      lbCopyPromptBtn.addEventListener('click', function (event) {
        event.preventDefault();
        runCopyFeedback(lbCopyPromptBtn, promptEl ? promptEl.textContent : '');
      });
    }

    if (lbCopyNegBtn) {
      lbCopyNegBtn.addEventListener('click', function (event) {
        event.preventDefault();
        runCopyFeedback(lbCopyNegBtn, negEl ? negEl.textContent : '');
      });
    }

    lightbox.addEventListener('click', function (event) {
      if (event.target === lightbox || event.target.closest('[data-gallery-close]')) {
        event.preventDefault();
        closeLightbox(true);
      }
    });

    lightbox.addEventListener('close', function () {
      if (imgEl) {
        imgEl.removeAttribute('src');
        imgEl.alt = '';
      }
      if (
        shouldRestoreFocus &&
        lastTrigger &&
        lastTrigger.isConnected &&
        !lastTrigger.closest('[hidden], .is-hidden')
      ) {
        lastTrigger.focus({ preventScroll: true });
      }
      lastTrigger = null;
      shouldRestoreFocus = true;
    });
  }

  function initMain() {
    initMobileDrawer();
    initArchiveFilters();
    initGalleryInteractions();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMain);
  } else {
    initMain();
  }
})();
