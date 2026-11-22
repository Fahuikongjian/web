(function () {
  'use strict';

  window.StarloopGames = window.StarloopGames || {};

  const modes = [{ size: 9, mines: 10 }, { size: 12, mines: 22 }];
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
    const value = element('span', 'game-stat-value');
    value.setAttribute(attribute, '');
    node.appendChild(element('span', 'game-stat-label', label));
    node.appendChild(value);
    return { node, value };
  }

  function mount(containerEl) {
    unmount();
    const root = element('div', 'game-shell game-shell--minesweeper');
    const hud = element('div', 'game-hud');
    const stats = element('div', 'game-stats');
    const remainingStat = stat('雷数', 'data-mine-remaining');
    const timerStat = stat('用时', 'data-game-timer');
    stats.appendChild(remainingStat.node);
    stats.appendChild(timerStat.node);
    const actions = element('div', 'game-actions');
    const modeButton = button('9×9', 'game-btn', 'data-mine-mode');
    const flagButton = button('插旗', 'game-btn', 'data-mine-flag-toggle');
    const restartButton = button('重开', 'game-btn game-btn--primary', 'data-game-restart');
    actions.appendChild(modeButton);
    actions.appendChild(flagButton);
    actions.appendChild(restartButton);
    hud.appendChild(stats);
    hud.appendChild(actions);
    root.appendChild(hud);

    const frame = element('div', 'game-board-frame');
    const grid = element('div', 'mine-grid');
    grid.dataset.gameBoard = 'minesweeper';
    frame.appendChild(grid);
    const overlay = element('div', 'game-overlay');
    const title = element('div', 'game-overlay-title');
    title.setAttribute('role', 'status');
    const replayButton = button('再来一局', 'game-btn game-btn--primary');
    overlay.appendChild(title);
    overlay.appendChild(replayButton);
    frame.appendChild(overlay);
    root.appendChild(frame);

    let mode = 0;
    let cells;
    let flags;
    let revealed;
    let flagMode;
    let status;
    let startedAt;
    let timer = null;

    function updateTimer() {
      timerStat.value.textContent = `${Math.floor((Date.now() - startedAt) / 1000)}s`;
    }

    function stopTimer() {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    function updateRemaining() {
      remainingStat.value.textContent = String(modes[mode].mines - flags);
    }

    function setFlagMode(active) {
      flagMode = active;
      flagButton.classList.toggle('is-active', active);
      flagButton.setAttribute('aria-pressed', String(active));
    }

    function restart() {
      stopTimer();
      const { size } = modes[mode];
      modeButton.textContent = `${size}×${size}`;
      grid.style.setProperty('--mine-cols', String(size));
      grid.textContent = '';
      const fragment = document.createDocumentFragment();
      cells = Array.from({ length: size * size }, (_, index) => {
        const node = button('', 'mine-cell');
        const row = Math.floor(index / size);
        const col = index % size;
        const label = `第 ${row + 1} 行，第 ${col + 1} 列`;
        node.dataset.row = String(row);
        node.dataset.col = String(col);
        node.setAttribute('aria-label', label);
        fragment.appendChild(node);
        return { node, index, row, col, label, mine: false, adjacent: 0, flagged: false, revealed: false };
      });
      grid.appendChild(fragment);
      flags = 0;
      revealed = 0;
      status = 'ready';
      overlay.hidden = true;
      overlay.classList.remove('is-visible');
      title.textContent = '';
      timerStat.value.textContent = '0s';
      setFlagMode(false);
      updateRemaining();
    }

    function neighbors(cell) {
      const { size } = modes[mode];
      const adjacent = [];
      for (let row = Math.max(0, cell.row - 1); row <= Math.min(size - 1, cell.row + 1); row += 1) {
        for (let col = Math.max(0, cell.col - 1); col <= Math.min(size - 1, cell.col + 1); col += 1) {
          const index = row * size + col;
          if (index !== cell.index) adjacent.push(cells[index]);
        }
      }
      return adjacent;
    }

    function start(first) {
      const safe = new Set(neighbors(first));
      safe.add(first);
      const candidates = cells.filter(cell => !safe.has(cell));
      for (let i = 0; i < modes[mode].mines; i += 1) {
        const pick = i + Math.floor(Math.random() * (candidates.length - i));
        [candidates[i], candidates[pick]] = [candidates[pick], candidates[i]];
        const mine = candidates[i];
        mine.mine = true;
        neighbors(mine).forEach(cell => {
          cell.adjacent += 1;
        });
      }
      status = 'playing';
      startedAt = Date.now();
      timer = window.setInterval(updateTimer, 1000);
    }

    function finish(won, exploded) {
      status = 'finished';
      updateTimer();
      stopTimer();
      cells.forEach(cell => {
        if (!cell.mine) return;
        cell.node.classList.add('is-mine');
        if (cell === exploded) cell.node.classList.add('is-exploded');
        cell.node.textContent = cell.flagged ? '⚑' : '✹';
        cell.node.setAttribute('aria-label', `${cell.label}：雷`);
      });
      title.textContent = won ? '扫雷成功！' : '踩到雷了！';
      overlay.hidden = false;
      overlay.classList.add('is-visible');
    }

    function reveal(first) {
      if (status === 'finished' || first.flagged || first.revealed) return;
      if (status === 'ready') start(first);
      if (first.mine) {
        first.node.classList.add('is-revealed');
        finish(false, first);
        return;
      }

      const pending = [first];
      first.revealed = true;
      while (pending.length) {
        const cell = pending.pop();
        revealed += 1;
        cell.node.classList.add('is-revealed');
        if (cell.adjacent) {
          cell.node.dataset.adjacent = String(cell.adjacent);
          cell.node.textContent = String(cell.adjacent);
          cell.node.setAttribute('aria-label', `${cell.label}：${cell.adjacent}`);
        } else {
          cell.node.setAttribute('aria-label', `${cell.label}：空`);
          neighbors(cell).forEach(neighbor => {
            if (neighbor.revealed || neighbor.flagged || neighbor.mine) return;
            neighbor.revealed = true;
            pending.push(neighbor);
          });
        }
      }
      if (revealed === cells.length - modes[mode].mines) finish(true);
    }

    function toggleFlag(cell) {
      if (status === 'finished' || cell.revealed) return;
      cell.flagged = !cell.flagged;
      flags += cell.flagged ? 1 : -1;
      cell.node.classList.toggle('is-flagged', cell.flagged);
      cell.node.textContent = cell.flagged ? '⚑' : '';
      cell.node.setAttribute('aria-label', cell.flagged ? `${cell.label}：已插旗` : cell.label);
      updateRemaining();
    }

    function clickedCell(target) {
      const node = target.closest('.mine-cell');
      if (!node || node.parentElement !== grid) return null;
      return cells[Number(node.dataset.row) * modes[mode].size + Number(node.dataset.col)];
    }

    function onClick(event) {
      const control = event.target.closest('button');
      if (control === modeButton) {
        mode = (mode + 1) % modes.length;
        restart();
      } else if (control === restartButton || control === replayButton) {
        restart();
      } else if (control === flagButton) {
        setFlagMode(!flagMode);
      } else {
        const cell = clickedCell(event.target);
        if (!cell) return;
        if (flagMode) toggleFlag(cell);
        else reveal(cell);
      }
    }

    function onContextMenu(event) {
      const cell = clickedCell(event.target);
      if (!cell) return;
      event.preventDefault();
      toggleFlag(cell);
    }

    restart();
    containerEl.appendChild(root);
    root.addEventListener('click', onClick);
    grid.addEventListener('contextmenu', onContextMenu);
    dispose = function () {
      stopTimer();
      root.removeEventListener('click', onClick);
      grid.removeEventListener('contextmenu', onContextMenu);
      root.remove();
    };
  }

  function unmount() {
    if (dispose) {
      dispose();
      dispose = null;
    }
  }

  window.StarloopGames.minesweeper = { mount, unmount };
}());
