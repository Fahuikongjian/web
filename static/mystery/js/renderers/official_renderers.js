/* ==========================================================================
   MYSTERY ARG ENGINE — 《大闰录 · 卷一：纸傩代身》官方与检索站点渲染器
   Registers: window.MysteryRenderers.search, .institution, .property
   Case: CASE-LXJZ-61 (The Intercalary Chronicle)
   ========================================================================== */
(function (global) {
  "use strict";

  var SEARCH_BASE = "https://search.qiandu.lh";
  var INST_BASE = "https://feiyi.fengning.gov.lh";
  var PROP_BASE = "https://wy.huaianli.lh";
  var DEMOLITION_URL = PROP_BASE + "/notice/building7-demolition";
  var INTERNAL_GATE = "gate-feiyi-internal";
  var PROP_SNAPSHOT_META = {
    supported: true,
    snapshotDate: "2024-10-15",
    bannerText: "当前正在浏览 2024-10-15 槐安里原版公示时光机快照（前站长苏明归档件）"
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escapeRegExp(str) {
    return String(str).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function resolveAsset(context, url) {
    if (!url) {
      return "";
    }
    if (context && typeof context.resolveAssetUrl === "function") {
      return context.resolveAssetUrl(url);
    }
    return url;
  }

  function normalizeSecret(context, raw) {
    if (context && typeof context.normalizeSecret === "function") {
      return context.normalizeSecret(raw);
    }
    return String(raw == null ? "" : raw)
      .trim()
      .toLowerCase()
      .replace(/[\s\-_:：]+/g, "");
  }

  function isGateUnlocked(context, gateId) {
    if (!gateId || !context || typeof context.isGateUnlocked !== "function") {
      return false;
    }
    return Boolean(context.isGateUnlocked(gateId));
  }

  function showToast(context, message, type) {
    if (context && typeof context.showToast === "function") {
      context.showToast(message, type || "info");
    }
  }

  function renderLink(url, label, className, styleAttr) {
    var safeUrl = escapeHtml(url);
    var safeLabel = escapeHtml(label);
    if (!/^https:\/\/[^/\s]+/i.test(String(url || ""))) {
      return safeLabel;
    }
    var cls = className ? ' class="' + escapeHtml(className) + '"' : "";
    var sty = styleAttr ? ' style="' + escapeHtml(styleAttr) + '"' : "";
    return '<a' + cls + sty + ' href="' + safeUrl + '" data-mystery-link="' + safeUrl + '">' + safeLabel + "</a>";
  }

  function renderParagraphs(values, styleAttr) {
    var list = Array.isArray(values) ? values : [values];
    var sty = styleAttr ? ' style="' + escapeHtml(styleAttr) + '"' : "";
    var out = "";
    for (var i = 0; i < list.length; i++) {
      var item = list[i];
      if (!item) {
        continue;
      }
      var chunks = String(item).split(/\n\n+/);
      for (var j = 0; j < chunks.length; j++) {
        if (chunks[j].trim()) {
          out += "<p" + sty + ">" + escapeHtml(chunks[j].trim()) + "</p>";
        }
      }
    }
    return out;
  }

  function renderTable(className, headers, rows) {
    var headHtml = "";
    if (Array.isArray(headers) && headers.length) {
      headHtml = "<thead><tr>" + headers.map(function (h) {
        return '<th scope="col">' + escapeHtml(h) + "</th>";
      }).join("") + "</tr></thead>";
    }
    var bodyHtml = (Array.isArray(rows) ? rows : []).map(function (row) {
      return "<tr>" + (Array.isArray(row) ? row : []).map(function (cell) {
        return "<td>" + escapeHtml(cell) + "</td>";
      }).join("") + "</tr>";
    }).join("");
    return '<table class="' + escapeHtml(className) + '">' + headHtml + "<tbody>" + bodyHtml + "</tbody></table>";
  }

  function getRouteSegments(route) {
    if (route && Array.isArray(route.segments)) {
      return route.segments.filter(Boolean);
    }
    var path = (route && (route.path || route.pathname)) ? String(route.path || route.pathname) : "/";
    return path.split("/").filter(Boolean);
  }

  function getQueryParam(route, key) {
    if (route && route.query) {
      if (typeof route.query.get === "function") {
        var got = route.query.get(key);
        if (got != null) {
          return String(got);
        }
      } else if (route.query[key] != null) {
        return String(route.query[key]);
      }
    }
    if (route && route.rawUrl) {
      var idx = String(route.rawUrl).indexOf("?");
      if (idx >= 0) {
        try {
          var params = new URLSearchParams(String(route.rawUrl).slice(idx + 1));
          var val = params.get(key);
          if (val != null) {
            return val;
          }
        } catch (err) {
          return "";
        }
      }
    }
    return "";
  }

  function highlightText(rawText, terms) {
    var text = String(rawText == null ? "" : rawText);
    if (!terms || !terms.length) {
      return escapeHtml(text);
    }
    var unique = [];
    var seen = Object.create(null);
    for (var i = 0; i < terms.length; i++) {
      var tok = String(terms[i] || "").trim();
      var lower = tok.toLowerCase();
      if (tok && !seen[lower]) {
        seen[lower] = true;
        unique.push(tok);
      }
    }
    if (!unique.length) {
      return escapeHtml(text);
    }
    unique.sort(function (a, b) {
      return b.length - a.length;
    });
    var pattern = unique.map(escapeRegExp).join("|");
    var parts = text.split(new RegExp("(" + pattern + ")", "gi"));
    var html = "";
    for (var j = 0; j < parts.length; j++) {
      if (!parts[j]) {
        continue;
      }
      if (j % 2 === 1) {
        html += '<mark class="site-search-highlight">' + escapeHtml(parts[j]) + "</mark>";
      } else {
        html += escapeHtml(parts[j]);
      }
    }
    return html;
  }

  /* ========================================================================
     1. 千度旧网检索（岁差镜像）: https://search.qiandu.lh
     ======================================================================== */
  var SEARCH_TABS = [
    { key: "all", label: "全部网页" },
    { key: "institution", label: "非遗政务" },
    { key: "property", label: "槐安里物业" },
    { key: "blog", label: "民俗网志" },
    { key: "forum", label: "老黄历BBS" }
  ];

  var DOMAIN_TO_TAB = {
    "feiyi.fengning.gov.lh": "institution",
    "wy.huaianli.lh": "property",
    "blog.shanye.lh": "blog",
    "bbs.huangli.lh": "forum"
  };

  function parseSearchQuery(rawQuery) {
    var raw = String(rawQuery || "").trim();
    var siteDomain = "";
    var rest = raw.replace(/(?:^|\s)site:([a-z0-9.-]+)(?=\s|$)/gi, function (_, host) {
      if (!siteDomain) {
        siteDomain = host.toLowerCase();
      }
      return " ";
    }).replace(/\s+/g, " ").trim();
    var terms = rest ? rest.split(/\s+/).filter(Boolean) : [];
    return { raw: raw, siteDomain: siteDomain, rest: rest, terms: terms };
  }

  function runFallbackSearch(rawQuery, data, context) {
    var parsed = parseSearchQuery(rawQuery);
    var entries = Array.isArray(data.entries) ? data.entries : [];
    var eggs = Array.isArray(data.easterEggs) ? data.easterEggs : [];
    var normRaw = normalizeSecret(context, parsed.raw);
    var normRest = normalizeSecret(context, parsed.rest);
    var matchedEggs = eggs.filter(function (egg) {
      return (egg.triggers || []).some(function (trigger) {
        var token = normalizeSecret(context, trigger);
        return Boolean(token) && (normRaw.indexOf(token) !== -1 || normRest.indexOf(token) !== -1);
      });
    });

    matchedEggs.forEach(function (egg) {
      if (egg.gateId && context && typeof context.unlockGate === "function") {
        context.unlockGate(egg.gateId);
      }
    });

    var eggResultIds = Object.create(null);
    matchedEggs.forEach(function (egg) {
      if (egg.resultId) {
        eggResultIds[egg.resultId] = true;
      }
    });

    var pinned = [];
    var exact = [];
    var partial = [];

    for (var i = 0; i < entries.length; i++) {
      var entry = entries[i];
      var domain = String(entry.domain || "").toLowerCase();
      if (parsed.siteDomain && parsed.siteDomain !== domain) {
        continue;
      }
      if (!parsed.siteDomain && entry.requireSiteOperator === true) {
        continue;
      }
      if (eggResultIds[entry.id]) {
        pinned.push(entry);
        continue;
      }
      if (entry.unlockGate && !isGateUnlocked(context, entry.unlockGate)) {
        continue;
      }
      if (parsed.siteDomain && !parsed.terms.length) {
        exact.push({ entry: entry, score: 10 });
        continue;
      }
      if (!parsed.terms.length) {
        continue;
      }
      var titleLower = String(entry.title || "").toLowerCase();
      var kwLower = [].concat(entry.keywords || [], entry.tags || []).join(" ").toLowerCase();
      var fields = [titleLower, String(entry.snippet || "").toLowerCase(), String(entry.url || "").toLowerCase(), kwLower].join(" ");
      var hits = 0;
      var score = 0;
      for (var k = 0; k < parsed.terms.length; k++) {
        var term = parsed.terms[k].toLowerCase();
        if (fields.indexOf(term) !== -1) {
          hits += 1;
          score += 2;
          if (titleLower.indexOf(term) !== -1) {
            score += 4;
          }
          if (kwLower.indexOf(term) !== -1) {
            score += 3;
          }
        }
      }
      if (hits === parsed.terms.length) {
        exact.push({ entry: entry, score: score });
      } else if (hits > 0) {
        partial.push({ entry: entry, hits: hits, score: score });
      }
    }

    exact.sort(function (a, b) {
      return b.score - a.score;
    });
    var list = exact.map(function (item) {
      return item.entry;
    });
    if (!list.length && partial.length) {
      partial.sort(function (a, b) {
        return (b.hits - a.hits) || (b.score - a.score);
      });
      list = partial.map(function (item) {
        return item.entry;
      });
    }

    return {
      parsed: parsed,
      matchedEgg: matchedEggs[0] || null,
      results: pinned.concat(list)
    };
  }

  function renderSearch(route, siteData, context) {
    var data = siteData || {};
    var ctx = context || {};
    var q = getQueryParam(route, "q").trim();
    var siteName = data.siteName || "千度旧网检索";
    var hotQueries = Array.isArray(data.hotQueries) ? data.hotQueries : [];
    var syntaxTips = Array.isArray(data.syntaxTips) ? data.syntaxTips : [];
    var quickOps = data.quickDomains || ["blog.shanye.lh", "feiyi.fengning.gov.lh"];

    var logoHtml =
      '<a class="site-search-logo" href="' + SEARCH_BASE + '/" data-mystery-link="' + SEARCH_BASE + '/" style="text-decoration:none;">' +
        '千度<span class="site-search-logo-accent">旧网检索</span>' +
      "</a>";

    var formHtml =
      '<form class="site-search-form" data-search-form="true">' +
        '<input class="site-search-input" type="search" name="q" aria-label="检索关键词" value="' + escapeHtml(q) + '" placeholder="输入关键词或站点域名…" autocomplete="off">' +
        '<button class="site-search-submit" type="submit">检索</button>' +
      "</form>";

    var html = "";
    var sourceComment = "<!-- QIANDU_ARCHIVE_SEARCH | supports site:<domain> & intercalary snapshot cache -->";

    if (!q) {
      html =
        '<main class="site-search-home">' +
          logoHtml +
          '<p class="site-search-tagline">' + escapeHtml(data.tagline || "丰宁地方旧网中文索引 · 岁差归档镜像（1998–2024）") + "</p>" +
          formHtml +
          '<div class="site-search-syntax-tips">' +
            "<span>限定站点：</span>" +
            quickOps.map(function (domain) { return "site:" + domain; }).map(function (op) {
              return '<button type="button" class="site-search-chip" data-search-query="' + escapeHtml(op) + '">' + escapeHtml(op) + "</button>";
            }).join("") +
          "</div>" +
          (syntaxTips.length
            ? '<div style="margin-bottom:20px;font-size:12.5px;color:#64748b;line-height:1.7;">' +
                syntaxTips.map(function (tip) {
                  return "<div>• " + escapeHtml(tip) + "</div>";
                }).join("") +
              "</div>"
            : "") +
          '<div class="site-search-hotlist">' +
            '<h2 class="site-search-hotlist-title">常见检索词</h2>' +
            '<div class="site-search-hot-items">' +
              hotQueries.map(function (item) {
                return '<button type="button" class="site-search-hot-item" data-search-query="' + escapeHtml(item) + '">' + escapeHtml(item) + "</button>";
              }).join("") +
            "</div>" +
          "</div>" +
        "</main>";
    } else {
      var parsed = parseSearchQuery(q);
      var ext = global.MysterySearchEngine;
      var searchRes = null;
      if (ext && typeof ext.search === "function") {
        try {
          searchRes = ext.search(q, data, ctx);
        } catch (err) {
          searchRes = null;
        }
      }
      if (!searchRes || !Array.isArray(searchRes.results)) {
        searchRes = runFallbackSearch(q, data, ctx);
      }

      var matchedEgg = searchRes.matchedEgg || (Array.isArray(searchRes.triggeredEggs) ? searchRes.triggeredEggs[0] : null);
      var results = searchRes.results || [];
      var highlightTerms = parsed.terms.slice();
      if (matchedEgg && parsed.rest && highlightTerms.indexOf(parsed.rest) === -1) {
        highlightTerms.push(parsed.rest);
      }

      var eggHtml = "";
      var targetEntry = matchedEgg && results.find(function (item) { return item.id === matchedEgg.resultId; });
      if (targetEntry) {
        eggHtml =
          '<aside class="site-search-easter-egg">' +
            '<div style="font-weight:700;margin-bottom:4px;">⚠ ' + escapeHtml(matchedEgg.bannerTitle || "检测到岁差索引裂隙缓存") + "</div>" +
            renderParagraphs(matchedEgg.bannerNote, "margin:0 0 8px;") +
            '<div>' + renderLink(targetEntry.url, "查阅缓存") + "</div>" +
          "</aside>";
      }

      var tabsHtml = SEARCH_TABS.map(function (tab, idx) {
        return (
          '<button type="button" class="site-search-tab' + (idx === 0 ? " is-active" : "") + '"' +
          ' data-search-tab="' + escapeHtml(tab.key) + '"' +
          ' aria-pressed="' + (idx === 0 ? "true" : "false") + '">' +
          escapeHtml(tab.label) +
          "</button>"
        );
      }).join("");

      var resultsHtml = results.map(function (entry) {
        var category = DOMAIN_TO_TAB[String(entry.domain || "").toLowerCase()] || "";
        var isSpecial = Boolean(entry.isSnapshotOnly || entry.requireSiteOperator);
        var badgeText = entry.badge || (entry.isSnapshotOnly ? "岁差缓存" : "");
        var badgeHtml = badgeText
          ? '<span class="' + (isSpecial ? "site-search-snapshot-badge" : "site-search-locked-badge") + '">' + escapeHtml(badgeText) + "</span>"
          : "";
        return (
          '<article class="site-search-result" data-result-category="' + escapeHtml(category) + '">' +
            '<div class="site-search-result-url">' +
              "<span>" + escapeHtml(entry.url) + "</span>" +
              (entry.date ? "<span>· " + escapeHtml(entry.date) + "</span>" : "") +
              badgeHtml +
            "</div>" +
            '<a class="site-search-result-title" href="' + escapeHtml(entry.url) + '" data-mystery-link="' + escapeHtml(entry.url) + '">' +
              highlightText(entry.title, highlightTerms) +
            "</a>" +
            '<p class="site-search-result-snippet">' + highlightText(entry.snippet, highlightTerms) + "</p>" +
          "</article>"
        );
      }).join("");

      var statsMsg = "找到 " + results.length + " 条地方归档记录";
      if (parsed.siteDomain) {
        statsMsg += "（已启用站内限定：site:" + parsed.siteDomain + "）";
      }

      html =
        '<header class="site-search-header">' +
          logoHtml +
          formHtml +
          '<nav class="site-search-tabs" aria-label="检索分类">' + tabsHtml + "</nav>" +
        "</header>" +
        '<main class="site-search-container">' +
          '<div class="site-search-stats">' + escapeHtml(statsMsg) + "</div>" +
          eggHtml +
          '<div class="site-search-result-list">' + resultsHtml + "</div>" +
          '<div class="site-search-empty" data-search-empty' + (results.length ? " hidden" : "") + ">" +
            '<p style="margin:0 0 10px;font-weight:700;">未找到匹配记录。</p>' +
            '<p style="margin:0 0 10px;">可拆短关键词，或使用 <code>site:域名</code> 限定站点。</p>' +
            '<div class="site-search-hot-items">' +
              hotQueries.map(function (item) {
                return '<button type="button" class="site-search-hot-item" data-search-query="' + escapeHtml(item) + '">' + escapeHtml(item) + "</button>";
              }).join("") +
            "</div>" +
          "</div>" +
        "</main>";

      sourceComment = "<!-- QIANDU_SEARCH_RESULTS | site_filter=" + (parsed.siteDomain || "none") + " | cache_hits=" + (matchedEgg ? "1" : "0") + " -->";
    }

    return {
      html: html,
      pageTitle: q ? (q + " - " + siteName) : siteName,
      themeClass: "site-theme-search",
      sourceComment: sourceComment,
      sourceClueId: null,
      snapshotMeta: null,
      onMount: function (root) {
        if (!root) {
          return;
        }
        var goQuery = function (val) {
          var term = String(val || "").trim();
          if (typeof ctx.navigate !== "function") {
            return;
          }
          if (!term) {
            ctx.navigate(SEARCH_BASE + "/");
          } else {
            ctx.navigate(SEARCH_BASE + "/search?q=" + encodeURIComponent(term));
          }
        };

        var searchForm = root.querySelector('form[data-search-form="true"]');
        if (searchForm) {
          searchForm.addEventListener("submit", function (ev) {
            ev.preventDefault();
            var inp = searchForm.querySelector('input[name="q"]');
            goQuery(inp ? inp.value : "");
          });
        }

        var quickBtns = root.querySelectorAll("[data-search-query]");
        for (var i = 0; i < quickBtns.length; i++) {
          quickBtns[i].addEventListener("click", function (ev) {
            goQuery(ev.currentTarget.getAttribute("data-search-query"));
          });
        }

        var tabBtns = root.querySelectorAll("[data-search-tab]");
        var cards = root.querySelectorAll(".site-search-result");
        var emptyBox = root.querySelector("[data-search-empty]");
        for (var j = 0; j < tabBtns.length; j++) {
          tabBtns[j].addEventListener("click", function (ev) {
            var activeBtn = ev.currentTarget;
            var targetCat = activeBtn.getAttribute("data-search-tab") || "all";
            for (var m = 0; m < tabBtns.length; m++) {
              var isAct = tabBtns[m] === activeBtn;
              tabBtns[m].classList.toggle("is-active", isAct);
              tabBtns[m].setAttribute("aria-pressed", isAct ? "true" : "false");
            }
            var visible = 0;
            for (var c = 0; c < cards.length; c++) {
              var cat = cards[c].getAttribute("data-result-category") || "";
              var hide = targetCat !== "all" && cat !== targetCat;
              cards[c].hidden = hide;
              if (!hide) {
                visible += 1;
              }
            }
            if (emptyBox) {
              emptyBox.hidden = visible > 0;
            }
          });
        }
      }
    };
  }

  /* ========================================================================
     2. 丰宁县非物质文化遗产保护中心: https://feiyi.fengning.gov.lh
     ======================================================================== */
  function renderTroupePhoto(archive, isInternalScan) {
    var count = isInternalScan ? 13 : 12;
    var figures = [];
    for (var i = 0; i < count; i++) {
      var isThirteenth = isInternalScan && i === 12;
      var coat = isThirteenth ? "#382a24" : ["#6d5e4e", "#58514a", "#7c6b56"][i % 3];
      var frameStyle = isThirteenth
        ? "display:inline-flex;flex-direction:column;align-items:center;padding:3px 4px;border:2px dashed #b91c1c;background:rgba(185,28,28,0.14);border-radius:3px;box-shadow:0 0 10px rgba(185,28,28,0.35);"
        : "display:inline-flex;flex-direction:column;align-items:center;padding:3px 2px;";
      var svg =
        '<svg viewBox="0 0 40 56" width="38" height="52" aria-hidden="true">' +
          '<path fill="' + coat + '" d="M4 55V43Q4 34 15 31H25Q36 34 36 43V55Z"/>' +
          '<ellipse cx="20" cy="21" rx="8.5" ry="11.5" fill="' + (isThirteenth ? "#d6b89c" : "#c4a386") + '"/>' +
          '<path fill="#342d27" d="M11 20Q10 6 21 7Q30 7 29 19L24 14L13 17Z"/>' +
          '<path stroke="#43352c" stroke-width="1.2" fill="none" d="M15 21h3m4 0h3"/>' +
          (isThirteenth
            ? '<path stroke="#43352c" stroke-width="1.2" fill="none" d="M16 26.5q4 2.5 8 0"/>' +
              '<circle cx="24.5" cy="24.5" r="1.5" fill="#140d09"/>' +
              '<path d="M15 32l5 5 5-5m-5 5v15" stroke="#d6b89c" stroke-width="1.1" fill="none"/>'
            : '<path stroke="#43352c" stroke-width="1.1" fill="none" d="M16.5 27h7"/>') +
        "</svg>";
      var label = isThirteenth
        ? '<span style="display:inline-block;margin-top:2px;padding:1px 4px;background:#991b1b;color:#fff;font-size:10px;font-weight:700;line-height:1.3;white-space:nowrap;">第13人·周延生</span>'
        : '<span style="font-size:10px;color:#5c4d40;font-family:var(--font-mono, monospace);">#' + (i + 1) + "</span>";
      figures.push('<span class="site-inst-photo-figure' + (isThirteenth ? " is-anomaly" : "") + '" style="' + frameStyle + '">' + svg + label + "</span>");
    }

    var row1 = '<div style="display:flex;justify-content:center;align-items:flex-end;flex-wrap:wrap;gap:6px;margin-bottom:6px;">' + figures.slice(0, 6).join("") + "</div>";
    var row2 = '<div style="display:flex;justify-content:center;align-items:flex-end;flex-wrap:wrap;gap:6px;">' + figures.slice(6).join("") + "</div>";
    var code = archive.archiveCode || archive.code || "FN-FY-1994-13";
    var badgeText = isInternalScan ? "未裁切底片高清扫件（实见 13 人 · 右缘异常）" : "公开裁边缩略件（原册登记 12 人）";

    return (
      '<figure class="site-inst-photo-frame" style="margin:14px 0;">' +
        '<div class="site-inst-photo-canvas">' +
          '<div style="font-family:var(--font-mono, monospace);font-size:11px;color:#5c4d40;margin-bottom:10px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;">' +
            "<span>底片编号：" + escapeHtml(code) + " · 丰宁太平社</span>" +
            '<span style="font-weight:700;color:' + (isInternalScan ? "#991b1b" : "#5c4d40") + ';">' + escapeHtml(badgeText) + "</span>" +
          "</div>" +
          '<div class="site-inst-photo-figures" style="display:block;">' + row1 + row2 + "</div>" +
        "</div>" +
        '<figcaption class="site-inst-photo-caption" style="margin-top:10px;">' + escapeHtml(code) + " · " + escapeHtml(archive.caption || "") + "</figcaption>" +
        (isInternalScan && archive.annotation
          ? '<p class="site-inst-photo-note" style="margin:6px 0 0;color:#991b1b;font-weight:700;">' + escapeHtml(archive.annotation) + "</p>"
          : "") +
      "</figure>"
    );
  }

  function renderInstShell(data, context, activePath, isInternalMode, bodyHtml) {
    var logoSrc = resolveAsset(context, data.logoUrl || "/static/mystery/assets/institution-logo.svg");
    var siteName = data.siteName || "丰宁县非物质文化遗产保护中心";
    var shortName = data.shortName || "丰宁非遗中心";
    var navItems = [
      { path: "/", label: "中心首页" },
      { path: "/notices", label: "通知公示" },
      { path: "/staff", label: "人员名录" },
      { path: "/archives", label: "公开馆藏" },
      { path: "/internal", label: "内部馆藏" }
    ];

    var topbarLeft = isInternalMode
      ? "丰宁非遗馆藏阅览室　只读会话"
      : "丰宁县政务文化信息公开网 · 城东文化街 42 号";
    var topbarRight = isInternalMode
      ? "本地索引：FY-INT · 审计记录开启"
      : ("档案查询电话：" + ((data.overview && data.overview.phone) || "0572-6412089"));

    return (
      '<div class="site-inst-topbar">' +
        "<span>" + escapeHtml(topbarLeft) + "</span>" +
        "<span>" + escapeHtml(topbarRight) + "</span>" +
      "</div>" +
      '<header class="site-inst-header">' +
        '<div class="site-inst-header-inner">' +
          '<div class="site-inst-brand">' +
            (logoSrc ? '<img class="site-inst-crest" src="' + escapeHtml(logoSrc) + '" alt="' + escapeHtml(shortName) + '">' : "") +
            "<div>" +
              '<h1 class="site-inst-org-name">' + escapeHtml(siteName) + "</h1>" +
              '<p class="site-inst-org-sub">FENGNING ICH PROTECTION CENTER · ' + escapeHtml(data.motto || "守护乡邦文脉 · 传承丰宁百戏") + "</p>" +
            "</div>" +
          "</div>" +
          (isInternalMode
            ? '<span class="site-inst-clearance clearance-top">特级馆藏终端 · INTERNAL</span>'
            : renderLink(INST_BASE + "/internal", "内部馆藏登录 →", "", "color:#dfb86b;font-size:12.5px;font-weight:700;text-decoration:none;border:1px solid rgba(223,184,107,0.45);padding:6px 12px;border-radius:4px;")) +
        "</div>" +
      "</header>" +
      '<nav class="site-inst-nav" aria-label="非遗中心导航">' +
        '<div class="site-inst-nav-inner">' +
          navItems.map(function (item) {
            var active = item.path === activePath;
            return renderLink(
              INST_BASE + item.path,
              item.label,
              "site-inst-nav-item" + (active ? " is-active" : ""),
              "text-decoration:none;display:inline-block;"
            );
          }).join("") +
        "</div>" +
      "</nav>" +
      '<main class="site-inst-main">' + bodyHtml + "</main>"
    );
  }

  function renderInstitution(route, siteData, context) {
    var data = siteData || {};
    var ctx = context || {};
    var segments = getRouteSegments(route);
    var section = segments[0] || "";
    var subId = segments[1] || "";
    var isInternalRoute = section === "internal";
    var isLoggedIn = isInternalRoute && isGateUnlocked(ctx, INTERNAL_GATE);
    var themeClass = isLoggedIn ? "site-theme-institution site-theme-institution--internal" : "site-theme-institution";
    var shortName = data.shortName || "丰宁非遗中心";
    var overview = data.overview || {};
    var notices = Array.isArray(data.notices) ? data.notices : [];
    var exhibits = Array.isArray(data.publicExhibits) ? data.publicExhibits : [];
    var staffDir = data.staffDirectory || {};
    var baseComment = overview.sourceComment || "<!-- FENGNING_FEIYI_CMS | internal: /internal | employeeId format: FY-YYYY-NNN -->";

    /* A. 岁差缓存页 /archive/darun-draft-61 */
    if (section === "archive" && subId) {
      var cached = data.cachedArchivePages && data.cachedArchivePages[subId];
      if (cached && isGateUnlocked(ctx, "gate-search-darun")) {
        var cacheHtml =
          '<div class="mystery-snapshot-callout">' +
            "<strong>⚠ 旧索引缓存（原始时间戳：" + escapeHtml(cached.cachedAt || "2019-02-30 00:61") + "）</strong><br>" +
            escapeHtml(cached.deletedNote || "") +
          "</div>" +
          '<section class="site-inst-section">' +
            '<div class="site-inst-doc-redhead">丰宁非遗中心 · 旧站迁移副本</div>' +
            '<h2 class="site-inst-section-title"><span>' + escapeHtml(cached.title) + '</span><span class="site-inst-notice-badge is-urgent">已撤回</span></h2>' +
            '<div style="line-height:1.9;font-size:14.5px;color:#1e293b;">' +
              renderParagraphs(cached.paragraphs, "margin:0 0 13px;") +
            "</div>" +
          "</section>";

        return {
          html: renderInstShell(data, ctx, "/archives", false, cacheHtml),
          pageTitle: cached.title + " - " + shortName,
          themeClass: "site-theme-institution",
          sourceComment: cached.sourceComment || baseComment,
          sourceClueId: null,
          snapshotMeta: null,
        };
      }
    }

    /* B. 通知公示 (/notices, /notices/:id) */
    if (section === "notices") {
      if (subId) {
        var notice = notices.find(function (item) {
          return item.id === subId;
        });
        if (notice) {
          var noticeTableHtml = (Array.isArray(notice.tableRows) && notice.tableRows.length)
            ? '<div class="site-inst-table-wrap" style="margin:16px 0;">' +
                renderTable("site-inst-registry-table", notice.tableHeaders || [], notice.tableRows) +
              "</div>"
            : "";
          var detailHtml =
            '<section class="site-inst-section">' +
              '<div style="margin-bottom:10px;">' + renderLink(INST_BASE + "/notices", "← 返回通知公示目录", "", "font-size:12.5px;color:#1e40af;text-decoration:none;") + "</div>" +
              '<div class="site-inst-doc-redhead">丰宁县非物质文化遗产保护中心文件</div>' +
              '<h2 class="site-inst-section-title"><span>' + escapeHtml(notice.title) + '</span><span class="site-inst-notice-badge' + (notice.isUrgent ? " is-urgent" : "") + '">' + escapeHtml(notice.department || "办公室") + "</span></h2>" +
              '<div style="font-family:var(--font-mono, monospace);font-size:12px;color:#64748b;margin-bottom:14px;">发文日期：' + escapeHtml(notice.date) + " · 承办科室：" + escapeHtml(notice.department || "") + "</div>" +
              '<div style="line-height:1.85;font-size:14px;">' + renderParagraphs(notice.paragraphs || notice.content, "margin:0 0 12px;") + "</div>" +
              noticeTableHtml +
              '<div style="margin-top:16px;padding-top:12px;border-top:1px solid #e2e8f0;display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;">' +
                renderLink(INST_BASE + "/staff", "查阅中心人员名录与工号示例 →", "", "color:#1e40af;") +
                renderLink(INST_BASE + "/internal", "前往内部馆藏档案终端 →", "", "color:#991b1b;") +
              "</div>" +
            "</section>";

          return {
            html: renderInstShell(data, ctx, "/notices", false, detailHtml),
            pageTitle: notice.title + " - " + shortName,
            themeClass: "site-theme-institution",
            sourceComment: notice.sourceComment || baseComment,
            sourceClueId: null,
            snapshotMeta: null,
          };
        }
      }

      var sortedNotices = notices.slice().sort(function (a, b) {
        return String(b.date || "").localeCompare(String(a.date || ""));
      });
      var listHtml =
        '<section class="site-inst-section">' +
          '<div class="site-inst-doc-redhead">通知公示与人事编制栏</div>' +
          '<div class="site-inst-table-wrap">' +
            '<table class="site-inst-registry-table">' +
              "<thead><tr><th>发文日期</th><th>公文标题与摘要</th><th>承办科室</th></tr></thead>" +
              "<tbody>" +
                sortedNotices.map(function (item) {
                  var url = INST_BASE + "/notices/" + encodeURIComponent(item.id);
                  return (
                    "<tr>" +
                      '<td style="white-space:nowrap;font-family:var(--font-mono, monospace);">' + escapeHtml(item.date) + "</td>" +
                      "<td>" +
                        renderLink(url, item.title, "", "color:#0f2036;font-weight:700;text-decoration:none;") +
                        '<div style="font-size:12px;color:#64748b;margin-top:3px;">' + escapeHtml(item.summary || "") + "</div>" +
                      "</td>" +
                      '<td style="white-space:nowrap;"><span class="site-inst-notice-badge' + (item.isUrgent ? " is-urgent" : "") + '">' + escapeHtml(item.department || "") + "</span></td>" +
                    "</tr>"
                  );
                }).join("") +
              "</tbody>" +
            "</table>" +
          "</div>" +
        "</section>";

      return {
        html: renderInstShell(data, ctx, "/notices", false, listHtml),
        pageTitle: "通知公示 - " + shortName,
        themeClass: "site-theme-institution",
        sourceComment: baseComment,
        sourceClueId: null,
        snapshotMeta: null,
        onMount: function () {}
      };
    }

    /* C. 人员名录 (/staff) */
    if (section === "staff") {
      var members = Array.isArray(staffDir.members) ? staffDir.members : [];
      var staffHtml =
        '<section class="site-inst-section">' +
          '<div class="site-inst-doc-redhead">中心人员名录与工号编制规范</div>' +
          '<div class="mystery-snapshot-callout" style="margin-top:0;">' +
            "<strong>统一工号编制说明：</strong>" + escapeHtml(staffDir.idRuleNote || "FY-入职年份(4位)-系统三位序号") +
            '<div style="margin-top:6px;">' + renderLink(INST_BASE + "/notices/2018-archive-recruit", "查阅《2018 年度非遗数字化归档专员录用及工号编制公示》 →", "", "color:#92400e;font-weight:700;") + "</div>" +
          "</div>" +
          '<div class="site-inst-staff-grid" style="margin-bottom:18px;">' +
            members.map(function (m) {
              return (
                '<div class="site-inst-staff-card">' +
                  '<div class="site-inst-staff-header">' +
                    '<span class="site-inst-staff-name">' + escapeHtml(m.name) + "</span>" +
                    '<span class="site-inst-staff-id">' + escapeHtml(m.employeeId) + "</span>" +
                  "</div>" +
                  '<div class="site-inst-staff-role">' + escapeHtml(m.title) + "</div>" +
                  '<div class="site-inst-staff-meta">' +
                    "<div>科室：" + escapeHtml(m.department) + "</div>" +
                    "<div>状态：" + escapeHtml(m.status) + "</div>" +
                    '<div style="margin-top:4px;color:#334155;">' + escapeHtml(m.note) + "</div>" +
                  "</div>" +
                "</div>"
              );
            }).join("") +
          "</div>" +
          '<div class="site-inst-table-wrap">' +
            renderTable(
              "site-inst-registry-table",
              ["工号", "姓名", "职务", "所属科室", "在册状态"],
              members.map(function (m) {
                return [m.employeeId, m.name, m.title, m.department, m.status];
              })
            ) +
          "</div>" +
        "</section>";

      return {
        html: renderInstShell(data, ctx, "/staff", false, staffHtml),
        pageTitle: "人员名录 - " + shortName,
        themeClass: "site-theme-institution",
        sourceComment: baseComment,
        sourceClueId: null,
        snapshotMeta: null,
        onMount: function () {}
      };
    }

    /* D. 公开馆藏 (/archives) */
    if (section === "archives") {
      var exhibitsHtml = exhibits.map(function (item) {
        return (
          '<section class="site-inst-section">' +
            '<h2 class="site-inst-section-title"><span>' + escapeHtml(item.title) + '</span><span class="site-inst-notice-badge">' + escapeHtml(item.code) + "</span></h2>" +
            (item.code === "FN-FY-1994-13" ? renderTroupePhoto(item, false) : "") +
            '<div style="line-height:1.85;font-size:14px;color:#334155;">' + renderParagraphs(item.description, "margin:0 0 10px;") + "</div>" +
            (item.code === "FN-FY-1994-13"
              ? '<div style="margin-top:10px;font-size:12.5px;color:#64748b;">未裁切底片高清原件已移入特级封存库，' +
                  renderLink(INST_BASE + "/internal", "持有效馆员工号可登录内部馆藏系统调阅 →", "", "color:#991b1b;font-weight:700;") +
                "</div>"
              : "") +
          "</section>"
        );
      }).join("");

      return {
        html: renderInstShell(data, ctx, "/archives", false, exhibitsHtml),
        pageTitle: "公开馆藏 - " + shortName,
        themeClass: "site-theme-institution",
        sourceComment: baseComment,
        sourceClueId: null,
        snapshotMeta: null,
        onMount: function () {}
      };
    }

    /* E. 内部馆藏终端 (/internal & /internal/:docId) */
    if (section === "internal") {
      var gate = data.internalGate || {};
      var gateId = gate.gateId || INTERNAL_GATE;

      if (!isLoggedIn) {
        var loginHtml =
          '<section class="site-inst-section">' +
            '<div class="site-inst-doc-redhead">丰宁非遗特级馆藏内部档案终端 · 身份核验</div>' +
            '<h2 class="site-inst-section-title"><span>' + escapeHtml(gate.systemTitle || "丰宁非遗特级馆藏内部档案终端") + '</span><span class="site-inst-notice-badge is-urgent">限馆内授权访问</span></h2>' +
            '<p style="font-size:13.5px;color:#475569;margin:0 0 16px;line-height:1.7;">' + escapeHtml(gate.loginHint || "请输入本中心职工工号（FY-YYYY-NNN）与个人馆藏口令。") + "</p>" +
            '<div class="site-inst-login-panel">' +
              '<form class="mystery-gate-form" data-inst-login="true">' +
                '<div class="mystery-gate-field" style="margin-bottom:12px;">' +
                  '<label class="mystery-gate-label" for="feiyi-emp-id" style="display:block;font-size:12.5px;font-weight:700;margin-bottom:4px;color:#1e293b;">职工工号（Employee ID）</label>' +
                  '<input id="feiyi-emp-id" class="mystery-gate-input" name="employeeId" type="text" placeholder="格式：FY-YYYY-NNN" autocomplete="username" style="width:100%;height:36px;padding:0 10px;border:1px solid #94a3b8;border-radius:4px;background:#fff;color:#0f172a;">' +
                "</div>" +
                '<div class="mystery-gate-field" style="margin-bottom:12px;">' +
                  '<label class="mystery-gate-label" for="feiyi-emp-pwd" style="display:block;font-size:12.5px;font-weight:700;margin-bottom:4px;color:#1e293b;">个人馆藏口令（Passcode）</label>' +
                  '<input id="feiyi-emp-pwd" class="mystery-gate-input" name="password" type="password" placeholder="请输入个人馆藏口令" autocomplete="current-password" style="width:100%;height:36px;padding:0 10px;border:1px solid #94a3b8;border-radius:4px;background:#fff;color:#0f172a;">' +
                "</div>" +
                '<div class="mystery-gate-error" data-login-error="true" role="alert" style="display:none;color:#b91c1c;background:#fee2e2;border:1px solid #fca5a5;padding:8px 10px;border-radius:4px;font-size:12.5px;margin-bottom:12px;"></div>' +
                '<button class="mystery-gate-submit" type="submit" style="height:36px;padding:0 18px;border:none;border-radius:4px;background:#991b1b;color:#fff;font-size:13px;font-weight:700;cursor:pointer;">核验工号并进入特级库房</button>' +
              "</form>" +
            "</div>" +
            '<div style="margin-top:16px;font-size:12.5px;color:#64748b;display:flex;gap:14px;flex-wrap:wrap;">' +
              renderLink(INST_BASE + "/staff", "查询中心工号编制规则 →", "", "color:#1e40af;") +
              renderLink(INST_BASE + "/notices/2018-archive-recruit", "查看 2018 年度归档专员录用公示 →", "", "color:#1e40af;") +
            "</div>" +
          "</section>";

        return {
          html: renderInstShell(data, ctx, "/internal", false, loginHtml),
          pageTitle: "内部馆藏登录 - " + shortName,
          themeClass: "site-theme-institution",
          sourceComment: "<!-- FEIYI_INTERNAL_GATE | format: FY-YYYY-NNN | unrevoked read-only account active -->",
          sourceClueId: null,
          snapshotMeta: null,
          onMount: function (root) {
            if (!root) {
              return;
            }
            var form = root.querySelector('form[data-inst-login="true"]');
            var errEl = root.querySelector('[data-login-error="true"]');
            if (!form) {
              return;
            }
            form.addEventListener("submit", function (ev) {
              ev.preventDefault();
              var empInput = form.querySelector('input[name="employeeId"]');
              var pwdInput = form.querySelector('input[name="password"]');
              var normEmp = normalizeSecret(ctx, empInput ? empInput.value : "");
              var normPwd = normalizeSecret(ctx, pwdInput ? pwdInput.value : "");
              var validIds = Array.isArray(gate.acceptedEmployeeIds) ? gate.acceptedEmployeeIds : ["FY-2018-061"];
              var validPwds = Array.isArray(gate.acceptedPasswords) ? gate.acceptedPasswords : ["cyq081561"];
              var empOk = validIds.some(function (id) {
                return normalizeSecret(ctx, id) === normEmp;
              });
              var pwdOk = validPwds.some(function (pw) {
                return normalizeSecret(ctx, pw) === normPwd;
              });

              if (empOk && pwdOk) {
                if (typeof ctx.unlockGate === "function") {
                  ctx.unlockGate(gateId);
                }
                showToast(ctx, "核验通过：已进入丰宁非遗特级馆藏终端（陈砚青 · 只读权限）", "success");
                if (typeof ctx.rerender === "function") {
                  ctx.rerender();
                }
              } else {
                var errMsg = "身份核验未通过：";
                if (!empOk && !pwdOk) {
                  errMsg += "工号与馆藏口令均不匹配，请核对 2018 录用公示序号与老黄历茶馆线索。";
                } else if (!empOk) {
                  errMsg += "未找到该职工工号，请按 FY-入职年份(4位)-系统三位序号 核对。";
                } else {
                  errMsg += "工号有效，但馆藏口令错误（请核对陈砚青在茶馆 610 帖时光机 5F 留下的口令规则与 618 帖生日）。";
                }
                if (errEl) {
                  errEl.textContent = errMsg;
                  errEl.style.display = "block";
                }
                showToast(ctx, "馆藏登录口令核验失败", "error");
              }
            });
          }
        };
      }

      /* 已登录态：暗玄朱砂内部馆藏终端 */
      var acct = gate.loggedInAccount || {
        employeeId: "FY-2018-061",
        name: "陈砚青",
        role: "前数字归档专员（只读馆藏权限 · 未注销）",
        clearance: "特级只读 · LEVEL-61"
      };
      var docs = Array.isArray(data.internalDocs) ? data.internalDocs : [];

      var sessionBarHtml =
        '<div class="site-inst-seal-strip">' +
          "<span>馆藏阅览室 · 丰宁非遗特级底片与名录档</span>" +
          "<span>归档组：FN-FY</span>" +
        "</div>" +
        '<div class="site-inst-internal-bar">' +
          '<div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px;">' +
            '<span class="site-inst-clearance clearance-confidential">' + escapeHtml(acct.clearance || "特级只读") + "</span>" +
            "<span>当前调阅人：<strong>" + escapeHtml(acct.name) + "</strong>（" + escapeHtml(acct.employeeId) + "）· " + escapeHtml(acct.role) + "</span>" +
          "</div>" +
          '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">' +
            (subId ? renderLink(INST_BASE + "/internal", "← 返回特级馆藏目录", "", "color:#dfb86b;text-decoration:none;font-size:12px;padding:5px 10px;border:1px solid rgba(223,184,107,0.45);border-radius:4px;") : "") +
            '<button class="site-inst-logout-btn" type="button" data-action="inst-logout">退出馆藏终端</button>' +
          "</div>" +
        "</div>";

      var bindLogout = function (root) {

        if (!root) {
          return;
        }
        var btn = root.querySelector('[data-action="inst-logout"]');
        if (btn) {
          btn.addEventListener("click", function () {
            if (typeof ctx.lockGate === "function") {
              ctx.lockGate(gateId);
              showToast(ctx, "已退出丰宁非遗内部馆藏会话", "info");
              if (typeof ctx.rerender === "function") {
                ctx.rerender();
              }
            } else {
              showToast(ctx, "已返回丰宁非遗公开官网", "info");
              if (typeof ctx.navigate === "function") {
                ctx.navigate(INST_BASE + "/");
              }
            }
          });
        }
      };

      if (subId) {
        var doc = docs.find(function (item) {
          return item.id === subId;
        });
        if (doc) {
          var docHtml =
            sessionBarHtml +
            '<article class="site-inst-dossier">' +
              '<div class="site-inst-dossier-head">' +
                "<div>" +
                  '<div style="margin-bottom:8px;"><span class="site-inst-clearance ' + escapeHtml(doc.clearanceClass || "clearance-top") + '">' + escapeHtml(doc.classification || "特级封存") + "</span></div>" +
                  '<h2 class="site-inst-dossier-title">' + escapeHtml(doc.title) + "</h2>" +
                "</div>" +
                '<span class="archive-wordmark archive-wordmark--seal" aria-hidden="true">馆藏<br>归档</span>' +
              "</div>" +
              '<div class="site-inst-dossier-meta">' +
                "<span>卷宗编号：" + escapeHtml(doc.code) + "</span>" +
                "<span>归档日期：" + escapeHtml(doc.date) + "</span>" +
                "<span>整理人：" + escapeHtml(doc.author) + "</span>" +
              "</div>" +
              (doc.photoArchive ? renderTroupePhoto(doc.photoArchive, true) : "") +
              '<div class="site-inst-dossier-body">' +
                (Array.isArray(doc.sections) ? doc.sections : []).map(function (sec) {
                  return (
                    '<div style="margin-bottom:18px;">' +
                      '<h3 style="margin:0 0 8px;font-size:14.5px;color:#dfb86b;">' + escapeHtml(sec.heading) + "</h3>" +
                      renderParagraphs(sec.body, "margin:0 0 10px;") +
                    "</div>"
                  );
                }).join("") +
              "</div>" +
            "</article>";

          return {
            html: renderInstShell(data, ctx, "/internal", true, docHtml),
            pageTitle: doc.title + " - 特级馆藏",
            themeClass: themeClass,
            sourceComment: doc.sourceComment || ("<!-- FEIYI_INTERNAL_DOC: " + doc.code + " -->"),
            sourceClueId: null,
            snapshotMeta: null,
            onMount: bindLogout
          };
        }
      }

      var internalListHtml =
        sessionBarHtml +
        '<section class="site-inst-section">' +
          '<h2 class="site-inst-section-title"><span>特级馆藏卷宗目录</span></h2>' +
          '<div class="site-inst-dossier-list">' +
            docs.map(function (item) {
              var docUrl = INST_BASE + "/internal/" + encodeURIComponent(item.id);
              return (
                '<article class="site-inst-dossier">' +
                  '<div class="site-inst-dossier-head">' +
                    "<div>" +
                      '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;">' +
                        '<span class="site-inst-clearance ' + escapeHtml(item.clearanceClass || "clearance-top") + '">' + escapeHtml(item.classification || "特级封存") + "</span>" +
                      "</div>" +
                      '<h3 class="site-inst-dossier-title">' + escapeHtml(item.title) + "</h3>" +
                    "</div>" +
                    renderLink(docUrl, "调阅完整卷宗 →", "", "padding:7px 14px;border-radius:4px;background:#dfb86b;color:#14120d;font-size:12.5px;font-weight:700;text-decoration:none;white-space:nowrap;") +
                  "</div>" +
                  '<div class="site-inst-dossier-meta">' +
                    "<span>卷宗编号：" + escapeHtml(item.code) + "</span>" +
                    "<span>日期：" + escapeHtml(item.date) + "</span>" +
                    "<span>整理人：" + escapeHtml(item.author) + "</span>" +
                  "</div>" +
                "</article>"
              );
            }).join("") +
          "</div>" +
        "</section>";

      return {
        html: renderInstShell(data, ctx, "/internal", true, internalListHtml),
        pageTitle: "特级馆藏目录 - " + shortName,
        themeClass: themeClass,
        sourceComment: "<!-- FEIYI_INTERNAL_PORTAL | SESSION: FY-2018-061 | KEY_ORDER: XING+ZHAI+MING+SHI -->",
        sourceClueId: null,
        snapshotMeta: null,
        onMount: bindLogout
      };
    }

    /* F. 非遗中心首页 (/) */
    var featuredExhibit = exhibits.find(function (item) {
      return item.code === "FN-FY-1994-13";
    }) || exhibits[0];
    var homeNotices = notices.slice().sort(function (a, b) {
      return String(b.date || "").localeCompare(String(a.date || ""));
    });

    var homeHtml =
      '<section class="site-inst-section">' +
        '<div class="site-inst-doc-redhead">丰宁县非物质文化遗产保护中心 · 公开政务平台</div>' +
        '<div style="line-height:1.85;font-size:14px;color:#334155;">' + renderParagraphs(overview.intro, "margin:0 0 12px;") + "</div>" +
        '<div style="display:flex;flex-wrap:wrap;gap:14px;font-family:var(--font-mono, monospace);font-size:12px;color:#475569;padding-top:10px;border-top:1px dashed #cbd5e1;">' +
          "<span>建馆时间：" + escapeHtml(overview.established || "1989年") + "</span>" +
          "<span>馆址：" + escapeHtml(overview.address || "丰宁县城东文化街 42 号") + "</span>" +
        "</div>" +
      "</section>" +
      '<section class="site-inst-section">' +
        '<h2 class="site-inst-section-title"><span>最新公文与人事公示</span>' + renderLink(INST_BASE + "/notices", "全部公示 →", "", "font-size:12.5px;color:#1e40af;text-decoration:none;") + "</h2>" +
        '<div class="site-inst-table-wrap">' +
          '<table class="site-inst-registry-table">' +
            "<thead><tr><th>日期</th><th>公告标题</th><th>科室</th></tr></thead>" +
            "<tbody>" +
              homeNotices.map(function (n) {
                var url = INST_BASE + "/notices/" + encodeURIComponent(n.id);
                return (
                  "<tr>" +
                    '<td style="white-space:nowrap;font-family:var(--font-mono, monospace);">' + escapeHtml(n.date) + "</td>" +
                    "<td>" + renderLink(url, n.title, "", "color:#0f2036;font-weight:700;text-decoration:none;") + "</td>" +
                    '<td style="white-space:nowrap;"><span class="site-inst-notice-badge' + (n.isUrgent ? " is-urgent" : "") + '">' + escapeHtml(n.department || "") + "</span></td>" +
                  "</tr>"
                );
              }).join("") +
            "</tbody>" +
          "</table>" +
        "</div>" +
      "</section>" +
      (featuredExhibit
        ? '<section class="site-inst-section">' +
            '<h2 class="site-inst-section-title"><span>重点馆藏缩略件</span>' + renderLink(INST_BASE + "/archives", "查看全部馆藏 →", "", "font-size:12.5px;color:#1e40af;text-decoration:none;") + "</h2>" +
            '<h3 style="margin:0 0 8px;font-size:15px;color:#0f2036;">' + escapeHtml(featuredExhibit.title) + "</h3>" +
            renderTroupePhoto(featuredExhibit, false) +
            '<div style="line-height:1.8;font-size:13.5px;color:#475569;">' + renderParagraphs(featuredExhibit.description, "margin:0;") + "</div>" +
          "</section>"
        : "");

    return {
      html: renderInstShell(data, ctx, "/", false, homeHtml),
      pageTitle: (data.siteName || "丰宁县非物质文化遗产保护中心") + " - 官网",
      themeClass: "site-theme-institution",
      sourceComment: baseComment,
      sourceClueId: null,
      snapshotMeta: null,
      onMount: function () {}
    };
  }

  /* ========================================================================
     3. 槐安里小区物业与拆迁公示网: https://wy.huaianli.lh
     ======================================================================== */
  function renderProperty(route, siteData, context) {
    var data = siteData || {};
    var ctx = context || {};
    var segments = getRouteSegments(route);
    var section = segments[0] || "";
    var subId = segments[1] || "";
    var siteName = data.siteName || "槐安里小区物业与拆迁公示网";
    var notices = Array.isArray(data.notices) ? data.notices : [];
    var demolition = notices.find(function (item) {
      return item.id === "building7-demolition";
    }) || notices[0];

    var navItems = [
      { path: "/", label: "小区首页" },
      { path: "/notice/building7-demolition", label: "7号楼拆迁公示" },
      { path: "/surveyor", label: "测绘员协查" },
      { path: "/floorplan", label: "7号楼层平面" }
    ];
    var activeNav = section === "notice" ? "/notice/building7-demolition" : (section ? ("/" + section) : "/");

    var title = siteName;
    var content = "";
    var sourceComment = "<!-- HUAIANLI_PROPERTY_PORTAL | BUILDING_07_REDEVELOPMENT -->";
    var snapshotMeta = null;
    var onMount = function (root) {

    };

    if (!section) {
      var bld = data.buildingOverview || {};
      content =
        '<section>' +
          '<h2 style="margin:0 0 10px;font-size:16px;color:#7f1d1d;border-bottom:1px solid #d6ccba;padding-bottom:6px;">7 号楼基础台账</h2>' +
          '<div class="site-prop-table-wrap" style="margin-bottom:12px;">' +
            renderTable(
              "site-prop-table",
              ["楼栋号", "竣工年份", "房产登记楼层"],
              [[bld.buildingNo || "7 号楼", bld.builtYear || "1994年", bld.officialFloors || "地上 13 层"]]
            ) +
          "</div>" +
          '<div style="font-size:13.5px;line-height:1.8;color:#44403c;">' + renderParagraphs(bld.architectNote, "margin:0;") + "</div>" +
        "</section>" +
        '<section>' +
          '<h2 style="margin:0 0 10px;font-size:16px;color:#7f1d1d;border-bottom:1px solid #d6ccba;padding-bottom:6px;">物业与拆迁公示栏</h2>' +
          '<div class="site-prop-table-wrap">' +
            '<table class="site-prop-table">' +
              "<thead><tr><th>公示文号</th><th>公示标题</th><th>原始发布日期</th></tr></thead>" +
              "<tbody>" +
                notices.map(function (n) {
                  var url = PROP_BASE + "/notice/" + encodeURIComponent(n.id);
                  return (
                    "<tr>" +
                      '<td style="white-space:nowrap;font-family:var(--font-mono, monospace);">' + escapeHtml(n.docCode || "") + "</td>" +
                      "<td>" +
                        renderLink(url, n.title, "", "color:#991b1b;font-weight:700;text-decoration:none;") +
                        (n.hasSnapshotDiff ? ' <span class="site-prop-surveyor-badge" style="margin-left:6px;">含 2024-10-15 时光机原版</span>' : "") +
                      "</td>" +
                      '<td style="white-space:nowrap;font-family:var(--font-mono, monospace);">' + escapeHtml(n.publishedDate || "") + "</td>" +
                    "</tr>"
                  );
                }).join("") +
              "</tbody>" +
            "</table>" +
          "</div>" +
        "</section>";
    } else if (section === "notice") {
      var notice = notices.find(function (item) {
        return item.id === subId;
      }) || demolition;
      title = notice ? notice.title : "公示未找到";

      if (notice) {
        var cur = notice.currentVersion || {};
        var snap = notice.snapshotVersion || null;
        var hasDiff = Boolean(notice.hasSnapshotDiff && snap);
        sourceComment = notice.sourceComment || sourceComment;
        if (hasDiff) {
          snapshotMeta = PROP_SNAPSHOT_META;
        }

        var docBar =
          '<div style="font-family:var(--font-mono, monospace);font-size:12px;color:#57534e;padding-bottom:10px;border-bottom:1px dashed #c9bfa9;">' +
            "公示文号：" + escapeHtml(notice.docCode || "") +
            " ｜ 原始发布：" + escapeHtml(notice.publishedDate || "") +
            " ｜ 签发：" + escapeHtml((hasDiff && ctx.isTimeMachine) ? "前站长苏明（原始版）" : (cur.issuer || "槐安里物业")) +
          "</div>";

        if (hasDiff && ctx.isTimeMachine) {
          var anomaly = snap.anomalyCard || {};
          var surveyor = snap.surveyorCard || {};
          var diffBlocks = Array.isArray(snap.diffBlocks) ? snap.diffBlocks : [];

          content =
            docBar +
            '<div class="mystery-snapshot-callout" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin:0;">' +
              "<div><strong>⏱ 已还原 2024-10-15 原始公示快照 · </strong>" + escapeHtml(snap.timestamp || "") + "</div>" +
              '<button type="button" data-prop-wayback-exit="true" style="padding:5px 12px;border-radius:3px;border:1px solid #92400e;background:transparent;color:#78350f;font-size:12px;font-weight:700;cursor:pointer;">切回 10-16 覆写版</button>' +
            "</div>" +
            '<h2 style="margin:0;font-size:20px;color:#7f1d1d;">' + escapeHtml(snap.headline || "") + "</h2>" +
            '<section class="site-prop-anomaly">' +
              '<div style="font-weight:800;font-size:14.5px;margin-bottom:6px;">⚠ 图外幽灵夹层异常登记：' + escapeHtml(anomaly.roomCode || "404B") + " 室</div>" +
              '<div style="font-family:var(--font-mono, monospace);font-size:12px;margin-bottom:6px;">位置：' + escapeHtml(anomaly.location || "") + "</div>" +
              renderParagraphs(anomaly.details, "margin:0;") +
            "</section>" +
            '<section class="site-prop-surveyor-card">' +
              '<div class="site-prop-surveyor-head">' +
                '<span class="site-prop-surveyor-name">失联测绘员协查卡：' + escapeHtml(surveyor.name || "周延生") + "</span>" +
                '<span class="site-prop-surveyor-badge">证件日期异常 · 跨界同脸</span>' +
              "</div>" +
              '<div class="site-prop-surveyor-meta">' +
                "职务：" + escapeHtml(surveyor.role || "") +
                " ｜ 身份证签发日：<strong style=\"color:#991b1b;\">" + escapeHtml(surveyor.idIssueDate || "1994-02-30") + "</strong>" +
              "</div>" +
              '<div class="site-prop-surveyor-note">' +
                renderParagraphs([surveyor.features, surveyor.lastSeen], "margin:0 0 8px;") +
              "</div>" +
            "</section>" +
            '<section class="mystery-snapshot-diff" style="margin-top:0;">' +
              '<div class="mystery-diff-header">' +
                '<h3 class="mystery-diff-title">7 号楼公示版本对照</h3>' +
                '<div class="mystery-diff-legend">' +
                  '<span class="mystery-diff-del">10 月 15 日存档</span>' +
                  '<span class="mystery-diff-ins">10 月 16 日存档</span>' +
                "</div>" +
              "</div>" +
              diffBlocks.map(function (blk) {
                return (
                  '<div class="mystery-diff-grid" style="margin-bottom:12px;">' +
                    '<div class="mystery-diff-col mystery-diff-col--before">' +
                      '<span class="mystery-diff-label">' + escapeHtml(blk.label || "篡改项") + " · 2024-10-15 原版</span>" +
                      '<div><span class="mystery-diff-del">' + escapeHtml(blk.beforeText || "") + "</span></div>" +
                    "</div>" +
                    '<div class="mystery-diff-col mystery-diff-col--after">' +
                      '<span class="mystery-diff-label">' + escapeHtml(blk.label || "篡改项") + " · 2024-10-16 覆写版</span>" +
                      '<div><span class="mystery-diff-ins">' + escapeHtml(blk.afterText || "") + "</span></div>" +
                    "</div>" +
                  "</div>"
                );
              }).join("") +
            "</section>";

          onMount = function (root) {

            var exitBtn = root && root.querySelector('[data-prop-wayback-exit="true"]');
            if (exitBtn) {
              exitBtn.addEventListener("click", function () {
                if (typeof ctx.toggleTimeMachine === "function") {
                  ctx.toggleTimeMachine(false);
                }
              });
            }
          };
        } else {
          content =
            docBar +
            '<h2 style="margin:0;font-size:19px;color:#1c1917;">' + escapeHtml(cur.headline || "") + "</h2>" +
            '<div style="font-size:12px;color:#78716c;">版本时间：' + escapeHtml(cur.timestamp || "") + "</div>" +
            '<div style="font-size:14.5px;line-height:1.9;color:#292524;">' + renderParagraphs(cur.paragraphs, "margin:0 0 12px;") + "</div>" +
            (cur.editorNote
              ? '<div class="mystery-snapshot-callout" style="margin:0;">' +
                  "<div>" + escapeHtml(cur.editorNote) + "</div>" +
                  (hasDiff
                    ? '<div style="margin-top:10px;">' +
                        '<button type="button" data-prop-wayback="true" class="archive-version-link">查阅 10 月 15 日存档</button>' +
                      "</div>"
                    : "") +
                "</div>"
              : "");

          onMount = function (root) {

            var btn = root && root.querySelector('[data-prop-wayback="true"]');
            if (btn) {
              btn.addEventListener("click", function () {
                if (typeof ctx.toggleTimeMachine === "function") {
                  ctx.toggleTimeMachine(true);
                }
              });
            }
          };
        }
      }
    } else if (section === "surveyor") {
      title = "测绘人员值班登记与协查抄件";
      content =
        '<div class="site-prop-surveyor-card">' +
          '<div class="site-prop-surveyor-head">' +
            '<span class="site-prop-surveyor-name">物业值班簿抄件：外派测绘员周延生</span>' +
            '<span class="site-prop-surveyor-badge">离场签字栏空白</span>' +
          "</div>" +
          '<div class="site-prop-surveyor-note">' + renderParagraphs(data.surveyorMissingNote, "margin:0;") + "</div>" +
        "</div>" +
        '<div>' + renderLink(DEMOLITION_URL, "前往查看 7 号楼拆迁复核公示（建议开启时光机对比） →", "", "color:#991b1b;font-weight:700;") + "</div>";
    } else if (section === "floorplan") {
      title = "7 号楼标准楼层与门牌对照表";
      var fp = data.floorplanData || {};
      var floors = Array.isArray(fp.standardFloors) ? fp.standardFloors : [];
      var units = fp.unitsPerFloor || 4;
      var gap = fp.hiddenGap || null;
      var showGap = Boolean(ctx.isTimeMachine && gap);
      snapshotMeta = PROP_SNAPSHOT_META;

      var rowsHtml = "";
      for (var f = 0; f < floors.length; f++) {
        var fl = floors[f];
        rowsHtml +=
          "<tr>" +
            '<td style="font-family:var(--font-mono, monospace);font-weight:700;">第 ' + escapeHtml(fl) + " 层</td>" +
            "<td>" + escapeHtml(fl) + "01、" + escapeHtml(fl) + "02、" + escapeHtml(fl) + "03、" + escapeHtml(fl) + "04（一梯" + escapeHtml(units) + "户）</td>" +
            "<td>标准住宅层</td>" +
          "</tr>";
        if (gap && Array.isArray(gap.betweenFloors) && fl === gap.betweenFloors[0]) {
          if (showGap) {
            rowsHtml +=
              '<tr class="site-prop-anomaly">' +
                '<td style="font-family:var(--font-mono, monospace);font-weight:800;color:#991b1b;">4F / 5F 夹层</td>' +
                '<td><strong>' + escapeHtml(gap.roomCode) + " 室（图外幽灵夹层 · " + escapeHtml(gap.areaSquareMeters) + "㎡）</strong></td>" +
                "<td>" + escapeHtml(gap.note) + "</td>" +
              "</tr>";
          } else {
            rowsHtml +=
              "<tr>" +
                '<td style="color:#78716c;font-family:var(--font-mono, monospace);">4F / 5F 转角</td>' +
                '<td style="color:#78716c;">无窗青砖封堵墙（竣工图未标室号）</td>' +
                '<td style="color:#78716c;">可在历史版本查阅复核附记</td>' +
              "</tr>";
          }
        }
      }

      content =
        '<div class="site-prop-table-wrap">' +
          '<table class="site-prop-table">' +
            "<thead><tr><th>楼层</th><th>登记门牌</th><th>测绘备注</th></tr></thead>" +
            "<tbody>" + rowsHtml + "</tbody>" +
          "</table>" +
        "</div>" +
        '<div>' + renderLink(DEMOLITION_URL, "返回 7 号楼拆迁复核公示 →", "", "color:#991b1b;font-weight:700;") + "</div>";
    } else {
      title = "页面未找到";
      content = renderParagraphs("未检索到该物业公示页。") + renderLink(PROP_BASE + "/", "返回槐安里物业首页", "", "color:#991b1b;font-weight:700;");
    }

    var pageHtml =
      '<div class="site-prop-wrapper">' +
        '<header class="site-prop-header">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;">' +
            "<div>" +
              '<div class="site-prop-redhead">丰宁县槐安里小区物业公示栏</div>' +
              '<div class="site-prop-title">' + escapeHtml(siteName) + "</div>" +
              '<div class="site-prop-sub">' + escapeHtml(data.communityName || "丰宁县槐安里社区") + "</div>" +
            "</div>" +
            '<span class="archive-wordmark archive-wordmark--seal" aria-hidden="true">槐安<br>物业</span>' +
          "</div>" +
        "</header>" +
        '<nav class="site-prop-nav" aria-label="物业站导航">' +
          navItems.map(function (item) {
            return renderLink(
              PROP_BASE + item.path,
              item.label,
              "site-prop-nav-item" + (item.path === activeNav ? " is-active" : ""),
              "text-decoration:none;display:inline-block;"
            );
          }).join("") +
        "</nav>" +
        '<main class="site-prop-main">' +
          (data.bannerNotice ? '<div class="site-prop-warn-strip">' + escapeHtml(data.bannerNotice) + "</div>" : "") +
          '<h1 style="margin:0;font-size:20px;color:#1c1917;">' + escapeHtml(title) + "</h1>" +
          content +
        "</main>" +
      "</div>";

    return {
      html: pageHtml,
      pageTitle: title + " - " + siteName,
      themeClass: "site-theme-property",
      sourceComment: sourceComment,
      sourceClueId: null,
      snapshotMeta: snapshotMeta,
      onMount: onMount
    };
  }

  /* ========================================================================
     Register ONLY Official & Search Slice: search / institution / property
     ======================================================================== */
  global.MysteryRenderers = global.MysteryRenderers || {};
  global.MysteryRenderers.search = renderSearch;
  global.MysteryRenderers.institution = renderInstitution;
  global.MysteryRenderers.property = renderProperty;
})(window);
