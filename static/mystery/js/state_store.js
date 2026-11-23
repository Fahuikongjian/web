(function (window) {
  "use strict";

  function normalizeSecret(value) {
    return String(value ?? "").normalize("NFKC").toLowerCase().replace(/[\s\-_:：—–]+/g, "");
  }

  function open(key, caseId) {
    const collections = ["unlockedGates", "revealedHiddenInks"];
    let entries = Object.fromEntries(collections.map(name => [name, new Set()]));
    let storageAvailable = true;

    function sync() {
      if (!storageAvailable) return;
      try {
        const saved = JSON.parse(window.localStorage.getItem(key));
        entries = Object.fromEntries(collections.map(function (name) {
          const values = saved?.caseId === caseId && Array.isArray(saved[name]) ? saved[name] : [];
          return [name, new Set(values.filter(value => typeof value === "string"))];
        }));
      } catch {
        // Keep the current session playable with unavailable or invalid storage.
      }
    }

    function has(name, id) {
      sync();
      return entries[name].has(id);
    }

    function change(name, id, present) {
      if (!id || has(name, id) === present) return false;
      const list = entries[name];
      if (present) list.add(id);
      else list.delete(id);
      const data = Object.fromEntries(collections.map(key => [key, [...entries[key]]]));
      try {
        if (storageAvailable) window.localStorage.setItem(key, JSON.stringify({ version: 1, caseId, ...data }));
      } catch {
        storageAvailable = false;
      }
      return true;
    }

    return {
      normalizeSecret,
      unlockGate: id => change("unlockedGates", id, true),
      lockGate: id => change("unlockedGates", id, false),
      isGateUnlocked: id => has("unlockedGates", id),
      revealHiddenInk: id => change("revealedHiddenInks", id, true),
      isHiddenInkRevealed: id => has("revealedHiddenInks", id)
    };
  }

  window.MysteryStateStore = { open };
}(window));
