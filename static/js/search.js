(function () {
  'use strict';

  function getBasePath() {
    var meta = document.querySelector('meta[name="site-base-path"]');
    if (!meta) {
      return '';
    }
    var raw = String(meta.getAttribute('content') || '').trim();
    if (!raw || raw === '/') {
      return '';
    }
    return '/' + raw.replace(/^\/+|\/+$/g, '');
  }

  function resolveResultUrl(rawUrl, prefix) {
    var url = String(rawUrl || '/');
    if (!prefix) {
      return url;
    }
    if (/^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(url) || url.indexOf('//') === 0) {
      return url;
    }
    if (url === prefix || url.indexOf(prefix + '/') === 0) {
      return url;
    }
    if (url.charAt(0) === '/') {
      return prefix + url;
    }
    return prefix + '/' + url;
  }

  var basePath = getBasePath();
  var INDEX_URL = basePath + '/api/search-index.json';
  var cachedIndex = null;
  var fetchPromise = null;
  var selectedIndex = -1;

  function getElements() {
    return {
      modal: document.querySelector('[data-search-modal]'),
      input: document.querySelector('[data-search-input]'),
      results: document.querySelector('[data-search-results]'),
      count: document.querySelector('[data-search-count]')
    };
  }

  function loadSearchIndex() {
    if (Array.isArray(cachedIndex)) {
      return Promise.resolve(cachedIndex);
    }
    if (fetchPromise) {
      return fetchPromise;
    }
    fetchPromise = fetch(INDEX_URL, { cache: 'no-cache', headers: { Accept: 'application/json' } })
      .then(function (resp) {
        if (!resp.ok) {
          throw new Error('Failed to load search index: ' + resp.status);
        }
        return resp.json();
      })
      .then(function (data) {
        cachedIndex = Array.isArray(data) ? data : [];
        return cachedIndex;
      })
      .catch(function (err) {
        fetchPromise = null;
        throw err;
      });
    return fetchPromise;
  }

  function isSubsequence(needle, haystack) {
    if (!needle || needle.length > haystack.length) {
      return false;
    }
    var i = 0;
    for (var j = 0; j < haystack.length && i < needle.length; j++) {
      if (haystack[j] === needle[i]) {
        i++;
      }
    }
    return i === needle.length;
  }

  function scoreItem(item, tokens, fullQuery) {
    if (!fullQuery) {
      return 1;
    }

    var title = String(item.title || '').toLowerCase();
    var category = String(item.category || '').toLowerCase();
    var tags = Array.isArray(item.tags) ? item.tags.join(' ').toLowerCase() : '';
    var summary = String(item.summary || '').toLowerCase();
    var excerpt = String(item.excerpt || '').toLowerCase();

    var totalScore = 0;
    for (var i = 0; i < tokens.length; i++) {
      var token = tokens[i];
      var tokenScore = 0;

      if (title.indexOf(token) !== -1) tokenScore += 14;
      if (tags.indexOf(token) !== -1) tokenScore += 9;
      if (category.indexOf(token) !== -1) tokenScore += 7;
      if (summary.indexOf(token) !== -1) tokenScore += 5;
      if (excerpt.indexOf(token) !== -1) tokenScore += 2;

      if (tokenScore === 0) {
        if (isSubsequence(token, title)) {
          tokenScore += 3;
        } else if (isSubsequence(token, tags)) {
          tokenScore += 2;
        } else {
          return 0;
        }
      }
      totalScore += tokenScore;
    }

    if (title.indexOf(fullQuery) !== -1) {
      totalScore += 10;
    }
    return totalScore;
  }

  function buildSnippet(item, tokens) {
    var summary = String(item.summary || '');
    var excerpt = String(item.excerpt || '');
    if (!tokens.length) {
      return summary || excerpt.slice(0, 110);
    }

    var lowerExcerpt = excerpt.toLowerCase();
    var lowerSummary = summary.toLowerCase();
    for (var i = 0; i < tokens.length; i++) {
      if (lowerSummary.indexOf(tokens[i]) !== -1) {
        return summary;
      }
    }

    for (var j = 0; j < tokens.length; j++) {
      var idx = lowerExcerpt.indexOf(tokens[j]);
      if (idx !== -1) {
        var start = Math.max(0, idx - 26);
        var end = Math.min(excerpt.length, idx + 84);
        var prefix = start > 0 ? '…' : '';
        var suffix = end < excerpt.length ? '…' : '';
        return prefix + excerpt.slice(start, end).trim() + suffix;
      }
    }

    return summary || excerpt.slice(0, 110);
  }

  function appendHighlightedText(container, text, tokens) {
    var source = String(text || '');
    if (!tokens.length || !source) {
      container.textContent = source;
      return;
    }

    var lower = source.toLowerCase();
    var ranges = [];

    tokens.forEach(function (token) {
      if (!token) return;
      var pos = 0;
      while (pos < lower.length) {
        var found = lower.indexOf(token, pos);
        if (found === -1) break;
        ranges.push([found, found + token.length]);
        pos = found + token.length;
      }
    });

    if (!ranges.length) {
      container.textContent = source;
      return;
    }

    ranges.sort(function (a, b) {
      return a[0] - b[0] || b[1] - a[1];
    });

    var merged = [ranges[0]];
    for (var i = 1; i < ranges.length; i++) {
      var prev = merged[merged.length - 1];
      var curr = ranges[i];
      if (curr[0] <= prev[1]) {
        prev[1] = Math.max(prev[1], curr[1]);
      } else {
        merged.push(curr);
      }
    }

    var cursor = 0;
    merged.forEach(function (range) {
      if (range[0] > cursor) {
        container.appendChild(document.createTextNode(source.slice(cursor, range[0])));
      }
      var mark = document.createElement('mark');
      mark.className = 'search-highlight';
      mark.textContent = source.slice(range[0], range[1]);
      container.appendChild(mark);
      cursor = range[1];
    });

    if (cursor < source.length) {
      container.appendChild(document.createTextNode(source.slice(cursor)));
    }
  }

  function updateSelection(newIndex) {
    var els = getElements();
    if (!els.results) return;
    var items = els.results.querySelectorAll('.search-result-item');
    if (!items.length) {
      selectedIndex = -1;
      els.input.removeAttribute('aria-activedescendant');
      return;
    }

    if (newIndex < 0) {
      selectedIndex = items.length - 1;
    } else if (newIndex >= items.length) {
      selectedIndex = 0;
    } else {
      selectedIndex = newIndex;
    }

    items.forEach(function (el, idx) {
      var active = idx === selectedIndex;
      el.classList.toggle('is-selected', active);
      el.setAttribute('aria-selected', active ? 'true' : 'false');
      if (active) {
        els.input.setAttribute('aria-activedescendant', el.id);
        el.scrollIntoView({ block: 'nearest', behavior: 'instant' });
      }
    });
  }

  function renderResults(queryText) {
    var els = getElements();
    if (!els.results) return;

    var rawQuery = String(queryText || '').trim();
    var lowerQuery = rawQuery.toLowerCase();
    var tokens = lowerQuery ? lowerQuery.split(/\s+/).filter(Boolean) : [];
    var items = Array.isArray(cachedIndex) ? cachedIndex : [];

    var scored = [];
    for (var i = 0; i < items.length; i++) {
      var score = scoreItem(items[i], tokens, lowerQuery);
      if (score > 0) {
        scored.push({ item: items[i], score: score, order: i });
      }
    }

    scored.sort(function (a, b) {
      return b.score - a.score || a.order - b.order;
    });

    var visible = scored.slice(0, 10);
    els.results.innerHTML = '';
    els.input.removeAttribute('aria-activedescendant');

    if (els.count) {
      els.count.textContent = rawQuery
        ? '命中 ' + scored.length + ' 篇'
        : '全部 ' + items.length + ' 篇';
    }

    if (!visible.length) {
      var empty = document.createElement('div');
      empty.className = 'search-empty';
      empty.textContent = items.length
        ? '未找到与「' + rawQuery + '」相关的文章，试试其他关键词。'
        : '暂无已发布文章。';
      els.results.appendChild(empty);
      selectedIndex = -1;
      return;
    }

    visible.forEach(function (entry, index) {
      var post = entry.item;
      var link = document.createElement('a');
      link.className = 'search-result-item';
      link.id = 'site-search-result-' + index;
      link.href = resolveResultUrl(post.url || '/', basePath);
      link.setAttribute('role', 'option');
      link.setAttribute('aria-selected', 'false');

      var top = document.createElement('div');
      top.className = 'search-result-top';

      var titleEl = document.createElement('span');
      titleEl.className = 'search-result-title';
      appendHighlightedText(titleEl, post.title || '', tokens);

      var metaEl = document.createElement('span');
      metaEl.className = 'search-result-meta';
      var metaParts = [];
      if (post.category) metaParts.push(post.category);
      if (post.date) metaParts.push(post.date);
      if (post.reading_time) metaParts.push(post.reading_time + ' 分钟');
      metaEl.textContent = metaParts.join(' · ');

      top.appendChild(titleEl);
      top.appendChild(metaEl);

      var excerptEl = document.createElement('p');
      excerptEl.className = 'search-result-excerpt';
      appendHighlightedText(excerptEl, buildSnippet(post, tokens), tokens);

      link.appendChild(top);
      link.appendChild(excerptEl);

      if (Array.isArray(post.tags) && post.tags.length) {
        var tagsMeta = document.createElement('div');
        tagsMeta.className = 'search-result-meta';
        appendHighlightedText(tagsMeta, '# ' + post.tags.join('  # '), tokens);
        link.appendChild(tagsMeta);
      }

      els.results.appendChild(link);
    });

    updateSelection(0);
  }

  function fitModalToViewport(modal) {
    var viewport = window.visualViewport;
    if (!modal.open || !viewport) return;
    if (viewport.scale === 1) {
      modal.style.setProperty('--search-viewport-height', viewport.height + 'px');
      modal.style.setProperty('--search-viewport-top', viewport.offsetTop + 'px');
    } else {
      modal.style.removeProperty('--search-viewport-height');
      modal.style.removeProperty('--search-viewport-top');
    }
  }

  function openModal() {
    var els = getElements();
    if (!els.modal || !els.input) return;

    if (els.modal.open) {
      els.input.focus();
      return;
    }

    var drawer = document.querySelector('[data-mobile-drawer][open]');
    if (drawer) drawer.close();
    els.modal.showModal();
    els.input.setAttribute('aria-expanded', 'true');
    fitModalToViewport(els.modal);

    if (cachedIndex === null && els.results) {
      els.results.innerHTML = '<div class="search-empty">正在载入文章索引…</div>';
    }

    loadSearchIndex()
      .then(function () {
        if (els.modal.open) {
          renderResults(els.input.value);
        }
      })
      .catch(function () {
        if (els.results) {
          els.results.innerHTML = '<div class="search-empty">索引加载失败，请稍后重试。</div>';
        }
      });
  }

  function initSearch() {
    var els = getElements();
    if (!els.modal || !els.input || !els.results) {
      return;
    }

    document.addEventListener('click', function (event) {
      if (event.target.closest('[data-search-open]')) {
        event.preventDefault();
        openModal();
        return;
      }

      if (event.target.closest('[data-search-close]') || event.target === els.modal) {
        event.preventDefault();
        els.modal.close();
      }
    });

    els.modal.addEventListener('close', function () {
      selectedIndex = -1;
      els.input.setAttribute('aria-expanded', 'false');
      els.input.removeAttribute('aria-activedescendant');
    });

    els.modal.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !event.isComposing) {
        event.preventDefault();
        els.modal.close();
      }
    });

    if (window.visualViewport) {
      var fitViewport = function () { fitModalToViewport(els.modal); };
      window.visualViewport.addEventListener('resize', fitViewport);
      window.visualViewport.addEventListener('scroll', fitViewport);
    }

    els.input.addEventListener('input', function () {
      if (cachedIndex !== null) {
        renderResults(els.input.value);
      }
    });

    els.input.addEventListener('keydown', function (event) {
      if (event.isComposing || event.keyCode === 229) return;

      if (event.key === 'ArrowDown') {
        event.preventDefault();
        updateSelection(selectedIndex + 1);
        return;
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault();
        updateSelection(selectedIndex - 1);
        return;
      }

      if (event.key === 'Enter') {
        var items = els.results.querySelectorAll('.search-result-item');
        var target = items[selectedIndex];
        if (target && target.getAttribute('href')) {
          event.preventDefault();
          window.location.href = target.getAttribute('href');
        }
      }
    });

    document.addEventListener('keydown', function (event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        if (els.modal.open) els.modal.close();
        else openModal();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
  } else {
    initSearch();
  }
})();
