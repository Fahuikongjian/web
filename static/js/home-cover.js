(function () {
  'use strict';

  function initHomeCover() {
    var opening = document.querySelector('[data-home-opening]');
    if (!opening) return;

    var stage = opening.querySelector('.home-opening-stage');
    var intro = opening.querySelector('#home-intro');
    var enter = opening.querySelector('.home-cover-enter');
    var header = document.querySelector('.site-header');
    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    var coverTop = 0;
    var travel = 1;
    var threshold = 90;
    var rest = 0;
    var springFrame = 0;
    var scrollFrame = 0;
    var scrollIdle = 0;
    var wheelIdle = 0;
    var wheel = null;
    var touch = null;

    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    function renderProgress() {
      var progress = clamp((window.scrollY - coverTop) / travel, 0, 1);
      var navOpacity = clamp((progress - 0.70) / 0.30, 0, 1);
      opening.style.setProperty('--cover-progress', progress);
      header.style.setProperty('--cover-nav-opacity', navOpacity);
      opening.classList.toggle('is-content-visible', progress >= 0.42);
      header.classList.toggle('is-cover-nav-visible', navOpacity >= 0.64);
    }

    function moveTo(top) {
      window.scrollTo({ top: top, behavior: 'instant' });
      renderProgress();
    }

    function springTo(stop) {
      window.cancelAnimationFrame(springFrame);
      window.clearTimeout(scrollIdle);
      rest = stop;
      var from = window.scrollY;
      var distance = Math.abs(coverTop + stop * travel - from);
      var duration = distance > travel / 2 ? 480 : 275;
      var started = performance.now();

      function step(now) {
        var elapsed = clamp((now - started) / duration, 0, 1);
        // A critically damped spring, normalized to finish at the exact stop.
        var eased = (1 - (1 + 7 * elapsed) * Math.exp(-7 * elapsed)) / (1 - 8 * Math.exp(-7));
        var target = coverTop + stop * travel;
        moveTo(from + (target - from) * eased);
        springFrame = elapsed < 1 ? window.requestAnimationFrame(step) : 0;
      }

      springFrame = window.requestAnimationFrame(step);
    }

    function measureStage() {
      if (reducedMotion.matches) return;

      var atExpandedStop = rest === 1 && Math.abs(window.scrollY - coverTop - travel) <= 1;
      coverTop = Math.round(window.scrollY + opening.getBoundingClientRect().top);
      travel = Math.max(1, opening.offsetHeight - stage.offsetHeight);
      threshold = clamp(travel * 0.14, 68, 106);
      if (atExpandedStop && !springFrame && !wheel && !(touch && touch.gesture)) {
        moveTo(coverTop + travel);
      } else {
        renderProgress();
      }
    }

    function gestureOrigin(delta) {
      var position = window.scrollY - coverTop;
      if (position < -1 || position > travel + 1) return null;
      if (springFrame || (position > 1 && position < travel - 1)) return rest;
      if (position <= 1) return delta > 0 ? 0 : null;
      return delta < 0 ? 1 : null;
    }

    function pushGesture(gesture, delta, velocity) {
      if (gesture.committed) return;
      var direction = gesture.origin === 0 ? 1 : -1;
      gesture.distance = Math.max(0, gesture.distance + delta * direction);
      if (gesture.distance >= threshold || (gesture.distance >= 32 && velocity * direction >= 0.65)) {
        gesture.committed = true;
        springTo(1 - gesture.origin);
      } else {
        var tension = gesture.distance * 0.65;
        moveTo(coverTop + gesture.origin * travel + tension * direction);
      }
    }

    function finishGesture(gesture) {
      if (gesture && !gesture.committed) springTo(gesture.origin);
    }

    function canHandleGesture(event) {
      return !reducedMotion.matches && !document.body.style.overflow && event.cancelable;
    }

    function onWheel(event) {
      if (!canHandleGesture(event) || event.ctrlKey || event.metaKey) return;
      var delta = event.deltaY;
      if (!delta || Math.abs(event.deltaX) > Math.abs(delta)) return;
      if (!wheel) {
        var origin = gestureOrigin(delta);
        if (origin === null) return;
        wheel = { origin: origin, distance: 0, committed: Boolean(springFrame) };
      }

      event.preventDefault();
      window.clearTimeout(wheelIdle);
      wheelIdle = window.setTimeout(function () {
        finishGesture(wheel);
        wheel = null;
      }, 140);

      if (event.deltaMode === 1) delta *= 36;
      if (event.deltaMode === 2) delta *= window.innerHeight;
      pushGesture(wheel, delta, 0);
    }

    function finishTouch() {
      if (!touch) return;
      finishGesture(touch.gesture);
      touch = null;
    }

    function onTouchStart(event) {
      if (event.touches.length !== 1) {
        finishTouch();
        return;
      }
      var point = event.touches[0];
      touch = { x: point.clientX, y: point.clientY, time: event.timeStamp, gesture: null };
    }

    function onTouchMove(event) {
      if (!touch || !canHandleGesture(event) || event.touches.length !== 1) return;
      var point = event.touches[0];
      var delta = touch.y - point.clientY;
      if (!touch.gesture) {
        var horizontal = Math.abs(point.clientX - touch.x);
        if (Math.max(horizontal, Math.abs(delta)) < 6) return;
        var origin = horizontal > Math.abs(delta) ? null : gestureOrigin(delta);
        if (origin === null) {
          touch = null;
          return;
        }
        touch.gesture = { origin: origin, distance: 0, committed: Boolean(springFrame) };
      }

      event.preventDefault();
      var velocity = delta / Math.max(12, event.timeStamp - touch.time);
      pushGesture(touch.gesture, delta, velocity);
      touch.y = point.clientY;
      touch.time = event.timeStamp;
    }

    function onScroll() {
      if (reducedMotion.matches || springFrame || wheel || (touch && touch.gesture)) return;
      if (!scrollFrame) {
        scrollFrame = window.requestAnimationFrame(function () {
          scrollFrame = 0;
          renderProgress();
        });
      }
      window.clearTimeout(scrollIdle);

      // Native scrolling from the article list, keyboard, or scrollbar can enter the cover.
      var position = window.scrollY - coverTop;
      if (position <= 1 || position >= travel - 1) {
        rest = position <= 1 ? 0 : 1;
      } else {
        scrollIdle = window.setTimeout(function () {
          if (springFrame || wheel || (touch && touch.gesture)) return;
          springTo(Math.abs(position - rest * travel) >= threshold ? 1 - rest : rest);
        }, 140);
      }
    }

    function syncMotionPreference() {
      var animated = !reducedMotion.matches;
      opening.classList.toggle('is-scroll-cover', animated);
      header.classList.toggle('is-cover-header', animated);
      if (!animated) {
        window.cancelAnimationFrame(springFrame);
        window.clearTimeout(wheelIdle);
        window.clearTimeout(scrollIdle);
        springFrame = 0;
        wheel = null;
        touch = null;
        return;
      }

      measureStage();
      if (window.location.hash === '#home-intro') {
        intro.focus({ preventScroll: true });
        moveTo(coverTop + travel);
      }
      onScroll();
    }

    enter.addEventListener('click', function (event) {
      if (reducedMotion.matches || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      if (wheel) wheel.committed = true;
      if (touch && touch.gesture) touch.gesture.committed = true;
      intro.focus({ preventScroll: true });
      springTo(1);
    });

    window.addEventListener('wheel', onWheel, { passive: false });
    window.addEventListener('touchstart', onTouchStart, { passive: true });
    window.addEventListener('touchmove', onTouchMove, { passive: false });
    window.addEventListener('touchend', finishTouch, { passive: true });
    window.addEventListener('touchcancel', finishTouch, { passive: true });
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', measureStage);
    window.addEventListener('pageshow', measureStage);
    reducedMotion.addEventListener('change', syncMotionPreference);
    if (window.ResizeObserver) {
      var observer = new ResizeObserver(measureStage);
      observer.observe(stage);
    }
    syncMotionPreference();
  }

  initHomeCover();
})();
