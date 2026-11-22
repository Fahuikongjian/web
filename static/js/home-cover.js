(function () {
  'use strict';

  var opening = document.querySelector('[data-home-opening]');
  if (!opening) return;

  var stage = opening.querySelector('.home-opening-stage');
  var intro = opening.querySelector('#home-intro');
  var content = opening.querySelector('.home-entries');
  var enter = opening.querySelector('.home-cover-enter');
  var coverMark = opening.querySelector('.home-cover-mark');
  var coverName = opening.querySelector('.home-cover-name');
  var coverTitle = opening.querySelector('.home-cover-title');
  var header = document.querySelector('.site-header');
  var headerMark = header ? header.querySelector('.brand-mark') : null;
  var headerTitle = header ? header.querySelector('.brand-title') : null;
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var coverTop = 0;
  var travel = 0;
  var renderedOffset = 0;
  var scrollFrame = 0;
  var brandMetrics = null;

  function unitInterval(value) {
    return Math.max(0, Math.min(1, value));
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function findSubtextRect(el, needle) {
    if (!el) return null;
    var textNode = el.firstChild;
    while (textNode && textNode.nodeType !== 3) {
      textNode = textNode.nextSibling;
    }
    if (!textNode || !textNode.nodeValue) {
      return el.getBoundingClientRect();
    }
    var full = textNode.nodeValue;
    var idx = needle ? full.indexOf(needle) : 0;
    if (idx === -1) {
      return el.getBoundingClientRect();
    }
    var range = document.createRange();
    range.setStart(textNode, idx);
    range.setEnd(textNode, needle ? idx + needle.length : full.length);
    var rect = range.getBoundingClientRect();
    if (!rect || rect.width <= 0 || rect.height <= 0) {
      return el.getBoundingClientRect();
    }
    return rect;
  }

  function computeItemDelta(el, srcTextRect, targetRect, maxRight) {
    if (!el || !srcTextRect || !targetRect || srcTextRect.width <= 0 || srcTextRect.height <= 0) {
      return { dx: 0, dy: 0, s: 1 };
    }
    var elRect = el.getBoundingClientRect();
    var scale = clamp(targetRect.width / srcTextRect.width, 0.12, 1.35);

    var textOffsetX = srcTextRect.left - elRect.left;
    var textOffsetY = srcTextRect.top - elRect.top;
    var targetLeft = targetRect.left;
    if (typeof maxRight === 'number' && targetLeft > maxRight) {
      targetLeft = maxRight;
    }
    var dx = targetLeft - (elRect.left + textOffsetX * scale);
    var targetCenterY = targetRect.top + targetRect.height / 2;
    var srcScaledCenterY = elRect.top + (textOffsetY + srcTextRect.height / 2) * scale;
    var dy = targetCenterY - srcScaledCenterY;

    return { dx: dx, dy: dy, s: scale };
  }

  function measureBrandTargets() {
    if (reducedMotion.matches || !header || !headerMark || !headerTitle) {
      brandMetrics = null;
      return;
    }
    if (!coverMark || !coverName || !coverTitle) {
      brandMetrics = null;
      return;
    }

    opening.classList.add('is-measuring');
    header.classList.add('is-measuring');

    var targetMarkRect = headerMark.getBoundingClientRect();
    var headerTitleBox = headerTitle.getBoundingClientRect();
    var targetNameRect = findSubtextRect(headerTitle, 'ASTRA YAO');
    var targetTitleRect = findSubtextRect(headerTitle, '星环手记');

    var srcMarkRect = coverMark.getBoundingClientRect();
    var srcNameTextRect = findSubtextRect(coverName, '');
    var srcTitleTextRect = findSubtextRect(coverTitle, '');

    var maxTitleLeft = headerTitleBox.right > 0 ? headerTitleBox.right - 20 : undefined;

    brandMetrics = {
      mark: computeItemDelta(coverMark, srcMarkRect, targetMarkRect),
      name: computeItemDelta(coverName, srcNameTextRect, targetNameRect, maxTitleLeft),
      title: computeItemDelta(coverTitle, srcTitleTextRect, targetTitleRect, maxTitleLeft)
    };

    opening.classList.remove('is-measuring');
    header.classList.remove('is-measuring');
  }

  function applyBrandMorph(progress) {
    if (!brandMetrics) return;
    var t = unitInterval(progress / 0.84);
    var smooth = t * t * (3 - 2 * t);
    var morph = 0.32 * t + 0.68 * smooth;

    var handoff = unitInterval((progress - 0.84) / 0.12);
    var coverBrandOpacity = 1 - handoff;
    var headerBrandOpacity = handoff;

    opening.style.setProperty('--cover-brand-opacity', coverBrandOpacity.toFixed(4));
    if (header) {
      header.style.setProperty('--header-brand-opacity', headerBrandOpacity.toFixed(4));
    }
    opening.classList.toggle('is-brand-docked', progress >= 0.96);

    var m = brandMetrics.mark;
    var n = brandMetrics.name;
    var ti = brandMetrics.title;

    opening.style.setProperty('--mark-tx', (m.dx * morph).toFixed(2) + 'px');
    opening.style.setProperty('--mark-ty', (m.dy * morph).toFixed(2) + 'px');
    opening.style.setProperty('--mark-s', (1 + (m.s - 1) * morph).toFixed(4));

    opening.style.setProperty('--name-tx', (n.dx * morph).toFixed(2) + 'px');
    opening.style.setProperty('--name-ty', (n.dy * morph).toFixed(2) + 'px');
    opening.style.setProperty('--name-s', (1 + (n.s - 1) * morph).toFixed(4));

    opening.style.setProperty('--title-tx', (ti.dx * morph).toFixed(2) + 'px');
    opening.style.setProperty('--title-ty', (ti.dy * morph).toFixed(2) + 'px');
    opening.style.setProperty('--title-s', (1 + (ti.s - 1) * morph).toFixed(4));
  }

  function clearBrandMorph() {
    var props = [
      '--cover-brand-opacity',
      '--mark-tx', '--mark-ty', '--mark-s',
      '--name-tx', '--name-ty', '--name-s',
      '--title-tx', '--title-ty', '--title-s'
    ];
    for (var i = 0; i < props.length; i++) {
      opening.style.removeProperty(props[i]);
    }
    opening.classList.remove('is-brand-docked');
    if (header) {
      header.style.removeProperty('--header-brand-opacity');
    }
  }

  function renderProgress() {
    renderedOffset = window.scrollY - coverTop;
    var progress = unitInterval(renderedOffset / travel);
    var navOpacity = unitInterval((progress - 0.70) / 0.30);
    var contentAccessible = progress >= 0.42;
    opening.style.setProperty('--cover-progress', progress);
    header.style.setProperty('--cover-nav-opacity', navOpacity);
    opening.classList.toggle('is-past-cover-cue', progress >= 0.34);
    header.classList.toggle('is-cover-nav-visible', navOpacity >= 0.64);
    content.inert = !contentAccessible;
    applyBrandMorph(progress);
  }

  function requestProgress() {
    if (reducedMotion.matches || scrollFrame) return;
    scrollFrame = window.requestAnimationFrame(function () {
      scrollFrame = 0;
      renderProgress();
    });
  }

  function measureStage() {
    if (reducedMotion.matches) return;

    var previousTravel = travel;
    coverTop = Math.round(window.scrollY + opening.getBoundingClientRect().top);
    travel = Math.max(1, opening.offsetHeight - stage.offsetHeight);
    if (travel !== previousTravel && renderedOffset > 0 && renderedOffset <= previousTravel) {
      window.scrollTo({
        top: coverTop + Math.round(renderedOffset * travel / previousTravel),
        behavior: 'instant'
      });
    }
    measureBrandTargets();
    renderProgress();
  }

  function scrollToIntro(behavior) {
    intro.focus({ preventScroll: true });
    window.scrollTo({ top: coverTop + travel, behavior: behavior });
  }

  function syncMotionPreference() {
    var animated = !reducedMotion.matches;
    opening.classList.toggle('is-scroll-cover', animated);
    header.classList.toggle('is-cover-header', animated);
    if (!animated) {
      window.cancelAnimationFrame(scrollFrame);
      scrollFrame = 0;
      travel = 0;
      brandMetrics = null;
      clearBrandMorph();
      content.inert = false;
      return;
    }

    measureStage();
    if (window.location.hash === '#home-intro') scrollToIntro('instant');
  }

  enter.addEventListener('click', function (event) {
    if (reducedMotion.matches || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    scrollToIntro('smooth');
  });

  window.addEventListener('scroll', requestProgress, { passive: true });
  window.addEventListener('resize', measureStage);
  window.addEventListener('pageshow', measureStage);
  reducedMotion.addEventListener('change', syncMotionPreference);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(measureStage);
  }
  if (window.ResizeObserver) {
    var observer = new ResizeObserver(measureStage);
    observer.observe(stage);
  }
  syncMotionPreference();
})();
