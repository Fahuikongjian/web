(function () {
  'use strict';

  function initReadingProgress() {
    var progressBar = document.querySelector('[data-reading-progress]');
    if (!progressBar) return;

    var articleBody = document.querySelector('[data-post-content]') || document.querySelector('.post-prose');
    var rafPending = false;

    function updateProgress() {
      rafPending = false;
      var scrollTop = window.scrollY || window.pageYOffset || 0;
      var viewportHeight = window.innerHeight || document.documentElement.clientHeight || 1;
      var totalScrollable;

      if (articleBody) {
        var rect = articleBody.getBoundingClientRect();
        var bodyBottom = rect.bottom + scrollTop;
        totalScrollable = Math.max(1, bodyBottom - viewportHeight);
      } else {
        totalScrollable = Math.max(1, document.documentElement.scrollHeight - viewportHeight);
      }

      var ratio = Math.min(1, Math.max(0, scrollTop / totalScrollable));
      progressBar.style.width = (ratio * 100).toFixed(2) + '%';
    }

    function onScrollOrResize() {
      if (!rafPending) {
        rafPending = true;
        window.requestAnimationFrame(updateProgress);
      }
    }

    window.addEventListener('scroll', onScrollOrResize, { passive: true });
    window.addEventListener('resize', onScrollOrResize, { passive: true });
    var toc = document.querySelector('[data-post-toc]');
    if (toc) toc.addEventListener('toggle', onScrollOrResize);
    updateProgress();
  }

  function decodeHashId(href) {
    if (!href || href.charAt(0) !== '#') return '';
    var raw = href.slice(1);
    try {
      return decodeURIComponent(raw);
    } catch (e) {
      return raw;
    }
  }

  function initTableOfContents() {
    var toc = document.querySelector('[data-post-toc]');
    if (!toc) return;
    var compact = window.matchMedia('(max-width: 1024px)');
    function setDefaultTocState() { toc.open = !compact.matches; }
    setDefaultTocState();
    compact.addEventListener('change', setDefaultTocState);

    var tocLinks = Array.prototype.slice.call(document.querySelectorAll('.toc-nav .toc-link[href^="#"]'));
    if (!tocLinks.length) return;

    var entries = [];
    tocLinks.forEach(function (link) {
      var id = decodeHashId(link.getAttribute('href'));
      if (!id) return;
      var heading = document.getElementById(id);
      if (heading) {
        entries.push({ id: id, link: link, heading: heading });
      }
    });

    if (!entries.length) return;

    var activeId = '';

    function setActiveLink(id) {
      if (!id || id === activeId) return;
      activeId = id;
      entries.forEach(function (entry) {
        var isCurrent = entry.id === id;
        entry.link.classList.toggle('is-active', isCurrent);
        if (isCurrent) {
          entry.link.setAttribute('aria-current', 'location');
        } else {
          entry.link.removeAttribute('aria-current');
        }
      });
    }

    function pickActiveFromPositions() {
      var scrollBottom = (window.scrollY || 0) + (window.innerHeight || 0);
      if (scrollBottom >= document.documentElement.scrollHeight - 4) {
        setActiveLink(entries[entries.length - 1].id);
        return;
      }

      var candidate = entries[0].id;
      for (var i = 0; i < entries.length; i++) {
        var top = entries[i].heading.getBoundingClientRect().top;
        if (top <= 130) {
          candidate = entries[i].id;
        } else {
          break;
        }
      }
      setActiveLink(candidate);
    }

    if ('IntersectionObserver' in window) {
      var visibleIds = new Set();
      var observer = new IntersectionObserver(
        function (observerEntries) {
          observerEntries.forEach(function (item) {
            var id = item.target.id;
            if (item.isIntersecting) {
              visibleIds.add(id);
            } else {
              visibleIds.delete(id);
            }
          });

          if (visibleIds.size > 0) {
            for (var i = 0; i < entries.length; i++) {
              if (visibleIds.has(entries[i].id)) {
                setActiveLink(entries[i].id);
                return;
              }
            }
          }
          pickActiveFromPositions();
        },
        {
          rootMargin: '-84px 0px -62% 0px',
          threshold: [0, 1]
        }
      );

      entries.forEach(function (entry) {
        observer.observe(entry.heading);
      });
    }

    tocLinks.forEach(function (link) {
      link.addEventListener('click', function (event) {
        var id = decodeHashId(link.getAttribute('href'));
        if (id) {
          setActiveLink(id);
          if (compact.matches && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
            toc.open = false;
            var heading = document.getElementById(id);
            if (heading) {
              heading.setAttribute('tabindex', '-1');
              heading.focus({ preventScroll: true });
            }
          }
        }
      });
    });

    window.addEventListener('scroll', pickActiveFromPositions, { passive: true });
    pickActiveFromPositions();
  }

  function fallbackCopyText(text) {
    var previousFocus = document.activeElement;
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
    previousFocus.focus({ preventScroll: true });
    return ok;
  }

  function copyCodeText(text) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      return navigator.clipboard.writeText(text).then(function () {
        return true;
      }, function () {
        return fallbackCopyText(text);
      });
    }
    return Promise.resolve(fallbackCopyText(text));
  }

  function initCodeCopyButtons() {
    var resetTimers = new WeakMap();

    document.addEventListener('click', function (event) {
      var btn = event.target.closest('.code-copy-btn');
      if (!btn) return;

      var wrapper = btn.closest('.code-block-wrapper');
      if (!wrapper) return;

      var pre = wrapper.querySelector('pre');
      if (!pre) return;

      var rawText = pre.innerText || pre.textContent || '';
      var codeText = rawText.replace(/\n$/, '');

      if (!btn.dataset.originalLabel) {
        btn.dataset.originalLabel = btn.textContent.trim() || '复制';
      }

      copyCodeText(codeText).then(function (copied) {
        var prevTimer = resetTimers.get(btn);
        if (prevTimer) {
          window.clearTimeout(prevTimer);
        }

        btn.classList.toggle('is-copied', copied);
        btn.textContent = copied ? '已复制' : '复制失败';
        btn.setAttribute('aria-label', copied ? '已复制代码' : '复制失败，可重试');

        var timer = window.setTimeout(function () {
          btn.classList.remove('is-copied');
          btn.textContent = btn.dataset.originalLabel || '复制';
          btn.setAttribute('aria-label', '复制代码');
          resetTimers.delete(btn);
        }, 2000);

        resetTimers.set(btn, timer);
      });
    });
  }

  function initPostPage() {
    if (window.__marginNotesPostInit) return;
    window.__marginNotesPostInit = true;

    initReadingProgress();
    initTableOfContents();
    initCodeCopyButtons();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPostPage);
  } else {
    initPostPage();
  }
})();
