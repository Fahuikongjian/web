(function () {
  'use strict';

  window.StarloopGames = window.StarloopGames || {};

  const GRID = 20;
  const TICK_MS = 120;
  const BEST_KEY = 'starloop-game-snake-best';
  const DIRECTIONS = {
    up: { x: 0, y: -1 },
    left: { x: -1, y: 0 },
    down: { x: 0, y: 1 },
    right: { x: 1, y: 0 }
  };
  const KEYS = {
    arrowup: 'up', w: 'up', arrowleft: 'left', a: 'left',
    arrowdown: 'down', s: 'down', arrowright: 'right', d: 'right'
  };
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
  let resizeObserver = null;
  let timer = null;
  let phase, snake, heading, turns, food, score, best, swipe;
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

  function stat(stats, label, name) {
    const item = element('div', 'game-stat');
    const labelEl = element('span', 'game-stat-label', label);
    const value = element('span', 'game-stat-value', '0');
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

  function placeFood() {
    const occupied = new Set(snake.map(cell => cell.y * GRID + cell.x));
    const free = [];
    for (let index = 0; index < GRID * GRID; index += 1) {
      if (!occupied.has(index)) free.push(index);
    }
    if (!free.length) return null;
    const index = free[Math.floor(Math.random() * free.length)];
    return { x: index % GRID, y: Math.floor(index / GRID) };
  }

  function resetBoard() {
    snake = [{ x: 9, y: 10 }, { x: 8, y: 10 }, { x: 7, y: 10 }];
    heading = DIRECTIONS.right;
    turns = [];
    score = 0;
    food = placeFood();
  }

  function draw(palette = getPalette()) {
    const { canvas, ctx } = ui;
    const size = Math.max(300, canvas.clientWidth || 400);
    const dpr = window.devicePixelRatio || 1;
    const pixels = Math.max(1, Math.round(size * dpr));
    if (canvas.width !== pixels) canvas.width = pixels;
    if (canvas.height !== pixels) canvas.height = pixels;
    if (!ctx) return;

    const scale = pixels / size;
    const cell = size / GRID;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.fillStyle = palette.bg;
    ctx.fillRect(0, 0, size, size);
    ctx.strokeStyle = palette.grid;
    ctx.lineWidth = 1 / scale;
    ctx.beginPath();
    for (let i = 1; i < GRID; i += 1) {
      const line = (Math.floor(i * cell * scale) + 0.5) / scale;
      ctx.moveTo(line, 0);
      ctx.lineTo(line, size);
      ctx.moveTo(0, line);
      ctx.lineTo(size, line);
    }
    ctx.stroke();

    if (food) {
      const x = (food.x + 0.5) * cell;
      const y = (food.y + 0.5) * cell;
      ctx.save();
      ctx.fillStyle = palette.gold;
      ctx.shadowColor = palette.gold;
      ctx.shadowBlur = 11 * scale;
      ctx.beginPath();
      for (let i = 0; i < 8; i += 1) {
        const angle = i * Math.PI / 4 - Math.PI / 2;
        const radius = cell * (i % 2 === 0 ? 0.43 : 0.14);
        const px = x + Math.cos(angle) * radius;
        const py = y + Math.sin(angle) * radius;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }

    snake.forEach((segment, index) => {
      ctx.fillStyle = index === 0 ? palette.glow : palette.crimson;
      ctx.globalAlpha = index === 0 ? 1 : Math.max(0.5, 1 - index * 0.035);
      const x = segment.x * cell;
      const y = segment.y * cell;
      ctx.fillRect(x + cell * 0.09, y + cell * 0.09, cell * 0.82, cell * 0.82);
      if (index === 0) {
        ctx.fillStyle = palette.bg;
        for (const side of [-1, 1]) {
          const eyeX = x + cell * (0.5 + heading.x * 0.2 + heading.y * side * 0.17);
          const eyeY = y + cell * (0.5 + heading.y * 0.2 + heading.x * side * 0.17);
          ctx.fillRect(eyeX - cell * 0.05, eyeY - cell * 0.05, cell * 0.1, cell * 0.1);
        }
      }
    });
    ctx.globalAlpha = 1;
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
    ui.bestValue.textContent = String(best);
  }

  function setPhase(next) {
    phase = next;
    if (phase === 'playing') {
      if (timer === null) timer = window.setInterval(tick, TICK_MS);
    } else if (timer !== null) {
      window.clearInterval(timer);
      timer = null;
    }

    const playing = phase === 'playing';
    const labels = {
      idle: ['贪吃蛇', '开始'],
      paused: ['已暂停', '继续'],
      over: ['结束', '重开'],
      win: ['已通关', '重开']
    };
    if (playing) {
      ui.toggle.textContent = '暂停';
      if (document.activeElement === ui.overlayButton) ui.toggle.focus();
    } else {
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

  function tick() {
    if (turns.length) heading = turns.shift();
    const head = { x: snake[0].x + heading.x, y: snake[0].y + heading.y };
    const eating = head.x === food.x && head.y === food.y;
    // The tail vacates its cell on this tick unless the snake grows.
    const bodyLength = snake.length - (eating ? 0 : 1);
    const hitsBody = snake.some((cell, index) =>
      index < bodyLength && head.x === cell.x && head.y === cell.y);
    if (head.x < 0 || head.x >= GRID || head.y < 0 || head.y >= GRID || hitsBody) {
      setPhase('over');
      return;
    }

    snake.unshift(head);
    if (eating) {
      score += 1;
      updateStats();
      food = placeFood();
      if (!food) {
        setPhase('win');
        return;
      }
    } else {
      snake.pop();
    }
    draw();
  }

  function restart() {
    if (timer !== null) window.clearInterval(timer);
    timer = null;
    resetBoard();
    updateStats();
    setPhase('playing');
  }

  function toggleGame() {
    if (phase === 'over' || phase === 'win') restart();
    else setPhase(phase === 'playing' ? 'paused' : 'playing');
  }

  function steer(name) {
    if (phase === 'idle') setPhase('playing');
    if (phase !== 'playing' || turns.length === 2) return;
    const next = DIRECTIONS[name];
    const previous = turns.length ? turns[turns.length - 1] : heading;
    if (next.x * previous.x + next.y * previous.y === 0) turns.push(next);
  }

  function onKeyDown(event) {
    const target = event.target;
    if (target && target.closest) {
      if (target.closest(IGNORED_TARGETS)) return;
      const game = target.closest('.game-shell');
      if (game && game !== ui.root) return;
    }
    if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
    const key = event.key.toLowerCase();
    if (key === ' ' || key === 'spacebar') {
      if (target === ui.restart || ui.dpad.contains(target)) return;
      event.preventDefault();
      if (!event.repeat) toggleGame();
    } else if (Object.prototype.hasOwnProperty.call(KEYS, key)) {
      event.preventDefault();
      steer(KEYS[key]);
    }
  }

  function onSwipeStart(event) {
    if (event.pointerType === 'mouse' || swipe) return;
    swipe = { id: event.pointerId, x: event.clientX, y: event.clientY, used: false };
    ui.canvas.setPointerCapture(event.pointerId);
  }

  function onSwipeMove(event) {
    if (!swipe || swipe.id !== event.pointerId || swipe.used) return;
    const x = event.clientX - swipe.x;
    const y = event.clientY - swipe.y;
    if (Math.max(Math.abs(x), Math.abs(y)) < 18) return;
    swipe.used = true;
    steer(Math.abs(x) > Math.abs(y) ? (x > 0 ? 'right' : 'left') : (y > 0 ? 'down' : 'up'));
  }

  function onSwipeEnd(event) {
    if (swipe && swipe.id === event.pointerId) swipe = null;
  }

  function mount(containerEl) {
    unmount();

    const root = element('div', 'game-shell game-shell--snake');
    const hud = element('div', 'game-hud');
    const stats = element('div', 'game-stats');
    const scoreValue = stat(stats, '得分', 'gameScore');
    const bestValue = stat(stats, '最佳', 'gameBest');
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

    const frame = element('div', 'game-canvas-frame game-canvas-frame--square');
    frame.style.position = 'relative';
    const canvas = element('canvas', 'game-canvas');
    canvas.dataset.gameCanvas = 'snake';
    canvas.setAttribute('aria-label', '贪吃蛇画布');
    canvas.width = canvas.height = 400;
    Object.assign(canvas.style, {
      display: 'block', width: '100%', height: 'auto', aspectRatio: '1 / 1', touchAction: 'none'
    });
    const overlay = element('div', 'game-overlay');
    Object.assign(overlay.style, {
      position: 'absolute', inset: '0', placeItems: 'center', pointerEvents: 'none'
    });
    const panel = element('div', 'game-overlay-panel');
    Object.assign(panel.style, {
      textAlign: 'center', padding: '12px 18px', border: '1px solid', borderRadius: '8px'
    });
    const title = element('div', 'game-overlay-title', '贪吃蛇');
    title.setAttribute('role', 'status');
    Object.assign(title.style, { fontWeight: '600', marginBottom: '8px' });
    const overlayButton = button('开始', true);
    overlayButton.style.pointerEvents = 'auto';
    panel.append(title, overlayButton);
    overlay.appendChild(panel);
    frame.append(canvas, overlay);

    const dpad = element('div', 'game-dpad');
    dpad.setAttribute('role', 'group');
    dpad.setAttribute('aria-label', '方向');
    Object.assign(dpad.style, {
      display: 'grid', gridTemplateColumns: 'repeat(3, 44px)', justifyContent: 'center', gap: '4px'
    });
    const controls = [
      ['up', '↑', '上', '1 / 2'], ['left', '←', '左', '2 / 1'],
      ['down', '↓', '下', '2 / 2'], ['right', '→', '右', '2 / 3']
    ];
    for (const [direction, glyph, label, area] of controls) {
      const control = button(glyph);
      control.className = 'game-btn game-dpad-btn';
      control.dataset.dir = direction;
      control.setAttribute('aria-label', label);
      dpad.appendChild(control);
      listen(control, 'click', () => steer(direction));
    }
    root.append(hud, frame, dpad);
    containerEl.appendChild(root);
    ui = {
      root, canvas, ctx: canvas.getContext('2d'), overlay, panel, title, overlayButton,
      toggle, restart: restartButton, dpad, scoreValue, bestValue
    };

    best = readBest();
    resetBoard();
    updateStats();
    setPhase('idle');
    onThemeChange();

    listen(toggle, 'click', toggleGame);
    listen(overlayButton, 'click', toggleGame);
    listen(restartButton, 'click', restart);
    listen(document, 'keydown', onKeyDown);
    listen(window, 'resize', onThemeChange);
    listen(canvas, 'pointerdown', onSwipeStart);
    listen(canvas, 'pointermove', onSwipeMove);
    listen(canvas, 'pointerup', event => {
      onSwipeMove(event);
      onSwipeEnd(event);
    });
    listen(canvas, 'pointercancel', onSwipeEnd);
    listen(canvas, 'lostpointercapture', onSwipeEnd);
    if (window.ResizeObserver) {
      resizeObserver = new window.ResizeObserver(() => {
        if (ui && ui.canvas === canvas) draw();
      });
      resizeObserver.observe(frame);
    }
  }

  function unmount() {
    if (timer !== null) window.clearInterval(timer);
    timer = null;
    if (resizeObserver) resizeObserver.disconnect();
    resizeObserver = null;
    while (listeners.length) listeners.pop()();
    if (ui) ui.root.remove();
    ui = null;
    swipe = null;
  }

  window.StarloopGames.snake = { mount, unmount, onThemeChange };
}());
