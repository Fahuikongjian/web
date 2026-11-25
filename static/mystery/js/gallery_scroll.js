(function (window, document) {
  "use strict";

  var INTERACTIVE_DRAG_IGNORE =
    "a, button, summary, details, input, select, textarea, label";
  var INPUT_FOCUS_IGNORE =
    "input, textarea, select, [contenteditable='true'], [contenteditable='']";
  var BOUNDARY_EPSILON = 2;
  var DRAG_THRESHOLD = 6;

  var motionQuery =
    typeof window.matchMedia === "function"
      ? window.matchMedia("(prefers-reduced-motion: reduce)")
      : null;

  function prefersReducedMotion() {
    return Boolean(motionQuery && motionQuery.matches);
  }

  function clamp(value, min, max) {
    if (value < min) return min;
    if (value > max) return max;
    return value;
  }

  function pad2(num) {
    return num < 10 ? "0" + num : String(num);
  }

  function nowMs() {
    return typeof window.performance !== "undefined" &&
      typeof window.performance.now === "function"
      ? window.performance.now()
      : Date.now();
  }

  // Allow wheel events to scroll nested open vertical containers (such as an
  // expanded <details> panel on short screens) before panning the reel.
  function hasVerticalScrollRoom(rawTarget, deltaY, stage, reel) {
    if (!rawTarget || deltaY === 0) return false;
    var el = rawTarget.nodeType === 1 ? rawTarget : rawTarget.parentElement;
    while (el && el !== reel && el !== stage && el !== document.documentElement) {
      if (el.tagName !== "DETAILS" || el.open) {
        var overflowY = window.getComputedStyle(el).overflowY;
        if (overflowY === "auto" || overflowY === "scroll" || overflowY === "overlay") {
          if (el.scrollHeight > el.clientHeight + 2) {
            if (
              deltaY > 0 &&
              el.scrollTop + el.clientHeight < el.scrollHeight - 1.5
            ) {
              return true;
            }
            if (deltaY < 0 && el.scrollTop > 1.5) {
              return true;
            }
          }
        }
      }
      el = el.parentElement;
    }
    return false;
  }

  function initStage(stage, stageIndex, totalStages) {
    if (!stage || stage.dataset.reelInit === "1") return;
    var reel = stage.querySelector("[data-horizontal-reel]");
    if (!reel) return;
    stage.dataset.reelInit = "1";

    function findControl(selector) {
      return (
        stage.querySelector(selector) ||
        (totalStages === 1 ? document.querySelector(selector) : null)
      );
    }

    var prevBtn = findControl("[data-reel-prev]");
    var nextBtn = findControl("[data-reel-next]");
    var progressEl = findControl("[data-reel-progress]");
    var counterEl = findControl("[data-reel-counter]");
    var cards = Array.prototype.slice.call(
      reel.querySelectorAll("[data-reel-card]")
    );

    if (progressEl) {
      progressEl.style.transformOrigin = "left center";
    }

    var animFrame = 0;
    var animStartTime = 0;
    var animStartPos = reel.scrollLeft;
    var animDuration = 220;
    var targetScroll = reel.scrollLeft;
    var activeIndex = 0;
    var dragState = null;
    var suppressClick = false;
    var prevUserSelect = "";
    var prevCursor = "";

    function getMaxScroll() {
      return Math.max(0, reel.scrollWidth - reel.clientWidth);
    }

    function setScrollLeftInstant(value) {
      var clamped = clamp(value, 0, getMaxScroll());
      var prevBehavior = reel.style.scrollBehavior;
      reel.style.scrollBehavior = "auto";
      reel.scrollLeft = clamped;
      reel.style.scrollBehavior = prevBehavior;
    }

    function setDisabledState(btn, disabled) {
      if (!btn) return;
      var flag = Boolean(disabled);
      btn.classList.toggle("disabled", flag);
      if ("disabled" in btn) {
        btn.disabled = flag;
      } else {
        btn.setAttribute("aria-disabled", String(flag));
      }
    }

    function computeActiveIndex(scrollLeft, maxScroll) {
      if (cards.length === 0) return -1;
      if (cards.length === 1) return 0;

      var reelRect = reel.getBoundingClientRect();
      if (maxScroll <= BOUNDARY_EPSILON) {
        var firstRect = cards[0].getBoundingClientRect();
        var secondRect = cards[1].getBoundingClientRect();
        if (secondRect.top > firstRect.bottom - 4) {
          var viewMidY =
            (window.innerHeight || document.documentElement.clientHeight || 0) / 2;
          var bestVertIdx = 0;
          var bestVertDist = Infinity;
          for (var v = 0; v < cards.length; v++) {
            var vRect = cards[v].getBoundingClientRect();
            var vDist = Math.abs(vRect.top + vRect.height / 2 - viewMidY);
            if (vDist < bestVertDist) {
              bestVertDist = vDist;
              bestVertIdx = v;
            }
          }
          return bestVertIdx;
        }
        return 0;
      }

      // Sweep focus between the first and last card centers so 01..N map monotonically
      // from scrollLeft=0 to maxScroll on wide desktop viewports as well as mobile.
      var progress = clamp(scrollLeft / maxScroll, 0, 1);
      var firstCardRect = cards[0].getBoundingClientRect();
      var lastCardRect = cards[cards.length - 1].getBoundingClientRect();
      var firstCenter =
        firstCardRect.left - reelRect.left + scrollLeft + firstCardRect.width / 2;
      var lastCenter =
        lastCardRect.left - reelRect.left + scrollLeft + lastCardRect.width / 2;
      var focusTrackX = firstCenter + progress * (lastCenter - firstCenter);

      var bestIndex = 0;
      var bestDistance = Infinity;
      for (var i = 0; i < cards.length; i++) {
        var rect = cards[i].getBoundingClientRect();
        var cardCenter = rect.left - reelRect.left + scrollLeft + rect.width / 2;
        var distance = Math.abs(cardCenter - focusTrackX);
        if (distance < bestDistance) {
          bestDistance = distance;
          bestIndex = i;
        }
      }
      return bestIndex;
    }

    function updateHUD() {
      var maxScroll = getMaxScroll();
      var scrollLeft = clamp(reel.scrollLeft, 0, maxScroll);
      var canScroll = reel.scrollWidth > reel.clientWidth + BOUNDARY_EPSILON;

      setDisabledState(prevBtn, !canScroll || scrollLeft <= BOUNDARY_EPSILON);
      setDisabledState(nextBtn, !canScroll || scrollLeft >= maxScroll - BOUNDARY_EPSILON);

      if (progressEl) {
        var base = cards.length > 0 ? 1 / cards.length : 1;
        var ratio =
          canScroll && maxScroll > 0
            ? base + (1 - base) * clamp(scrollLeft / maxScroll, 0, 1)
            : 1;
        progressEl.style.transform = "scaleX(" + clamp(ratio, 0, 1) + ")";
      }

      activeIndex = computeActiveIndex(scrollLeft, maxScroll);
      for (var i = 0; i < cards.length; i++) {
        cards[i].classList.toggle("is-active", i === activeIndex);
      }

      if (counterEl) {
        var readout =
          cards.length > 0
            ? pad2(activeIndex + 1) + " / " + pad2(cards.length)
            : "00 / 00";
        if (counterEl.textContent !== readout) {
          counterEl.textContent = readout;
        }
      }
    }

    function stopAnimation() {
      if (animFrame) {
        window.cancelAnimationFrame(animFrame);
        animFrame = 0;
      }
    }

    function stepAnimation() {
      animFrame = 0;
      var maxScroll = getMaxScroll();
      targetScroll = clamp(targetScroll, 0, maxScroll);

      var elapsed = nowMs() - animStartTime;
      var progress = animDuration > 0 ? clamp(elapsed / animDuration, 0, 1) : 1;
      var eased = 1 - Math.pow(1 - progress, 3);
      var next = animStartPos + (targetScroll - animStartPos) * eased;

      if (progress >= 1 || Math.abs(targetScroll - next) <= 0.5) {
        setScrollLeftInstant(targetScroll);
        updateHUD();
        return;
      }

      setScrollLeftInstant(next);
      updateHUD();
      animFrame = window.requestAnimationFrame(stepAnimation);
    }

    function animateTo(nextTarget, immediateRatio, rawDirectionDelta) {
      var maxScroll = getMaxScroll();
      var clampedTarget = clamp(nextTarget, 0, maxScroll);
      var currentLeft = reel.scrollLeft;

      if (prefersReducedMotion()) {
        stopAnimation();
        targetScroll = clampedTarget;
        setScrollLeftInstant(clampedTarget);
        updateHUD();
        return;
      }

      var prevTarget = animFrame ? targetScroll : currentLeft;
      targetScroll = clampedTarget;

      if (immediateRatio > 0) {
        var added = clampedTarget - prevTarget;
        var toTarget = clampedTarget - currentLeft;
        var step = 0;
        if (!animFrame) {
          step = toTarget;
        } else if (
          rawDirectionDelta !== 0 &&
          added * rawDirectionDelta >= 0 &&
          toTarget * rawDirectionDelta > 0
        ) {
          step = Math.abs(toTarget) < Math.abs(added) ? toTarget : added;
        }
        if (step !== 0) {
          setScrollLeftInstant(
            clamp(currentLeft + step * immediateRatio, 0, maxScroll)
          );
        }
      }

      updateHUD();

      var remaining = Math.abs(targetScroll - reel.scrollLeft);
      if (remaining > 0.75) {
        animStartPos = reel.scrollLeft;
        animStartTime = nowMs();
        animDuration = clamp(160 + remaining * 0.2, 180, 300);
        if (!animFrame) {
          animFrame = window.requestAnimationFrame(stepAnimation);
        }
      } else {
        stopAnimation();
        setScrollLeftInstant(targetScroll);
        updateHUD();
      }
    }

    function getCardStep() {
      if (cards.length >= 2) {
        var firstRect = cards[0].getBoundingClientRect();
        var secondRect = cards[1].getBoundingClientRect();
        var span = Math.abs(secondRect.left - firstRect.left);
        if (span > 0) return Math.round(span);
        if (firstRect.width > 0) return Math.round(firstRect.width);
      } else if (cards.length === 1) {
        var singleWidth = cards[0].getBoundingClientRect().width;
        if (singleWidth > 0) return Math.round(singleWidth);
      }
      return Math.max(240, Math.round(reel.clientWidth * 0.72));
    }

    function scrollByCard(direction) {
      var maxScroll = getMaxScroll();
      if (maxScroll <= BOUNDARY_EPSILON) return;
      var base = animFrame ? targetScroll : reel.scrollLeft;
      var step = getCardStep();
      var nextTarget = clamp(base + direction * step, 0, maxScroll);
      if (nextTarget <= 4) nextTarget = 0;
      if (maxScroll - nextTarget <= 4) nextTarget = maxScroll;
      animateTo(nextTarget, 0.22, direction);
    }

    function onWheel(event) {
      if (event.ctrlKey) return;
      if (reel.scrollWidth <= reel.clientWidth + BOUNDARY_EPSILON) return;
      if (event.deltaY === 0 || Math.abs(event.deltaY) < Math.abs(event.deltaX)) {
        return;
      }
      if (hasVerticalScrollRoom(event.target, event.deltaY, stage, reel)) {
        return;
      }

      event.preventDefault();

      var modeScale = 1;
      if (event.deltaMode === 1) {
        modeScale = 32;
      } else if (event.deltaMode === 2) {
        modeScale = reel.clientWidth * 0.85;
      }

      var rawDelta = event.deltaY * modeScale;
      var maxScroll = getMaxScroll();
      var baseTarget = animFrame ? targetScroll : reel.scrollLeft;
      var nextTarget = clamp(baseTarget + rawDelta, 0, maxScroll);

      animateTo(nextTarget, 0.45, rawDelta);
    }

    function onKeyDown(event) {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }
      if (reel.scrollWidth <= reel.clientWidth + BOUNDARY_EPSILON) return;

      var targetEl = event.target;
      if (targetEl && targetEl.closest && targetEl.closest(INPUT_FOCUS_IGNORE)) {
        return;
      }

      var activeEl = document.activeElement;
      if (activeEl && activeEl.closest && activeEl.closest(INPUT_FOCUS_IGNORE)) {
        return;
      }

      var onBody =
        !activeEl ||
        activeEl === document.body ||
        activeEl === document.documentElement;
      var focusAllowed = onBody ? stageIndex === 0 : stage.contains(activeEl);
      if (!focusAllowed) return;

      var maxScroll = getMaxScroll();
      if (event.key === "ArrowRight") {
        event.preventDefault();
        scrollByCard(1);
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        scrollByCard(-1);
      } else if (event.key === "Home") {
        event.preventDefault();
        animateTo(0, 0.25, -1);
      } else if (event.key === "End") {
        event.preventDefault();
        animateTo(maxScroll, 0.25, 1);
      }
    }

    function onPointerMove(event) {
      if (!dragState || event.pointerId !== dragState.pointerId) return;
      var dx = event.clientX - dragState.startX;

      if (!dragState.active) {
        if (Math.abs(dx) <= DRAG_THRESHOLD) return;
        dragState.active = true;
        dragState.moved = true;
        reel.classList.add("is-dragging");
        prevUserSelect = reel.style.userSelect;
        prevCursor = reel.style.cursor;
        reel.style.userSelect = "none";
        reel.style.cursor = "grabbing";
        if (window.getSelection) {
          var selection = window.getSelection();
          if (selection && !selection.isCollapsed) {
            selection.removeAllRanges();
          }
        }
        if (typeof reel.setPointerCapture === "function") {
          try {
            reel.setPointerCapture(dragState.pointerId);
          } catch (_err) {
            // Ignore synthetic PointerEvents without active capture state.
          }
        }
      }

      var next = clamp(dragState.startScrollLeft - dx, 0, getMaxScroll());
      setScrollLeftInstant(next);
      targetScroll = reel.scrollLeft;
      updateHUD();
    }

    function endDrag(event) {
      if (!dragState) return;
      if (event && event.pointerId !== undefined && event.pointerId !== dragState.pointerId) {
        return;
      }

      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", endDrag);
      window.removeEventListener("pointercancel", endDrag);
      window.removeEventListener("blur", endDrag);

      if (dragState.active) {
        reel.classList.remove("is-dragging");
        reel.style.userSelect = prevUserSelect;
        reel.style.cursor = prevCursor;
        if (
          typeof reel.hasPointerCapture === "function" &&
          typeof reel.releasePointerCapture === "function"
        ) {
          try {
            if (reel.hasPointerCapture(dragState.pointerId)) {
              reel.releasePointerCapture(dragState.pointerId);
            }
          } catch (_err) {
            // Ignore capture release errors on detached pointers.
          }
        }
      }

      if (dragState.moved) {
        suppressClick = true;
        window.setTimeout(function () {
          suppressClick = false;
        }, 0);
      }

      dragState = null;
    }

    function onPointerDown(event) {
      if (event.button !== 0 || event.pointerType === "touch") return;
      if (getMaxScroll() <= BOUNDARY_EPSILON) return;
      if (
        event.target &&
        event.target.closest &&
        event.target.closest(INTERACTIVE_DRAG_IGNORE)
      ) {
        return;
      }

      stopAnimation();
      dragState = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startScrollLeft: reel.scrollLeft,
        active: false,
        moved: false
      };

      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", endDrag);
      window.addEventListener("pointercancel", endDrag);
      window.addEventListener("blur", endDrag);
    }

    function onClickCapture(event) {
      if (!suppressClick) return;
      if (
        event.target &&
        event.target.closest &&
        event.target.closest(INTERACTIVE_DRAG_IGNORE)
      ) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      suppressClick = false;
    }

    function onDragStart(event) {
      if (dragState && dragState.active) {
        event.preventDefault();
      }
    }

    function onReelScroll() {
      if (!animFrame) {
        targetScroll = reel.scrollLeft;
      }
      updateHUD();
    }

    function syncAfterLayoutChange() {
      targetScroll = clamp(reel.scrollLeft, 0, getMaxScroll());
      updateHUD();
    }

    function onDetailsToggle() {
      syncAfterLayoutChange();
      window.requestAnimationFrame(syncAfterLayoutChange);
    }

    stage.addEventListener("wheel", onWheel, { passive: false });
    reel.addEventListener("scroll", onReelScroll, { passive: true });
    reel.addEventListener("pointerdown", onPointerDown);
    reel.addEventListener("click", onClickCapture, true);
    reel.addEventListener("dragstart", onDragStart);

    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        scrollByCard(-1);
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        scrollByCard(1);
      });
    }

    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("resize", syncAfterLayoutChange, { passive: true });
    if (document.readyState !== "complete") {
      window.addEventListener("load", syncAfterLayoutChange, { once: true });
    }

    // HTML <details> toggle events do not bubble in all engines; attach directly and on capture.
    stage.addEventListener("toggle", onDetailsToggle, true);
    var detailsList = stage.querySelectorAll("details");
    for (var d = 0; d < detailsList.length; d++) {
      detailsList[d].addEventListener("toggle", onDetailsToggle);
    }

    if (typeof window.ResizeObserver === "function") {
      var observer = new window.ResizeObserver(syncAfterLayoutChange);
      observer.observe(reel);
    }

    updateHUD();
  }

  function initAllStages() {
    var stages = document.querySelectorAll("[data-reel-stage]");
    for (var i = 0; i < stages.length; i++) {
      initStage(stages[i], i, stages.length);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAllStages, { once: true });
  } else {
    initAllStages();
  }
})(window, document);
