(function () {
  'use strict';

  function initHomeCover() {
    var opening = document.querySelector('[data-home-opening]');
    if (!opening) return;

    var stage = opening.querySelector('.home-opening-stage');
    var intro = opening.querySelector('#home-intro');
    var image = opening.querySelector('.vinyl-cover-img');
    var enter = opening.querySelector('.home-cover-enter');
    var header = document.querySelector('.site-header');
    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    var travel = 0;
    var frame = 0;

    function updateProgress() {
      frame = 0;
      if (reducedMotion.matches) return;

      var progress = Math.max(0, Math.min(1, -opening.getBoundingClientRect().top / travel));
      var navOpacity = Math.max(0, Math.min(1, (progress - 0.29) / 0.46));
      opening.style.setProperty('--cover-progress', progress);
      header.style.setProperty('--cover-nav-opacity', navOpacity);
      opening.classList.toggle('is-content-visible', progress >= 0.42);
      header.classList.toggle('is-cover-nav-visible', navOpacity >= 0.64);
    }

    function requestUpdate() {
      if (!frame && !reducedMotion.matches) frame = window.requestAnimationFrame(updateProgress);
    }

    function measureStage() {
      if (reducedMotion.matches) return;

      var stageRect = stage.getBoundingClientRect();
      var imageRect = image.getBoundingClientRect();
      travel = Math.max(1, opening.offsetHeight - stage.offsetHeight);
      opening.style.setProperty('--portrait-end-x', (imageRect.left - stageRect.left) + 'px');
      opening.style.setProperty('--portrait-end-y', (imageRect.top - stageRect.top) + 'px');
      opening.style.setProperty('--portrait-end-width', imageRect.width + 'px');
      opening.style.setProperty('--portrait-end-height', imageRect.height + 'px');
      requestUpdate();
    }

    function scrollToIntro(behavior) {
      var top = window.scrollY + opening.getBoundingClientRect().top;
      intro.focus({ preventScroll: true });
      window.scrollTo({ top: Math.ceil(top + travel), behavior: behavior });
    }

    function syncMotionPreference() {
      var animated = !reducedMotion.matches;
      opening.classList.toggle('is-scroll-cover', animated);
      header.classList.toggle('is-cover-header', animated);
      if (!animated) return;

      measureStage();
      if (window.location.hash === '#home-intro') scrollToIntro('instant');
    }

    enter.addEventListener('click', function (event) {
      if (reducedMotion.matches || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      scrollToIntro('smooth');
    });

    window.addEventListener('scroll', requestUpdate, { passive: true });
    window.addEventListener('resize', measureStage);
    window.addEventListener('pageshow', measureStage);
    reducedMotion.addEventListener('change', syncMotionPreference);
    if (window.ResizeObserver) {
      var observer = new ResizeObserver(measureStage);
      observer.observe(stage);
      observer.observe(image);
    }
    syncMotionPreference();
  }

  initHomeCover();
})();
