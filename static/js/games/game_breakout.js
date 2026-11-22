(function () {
  'use strict';

  window.StarloopGames = window.StarloopGames || {};

  const WIDTH = 520;
  const HEIGHT = 390;
  const ROWS = 5;
  const COLUMNS = 8;
  const RADIUS = 6;
  const PADDLE_WIDTH = 82;
  const PADDLE_HEIGHT = 10;
  const PADDLE_Y = 356;
  const PADDLE_SPEED = 370;
  const BRICK_WIDTH = 54;
  const BRICK_HEIGHT = 16;
  const BEST_KEY = 'starloop-game-breakout-best';
  const IGNORED_TARGETS = 'input, textarea, select, [contenteditable], dialog[open], [role="tab"]';
  const PALETTES = {
    dark: {
      bg: '#120D10', grid: 'rgba(223, 184, 107, 0.10)', crimson: '#E12D4B',
      glow: '#FF4766', gold: '#DFB86B', text: '#F5ECE2', veil: 'rgba(18, 13, 16, 0.36)'
    },
    light: {
      bg: '#F4EDE4', grid: 'rgba(143, 104, 34, 0.12)', crimson: '#C41E3A',
      glow: '#A0152D', gold: '#A97E2C', text: '#1A1417', veil: 'rgba(244, 237, 228, 0.36)'
    }
  };

  let ui = null;
  let raf = null;
  let lastFrame = null;
  let phase, paddleX, ball, bricks, bricksLeft, score, lives, best, round;
  const keys = new Set();
  const listeners = [];

  function getPalette() {
    return document.documentElement.dataset.theme === 'light' ? PALETTES.light : PALETTES.dark;
  }

  function element(tag, className, label) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (label) node.textContent = label;
    return node;
  }

  function button(label, primary = false) {
    const node = element('button', primary ? 'game-btn game-btn--primary' : 'game-btn', label);
    node.type = 'button';
    return node;
  }

  function stat(stats, label, name, initial) {
    const item = element('div', 'game-stat');
    const labelEl = element('span', 'game-stat-label', label);
    const value = element('span', 'game-stat-value', initial);
    value.dataset[name] = '';
    item.append(labelEl, value);
    stats.appendChild(item);
    return value;
  }

  function listen(target, type, handler) {
    target.addEventListener(type, handler);
    listeners.push(() => target.removeEventListener(type, handler));
  }

  function readBest() {
    try {
      const value = Number(window.localStorage.getItem(BEST_KEY));
      return Number.isSafeInteger(value) && value > 0 ? value : 0;
    } catch (error) {
      return 0;
    }
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(value, max));
  }

  function parkBall() {
    paddleX = WIDTH / 2;
    ball = { x: paddleX, y: PADDLE_Y - RADIUS, vx: 0, vy: 0 };
  }

  function buildBricks() {
    const gap = 8;
    const startX = (WIDTH - COLUMNS * BRICK_WIDTH - (COLUMNS - 1) * gap) / 2;
    bricks = [];
    for (let row = 0; row < ROWS; row += 1) {
      for (let column = 0; column < COLUMNS; column += 1) {
        bricks.push({
          x: startX + column * (BRICK_WIDTH + gap),
          y: 36 + row * (BRICK_HEIGHT + gap),
          gold: row % 2 === 0,
          alive: true
        });
      }
    }
    bricksLeft = bricks.length;
    parkBall();
  }

  function roundedRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + width, y, x + width, y + height, radius);
    ctx.arcTo(x + width, y + height, x, y + height, radius);
    ctx.arcTo(x, y + height, x, y, radius);
    ctx.arcTo(x, y, x + width, y, radius);
    ctx.closePath();
    ctx.fill();
  }

  function draw(palette = getPalette()) {
    const { canvas, ctx } = ui;
    const dpr = window.devicePixelRatio || 1;
    const pixelWidth = Math.max(1, Math.round(WIDTH * dpr));
    const pixelHeight = Math.max(1, Math.round(HEIGHT * dpr));
    if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
    if (canvas.height !== pixelHeight) canvas.height = pixelHeight;
    if (!ctx) return;

    const scaleX = pixelWidth / WIDTH;
    const scaleY = pixelHeight / HEIGHT;
    ctx.setTransform(scaleX, 0, 0, scaleY, 0, 0);
    ctx.fillStyle = palette.bg;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    ctx.strokeStyle = palette.grid;
    ctx.lineWidth = 1 / scaleX;
    ctx.beginPath();
    for (let x = 26; x < WIDTH; x += 26) {
      const line = (Math.floor(x * scaleX) + 0.5) / scaleX;
      ctx.moveTo(line, 0);
      ctx.lineTo(line, HEIGHT);
    }
    ctx.stroke();
    ctx.lineWidth = 1 / scaleY;
    ctx.beginPath();
    for (let y = 26; y < HEIGHT; y += 26) {
      const line = (Math.floor(y * scaleY) + 0.5) / scaleY;
      ctx.moveTo(0, line);
      ctx.lineTo(WIDTH, line);
    }
    ctx.stroke();

    for (const brick of bricks) {
      if (!brick.alive) continue;
      ctx.fillStyle = brick.gold ? palette.gold : palette.crimson;
      roundedRect(ctx, brick.x, brick.y, BRICK_WIDTH, BRICK_HEIGHT, 4);
      ctx.globalAlpha = 0.25;
      ctx.fillStyle = brick.gold ? palette.text : palette.glow;
      roundedRect(ctx, brick.x + 3, brick.y + 2, BRICK_WIDTH - 6, 3, 1.5);
      ctx.globalAlpha = 1;
    }
    ctx.fillStyle = palette.crimson;
    roundedRect(ctx, paddleX - PADDLE_WIDTH / 2, PADDLE_Y, PADDLE_WIDTH, PADDLE_HEIGHT, 5);
    ctx.fillStyle = palette.gold;
    roundedRect(ctx, paddleX - 9, PADDLE_Y + 4, 18, 2, 1);
    ctx.save();
    ctx.fillStyle = palette.text;
    ctx.shadowColor = palette.glow;
    ctx.shadowBlur = 12 * dpr;
    ctx.beginPath();
    ctx.arc(ball.x, ball.y, RADIUS, 0, 2 * Math.PI);
    ctx.fill();
    ctx.restore();
  }

  function onThemeChange() {
    if (!ui) return;
    const palette = getPalette();
    ui.root.style.color = palette.text;
    ui.overlay.style.backgroundColor = palette.veil;
    ui.panel.style.backgroundColor = palette.bg;
    ui.panel.style.borderColor = palette.gold;
    draw(palette);
  }

  function updateStats() {
    if (score > best) {
      best = score;
      try {
        window.localStorage.setItem(BEST_KEY, String(best));
      } catch (error) {
        // Keep the current session's best when storage is unavailable.
      }
    }
    ui.scoreValue.textContent = String(score);
    ui.livesValue.textContent = String(lives);
    ui.bestValue.textContent = String(best);
  }

  function stopAnimation() {
    if (raf !== null) window.cancelAnimationFrame(raf);
    raf = null;
    lastFrame = null;
  }

  function setPhase(next) {
    phase = next;
    const playing = phase === 'playing';
    if (playing) {
      if (raf === null) raf = window.requestAnimationFrame(frame);
      ui.toggle.textContent = '暂停';
      if (document.activeElement === ui.overlayButton) ui.toggle.focus();
    } else {
      stopAnimation();
      keys.clear();
      const labels = {
        idle: ['打砖块', '开始'],
        ready: ['待发球', '发球'],
        paused: ['已暂停', '继续'],
        over: ['结束', '重开'],
        win: ['已通关', '下一关']
      };
      const [title, action] = labels[phase];
      ui.title.textContent = title;
      ui.toggle.textContent = action;
      ui.overlayButton.textContent = action;
    }
    ui.overlay.hidden = playing;
    ui.overlay.style.display = playing ? 'none' : 'grid';
    ui.overlay.classList.toggle('is-visible', !playing);
    draw();
  }

  function resetGame() {
    stopAnimation();
    keys.clear();
    score = 0;
    lives = 3;
    round = 1;
    buildBricks();
    updateStats();
  }

  function launch() {
    const speed = Math.min(290 + (round - 1) * 22, 450);
    // Serve toward the center when the paddle starts close to a wall.
    ball.vx = speed * 0.39 * (paddleX > WIDTH / 2 ? -1 : 1);
    ball.vy = -Math.sqrt(speed * speed - ball.vx * ball.vx);
    setPhase('playing');
  }

  function restart() {
    resetGame();
    launch();
  }

  function toggleGame() {
    if (phase === 'playing') setPhase('paused');
    else if (phase === 'paused') setPhase('playing');
    else if (phase === 'over') restart();
    else {
      if (phase === 'win') {
        round += 1;
        buildBricks();
      }
      launch();
    }
  }

  function positionPaddle(x) {
    paddleX = clamp(x, PADDLE_WIDTH / 2, WIDTH - PADDLE_WIDTH / 2);
    if (phase === 'idle' || phase === 'ready') ball.x = paddleX;
  }

  function hitBrick(previousX, previousY) {
    for (const brick of bricks) {
      if (!brick.alive) continue;
      const right = brick.x + BRICK_WIDTH;
      const bottom = brick.y + BRICK_HEIGHT;
      const dx = ball.x - clamp(ball.x, brick.x, right);
      const dy = ball.y - clamp(ball.y, brick.y, bottom);
      if (dx * dx + dy * dy > RADIUS * RADIUS) continue;

      const leftSide = previousX <= brick.x - RADIUS;
      const rightSide = previousX >= right + RADIUS;
      const topSide = previousY <= brick.y - RADIUS;
      const bottomSide = previousY >= bottom + RADIUS;
      // When both faces are candidates at a corner, use the shallower overlap.
      if ((leftSide || rightSide) && (!(topSide || bottomSide) || Math.abs(dx) > Math.abs(dy))) {
        ball.x = leftSide ? brick.x - RADIUS : right + RADIUS;
        ball.vx = leftSide ? -Math.abs(ball.vx) : Math.abs(ball.vx);
      } else if (topSide || bottomSide || Math.abs(dy) >= Math.abs(dx)) {
        const above = topSide || (!bottomSide && ball.y < brick.y + BRICK_HEIGHT / 2);
        ball.y = above ? brick.y - RADIUS : bottom + RADIUS;
        ball.vy = above ? -Math.abs(ball.vy) : Math.abs(ball.vy);
      } else {
        ball.x = dx < 0 ? brick.x - RADIUS : right + RADIUS;
        ball.vx = dx < 0 ? -Math.abs(ball.vx) : Math.abs(ball.vx);
      }
      brick.alive = false;
      bricksLeft -= 1;
      score += 10;
      updateStats();
      if (bricksLeft === 0) setPhase('win');
      return;
    }
  }

  function advanceBall(dt) {
    const previousX = ball.x;
    const previousY = ball.y;
    ball.x += ball.vx * dt;
    ball.y += ball.vy * dt;

    if (ball.x <= RADIUS || ball.x >= WIDTH - RADIUS) {
      ball.x = clamp(ball.x, RADIUS, WIDTH - RADIUS);
      ball.vx = ball.x === RADIUS ? Math.abs(ball.vx) : -Math.abs(ball.vx);
    }
    if (ball.y <= RADIUS) {
      ball.y = RADIUS;
      ball.vy = Math.abs(ball.vy);
    }

    const paddleContactY = PADDLE_Y - RADIUS;
    if (ball.vy > 0 && previousY <= paddleContactY && ball.y >= paddleContactY) {
      const fraction = (paddleContactY - previousY) / (ball.y - previousY);
      const impactX = previousX + (ball.x - previousX) * fraction;
      if (Math.abs(impactX - paddleX) <= PADDLE_WIDTH / 2 + RADIUS) {
        const offset = clamp((impactX - paddleX) / (PADDLE_WIDTH / 2), -1, 1);
        const angle = offset * (Math.PI / 3);
        const speed = Math.min(Math.hypot(ball.vx, ball.vy) + 8, 530);
        ball.x = impactX;
        ball.y = paddleContactY;
        ball.vx = Math.sin(angle) * speed;
        ball.vy = -Math.cos(angle) * speed;
      }
    }

    if (ball.y - RADIUS > HEIGHT) {
      lives -= 1;
      updateStats();
      if (lives > 0) parkBall();
      setPhase(lives > 0 ? 'ready' : 'over');
      return;
    }
    hitBrick(previousX, previousY);
  }

  function frame(now) {
    raf = null;
    if (phase !== 'playing') return;
    const dt = lastFrame === null ? 0 : clamp((now - lastFrame) / 1000, 0, 0.032);
    lastFrame = now;
    const left = keys.has('arrowleft') || keys.has('a');
    const right = keys.has('arrowright') || keys.has('d');
    const movement = (Number(right) - Number(left)) * PADDLE_SPEED;
    // Each step moves the ball at most about four pixels at the speed cap.
    const steps = Math.ceil(dt / 0.0075);
    for (let step = 0; step < steps && phase === 'playing'; step += 1) {
      positionPaddle(paddleX + movement * dt / steps);
      advanceBall(dt / steps);
    }
    if (phase === 'playing') {
      draw();
      raf = window.requestAnimationFrame(frame);
    }
  }

  function acceptsKey(event) {
    const target = event.target;
    if (!target || !target.closest) return true;
    if (target.closest(IGNORED_TARGETS)) return false;
    const game = target.closest('.game-shell');
    return !game || game === ui.root;
  }

  function onKeyDown(event) {
    if (!acceptsKey(event) || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
    const key = event.key.toLowerCase();
    if (key === ' ' || key === 'spacebar') {
      if (event.target === ui.restart) return;
      event.preventDefault();
      if (!event.repeat) toggleGame();
      return;
    }
    const left = key === 'arrowleft' || key === 'a';
    if (!left && key !== 'arrowright' && key !== 'd') return;
    event.preventDefault();
    if (phase === 'playing') keys.add(key);
    else if (phase === 'idle' || phase === 'ready') {
      positionPaddle(paddleX + (left ? -16 : 16));
      draw();
    }
  }

  function onKeyUp(event) {
    if (acceptsKey(event)) keys.delete(event.key.toLowerCase());
  }

  function onFocusIn(event) {
    if (!acceptsKey(event)) keys.clear();
  }

  function onVisibilityChange() {
    if (document.hidden) {
      keys.clear();
      lastFrame = null;
    }
  }

  function onPointerMove(event) {
    if (phase !== 'idle' && phase !== 'ready' && phase !== 'playing') return;
    const rect = ui.canvas.getBoundingClientRect();
    if (!rect.width) return;
    positionPaddle((event.clientX - rect.left) * WIDTH / rect.width);
    if (phase !== 'playing') draw();
  }

  function mount(containerEl) {
    unmount();

    const root = element('div', 'game-shell game-shell--breakout');
    const hud = element('div', 'game-hud');
    const stats = element('div', 'game-stats');
    const scoreValue = stat(stats, '得分', 'gameScore', '0');
    const livesValue = stat(stats, '生命', 'gameLives', '3');
    const bestValue = stat(stats, '最佳', 'gameBest', '0');
    const actions = element('div', 'game-actions');
    const toggle = button('开始');
    toggle.dataset.gameToggle = '';
    const restartButton = button('重开', true);
    restartButton.dataset.gameRestart = '';
    actions.append(toggle, restartButton);
    hud.append(stats, actions);
    Object.assign(root.style, { display: 'grid', gap: '10px' });
    Object.assign(hud.style, {
      display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px'
    });
    for (const group of [stats, actions]) {
      Object.assign(group.style, { display: 'flex', gap: '10px', flexWrap: 'wrap' });
    }

    const frameEl = element('div', 'game-canvas-frame game-canvas-frame--wide');
    frameEl.style.position = 'relative';
    const canvas = element('canvas', 'game-canvas');
    canvas.dataset.gameCanvas = 'breakout';
    canvas.setAttribute('aria-label', '打砖块画布');
    canvas.width = WIDTH;
    canvas.height = HEIGHT;
    Object.assign(canvas.style, {
      display: 'block', width: '100%', height: 'auto', aspectRatio: '4 / 3', touchAction: 'none'
    });
    const overlay = element('div', 'game-overlay');
    Object.assign(overlay.style, {
      position: 'absolute', inset: '0', placeItems: 'center', pointerEvents: 'none'
    });
    const panel = element('div', 'game-overlay-panel');
    Object.assign(panel.style, {
      textAlign: 'center', padding: '12px 18px', border: '1px solid', borderRadius: '8px'
    });
    const title = element('div', 'game-overlay-title', '打砖块');
    title.setAttribute('role', 'status');
    Object.assign(title.style, { fontWeight: '600', marginBottom: '8px' });
    const overlayButton = button('开始', true);
    overlayButton.style.pointerEvents = 'auto';
    panel.append(title, overlayButton);
    overlay.appendChild(panel);
    frameEl.append(canvas, overlay);
    root.append(hud, frameEl);
    containerEl.appendChild(root);

    ui = {
      root, canvas, ctx: canvas.getContext('2d'), overlay, panel, title, overlayButton,
      toggle, restart: restartButton, scoreValue, livesValue, bestValue
    };
    best = readBest();
    resetGame();
    setPhase('idle');
    onThemeChange();

    listen(toggle, 'click', toggleGame);
    listen(overlayButton, 'click', toggleGame);
    listen(restartButton, 'click', restart);
    listen(document, 'keydown', onKeyDown);
    listen(document, 'keyup', onKeyUp);
    listen(document, 'focusin', onFocusIn);
    listen(document, 'visibilitychange', onVisibilityChange);
    listen(window, 'blur', () => keys.clear());
    listen(window, 'resize', onThemeChange);
    listen(canvas, 'pointerdown', onPointerMove);
    listen(canvas, 'pointermove', onPointerMove);
  }

  function unmount() {
    stopAnimation();
    keys.clear();
    while (listeners.length) listeners.pop()();
    if (ui) ui.root.remove();
    ui = null;
  }

  window.StarloopGames.breakout = { mount, unmount, onThemeChange };
}());
