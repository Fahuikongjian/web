(function () {
  'use strict';

  window.StarloopGames = window.StarloopGames || {};

  const size = 4;
  const bestKey = 'starloop-game-2048-best';
  const directions = {
    ArrowUp: 'up',
    ArrowLeft: 'left',
    ArrowDown: 'down',
    ArrowRight: 'right'
  };
  let dispose = null;

  function element(tag, className, label) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (label) node.textContent = label;
    return node;
  }

  function button(label, className, attribute) {
    const node = element('button', className, label);
    node.type = 'button';
    if (attribute) node.setAttribute(attribute, '');
    return node;
  }

  function stat(label, attribute) {
    const node = element('div', 'game-stat');
    const value = element('span', 'game-stat-value', '0');
    value.setAttribute(attribute, '');
    node.appendChild(element('span', 'game-stat-label', label));
    node.appendChild(value);
    return { node, value };
  }

  function addTile(board) {
    const empty = [];
    board.forEach((value, index) => {
      if (value === 0) empty.push(index);
    });
    if (empty.length) {
      const index = empty[Math.floor(Math.random() * empty.length)];
      board[index] = Math.random() < 0.9 ? 2 : 4;
    }
  }

  function moveAvailable(board) {
    return board.some((value, index) =>
      value === 0 ||
      (index % size < size - 1 && value === board[index + 1]) ||
      (index < board.length - size && value === board[index + size])
    );
  }

  function mount(containerEl) {
    unmount();
    const root = element('div', 'game-shell game-shell--2048');
    const hud = element('div', 'game-hud');
    const stats = element('div', 'game-stats');
    const scoreStat = stat('得分', 'data-game-score');
    const bestStat = stat('最佳', 'data-game-best');
    stats.appendChild(scoreStat.node);
    stats.appendChild(bestStat.node);
    const actions = element('div', 'game-actions');
    const undoButton = button('撤销', 'game-btn', 'data-game-undo');
    const restartButton = button('重开', 'game-btn game-btn--primary', 'data-game-restart');
    actions.appendChild(undoButton);
    actions.appendChild(restartButton);
    hud.appendChild(stats);
    hud.appendChild(actions);
    root.appendChild(hud);

    const frame = element('div', 'game-board-frame');
    const grid = element('div', 'g2048-grid');
    grid.dataset.gameBoard = '2048';
    grid.setAttribute('role', 'application');
    grid.setAttribute('aria-label', '2048 棋盘');
    grid.style.touchAction = 'none';
    const tiles = Array.from({ length: size * size }, () => {
      const cell = element('div', 'g2048-cell');
      const tile = element('div', 'g2048-tile');
      cell.appendChild(tile);
      grid.appendChild(cell);
      return tile;
    });
    frame.appendChild(grid);

    const overlay = element('div', 'game-overlay');
    const title = element('div', 'game-overlay-title');
    title.setAttribute('role', 'status');
    const continueButton = button('继续', 'game-btn');
    const replayButton = button('再来一局', 'game-btn game-btn--primary');
    overlay.appendChild(title);
    overlay.appendChild(continueButton);
    overlay.appendChild(replayButton);
    frame.appendChild(overlay);
    root.appendChild(frame);

    const dpad = element('div', 'game-dpad');
    [['up', '▲', '上'], ['left', '◀', '左'], ['down', '▼', '下'], ['right', '▶', '右']]
      .forEach(([direction, symbol, label]) => {
        const control = button(symbol, 'game-btn game-dpad-btn');
        control.dataset.dir = direction;
        control.setAttribute('aria-label', label);
        dpad.appendChild(control);
      });
    root.appendChild(dpad);

    let board;
    let score;
    let previous;
    let continued;
    let status;
    let startTouch = null;
    let best = 0;
    try {
      best = Math.max(0, Number(window.localStorage.getItem(bestKey)) || 0);
    } catch (error) {
      // The game can run when browser storage is unavailable.
    }

    function render() {
      tiles.forEach((tile, index) => {
        const value = board[index];
        tile.dataset.value = String(value);
        tile.textContent = value ? String(value) : '';
      });
      scoreStat.value.textContent = String(score);
      bestStat.value.textContent = String(best);
      undoButton.disabled = previous === null;
      overlay.hidden = status === '';
      overlay.classList.toggle('is-visible', !overlay.hidden);
      title.textContent = status === 'won' ? '达成 2048！' : status === 'lost' ? '游戏结束' : '';
      continueButton.hidden = status !== 'won';
    }

    function restart() {
      board = Array(size * size).fill(0);
      score = 0;
      previous = null;
      continued = false;
      status = '';
      startTouch = null;
      addTile(board);
      addTile(board);
      render();
    }

    function move(direction) {
      if (status) return;
      const vertical = direction === 'up' || direction === 'down';
      const reverse = direction === 'right' || direction === 'down';
      const next = board.slice();
      let points = 0;
      for (let line = 0; line < size; line += 1) {
        const indices = [];
        for (let step = 0; step < size; step += 1) {
          const offset = reverse ? size - 1 - step : step;
          indices.push(vertical ? offset * size + line : line * size + offset);
        }
        const values = indices.map(index => board[index]).filter(Boolean);
        const merged = [];
        for (let i = 0; i < values.length; i += 1) {
          let value = values[i];
          if (value === values[i + 1]) {
            value *= 2;
            points += value;
            i += 1;
          }
          merged.push(value);
        }
        indices.forEach((index, step) => {
          next[index] = merged[step] || 0;
        });
      }
      if (next.every((value, index) => value === board[index])) return;

      previous = { board, score, continued };
      board = next;
      score += points;
      if (score > best) {
        best = score;
        try {
          window.localStorage.setItem(bestKey, String(best));
        } catch (error) {
          // Keep the best score for this mount even without storage.
        }
      }
      addTile(board);
      if (!continued && board.includes(2048)) status = 'won';
      else if (!moveAvailable(board)) status = 'lost';
      render();
    }

    function onClick(event) {
      const control = event.target.closest('button');
      if (!control) return;
      if (control === restartButton || control === replayButton) restart();
      if (control === undoButton && previous) {
        ({ board, score, continued } = previous);
        previous = null;
        status = '';
        render();
      }
      if (control === continueButton && status === 'won') {
        continued = true;
        status = moveAvailable(board) ? '' : 'lost';
        render();
      }
      if (dpad.contains(control)) move(control.dataset.dir);
    }

    function onKeyDown(event) {
      const direction = directions[event.key];
      if (!Object.prototype.hasOwnProperty.call(directions, event.key) ||
          status || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;

      const target = event.target;
      const focused = target && (target.closest ? target : target.parentElement);
      if (focused && focused.closest('input, textarea, select, [contenteditable], dialog[open], [role="tab"]')) {
        return;
      }
      event.preventDefault();
      move(direction);
    }

    function onTouchStart(event) {
      startTouch = event.touches.length === 1 ? event.touches[0] : null;
    }

    function onTouchEnd(event) {
      const start = startTouch;
      startTouch = null;
      if (!start) return;
      const end = Array.prototype.find.call(event.changedTouches, touch => touch.identifier === start.identifier);
      if (!end) return;
      const x = end.clientX - start.clientX;
      const y = end.clientY - start.clientY;
      if (Math.max(Math.abs(x), Math.abs(y)) < 24) return;
      if (Math.abs(x) >= Math.abs(y)) move(x > 0 ? 'right' : 'left');
      else move(y > 0 ? 'down' : 'up');
    }

    function onTouchCancel() {
      startTouch = null;
    }

    restart();
    containerEl.appendChild(root);
    root.addEventListener('click', onClick);
    document.addEventListener('keydown', onKeyDown);
    grid.addEventListener('touchstart', onTouchStart, { passive: true });
    grid.addEventListener('touchend', onTouchEnd, { passive: true });
    grid.addEventListener('touchcancel', onTouchCancel);
    dispose = function () {
      document.removeEventListener('keydown', onKeyDown);
      root.removeEventListener('click', onClick);
      grid.removeEventListener('touchstart', onTouchStart);
      grid.removeEventListener('touchend', onTouchEnd);
      grid.removeEventListener('touchcancel', onTouchCancel);
      root.remove();
    };
  }

  function unmount() {
    if (dispose) {
      dispose();
      dispose = null;
    }
  }

  window.StarloopGames.game2048 = { mount, unmount };
}());
