(function (window) {
  "use strict";

  function defaultNormalize(raw) {
    return String(raw == null ? "" : raw).trim().toLowerCase().replace(/[\s\-_:：]+/g, "");
  }

  function search(rawQuery, siteData, context) {
    const raw = String(rawQuery == null ? "" : rawQuery);
    const normalizeSecret = context && typeof context.normalizeSecret === "function"
      ? context.normalizeSecret
      : defaultNormalize;
    const isGateUnlocked = context && typeof context.isGateUnlocked === "function"
      ? context.isGateUnlocked
      : function () { return false; };

    let siteDomain = "";
    const restQuery = raw.replace(/(?:^|\s)site:([a-z0-9.-]+)(?=\s|$)/gi, function (operator, domain) {
      if (!siteDomain) {
        siteDomain = domain.toLowerCase();
      }
      return " ";
    }).trim().replace(/\s+/g, " ");
    const terms = restQuery ? restQuery.toLowerCase().split(" ") : [];
    const data = siteData || {};
    const eggs = Array.isArray(data.easterEggs) ? data.easterEggs : [];
    const entries = Array.isArray(data.entries) ? data.entries : [];
    const normRaw = normalizeSecret(raw);
    const normRest = normalizeSecret(restQuery);
    const candidates = new Set([raw, restQuery].concat(raw.trim().split(/\s+/)).map(normalizeSecret));

    const triggeredEggs = eggs.filter(function (egg) {
      return (egg.triggers || []).some(function (trigger) {
        const secret = normalizeSecret(trigger);
        if (!secret) {
          return false;
        }
        return candidates.has(secret) ||
          (normRaw && normRaw.indexOf(secret) !== -1) ||
          (normRest && normRest.indexOf(secret) !== -1);
      });
    });
    triggeredEggs.forEach(function (egg) {
      if (egg.gateId && context && typeof context.unlockGate === "function") {
        context.unlockGate(egg.gateId);
      }
    });
    const eggIds = new Set(triggeredEggs.map(function (egg) { return egg.resultId; }));
    const pinned = new Map();
    const exactMatches = [];
    const partialMatches = [];

    entries.forEach(function (entry) {
      const domain = String(entry.domain || "").toLowerCase();
      if ((siteDomain && siteDomain !== domain) || (!siteDomain && entry.requireSiteOperator === true)) {
        return;
      }
      if (eggIds.has(entry.id)) {
        pinned.set(entry.id, entry);
        return;
      }
      if (entry.unlockGate && !isGateUnlocked(entry.unlockGate)) {
        return;
      }
      if (siteDomain && !terms.length) {
        exactMatches.push({ entry: entry, score: 10 });
        return;
      }
      if (!terms.length) {
        return;
      }
      const titleLower = String(entry.title || "").toLowerCase();
      const kwLower = [].concat(entry.keywords || [], entry.tags || []).join(" ").toLowerCase();
      const fields = [titleLower, String(entry.snippet || "").toLowerCase(), String(entry.url || "").toLowerCase(), kwLower].join(" ");
      let matchedCount = 0;
      let score = 0;
      terms.forEach(function (term) {
        if (fields.indexOf(term) !== -1) {
          matchedCount += 1;
          score += 2;
          if (titleLower.indexOf(term) !== -1) {
            score += 4;
          }
          if (kwLower.indexOf(term) !== -1) {
            score += 3;
          }
        }
      });
      if (matchedCount === terms.length) {
        exactMatches.push({ entry: entry, score: score });
      } else if (matchedCount > 0) {
        partialMatches.push({ entry: entry, score: score, matchedCount: matchedCount });
      }
    });

    exactMatches.sort(function (a, b) { return b.score - a.score; });
    let matchedList = exactMatches.map(function (item) { return item.entry; });
    if (!matchedList.length && partialMatches.length) {
      partialMatches.sort(function (a, b) {
        if (b.matchedCount !== a.matchedCount) {
          return b.matchedCount - a.matchedCount;
        }
        return b.score - a.score;
      });
      matchedList = partialMatches.map(function (item) { return item.entry; });
    }

    const featured = Array.from(eggIds).filter(function (id) {
      return pinned.has(id);
    }).map(function (id) {
      return pinned.get(id);
    });
    return {
      rawQuery: raw,
      siteDomain: siteDomain,
      restQuery: restQuery,
      triggeredEggs: triggeredEggs,
      matchedEgg: triggeredEggs[0] || null,
      results: featured.concat(matchedList)
    };
  }

  window.MysterySearchEngine = { search: search };
}(window));
