(function () {
  'use strict';

  var opening = document.querySelector('[data-home-opening]');
  if (!opening) return;

  var stage = opening.querySelector('.home-opening-stage');
  var intro = opening.querySelector('#home-intro');
  var content = opening.querySelector('.hero-grid');
  var enter = opening.querySelector('.home-cover-enter');
  var header = document.querySelector('.site-header');
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var coverTop = 0;
  var travel = 1;
  var scrollFrame = 0;

  function unitInterval(value) {
    return Math.max(0, Math.min(1, value));
  }

  function renderProgress() {
    var progress = unitInterval((window.scrollY - coverTop) / travel);
    var navOpacity = unitInterval((progress - 0.70) / 0.30);
    var contentAccessible = progress >= 0.42;
    opening.style.setProperty('--cover-progress', progress);
    header.style.setProperty('--cover-nav-opacity', navOpacity);
    opening.classList.toggle('is-past-cover-cue', progress >= 0.34);
    header.classList.toggle('is-cover-nav-visible', navOpacity >= 0.64);
    content.inert = !contentAccessible;
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

    coverTop = Math.round(window.scrollY + opening.getBoundingClientRect().top);
    travel = Math.max(1, opening.offsetHeight - stage.offsetHeight);
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
  if (window.ResizeObserver) {
    var observer = new ResizeObserver(measureStage);
    observer.observe(stage);
  }
  syncMotionPreference();
})();
