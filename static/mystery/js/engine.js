(function (window) {
  "use strict";

  function escapeHtml(value) {
    const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return String(value ?? "").replace(/[&<>"']/g, char => entities[char]);
  }

  function resolveAssetUrl(path) {
    const prefix = window.document.querySelector('meta[name="site-base-path"]')?.content || "";
    return path?.startsWith("/static/") ? prefix + path : path;
  }

  async function fetchJson(path) {
    const response = await window.fetch(resolveAssetUrl(path));
    if (!response.ok) throw new Error("Failed to load " + path + " (" + response.status + ")");
    return response.json();
  }

  async function loadCase(configUrl) {
    const chapter = await fetchJson(configUrl);
    const manifest = chapter.legacyManifest ? await fetchJson(chapter.legacyManifest) : {};
    const siteData = Object.fromEntries(await Promise.all((manifest.sites || []).map(async site => [
      site.siteKey, await fetchJson(site.dataUrl)
    ])));
    const search = siteData.search || chapter.search;
    chapter.searchUrl = "https://" + search.domain + "/";
    const siteNames = new Map(chapter.sites.map(site => [site.domain, site.title]));
    search.entries = search.entries.concat(chapter.records.filter(record => record.index !== false).map(record => ({
      id: "archive-" + record.id,
      title: record.title,
      url: "https://" + record.site + "/" + record.id,
      domain: record.site,
      date: record.date,
      snippet: record.snippet || record.paragraphs[0],
      keywords: [siteNames.get(record.site), ...(record.keywords || [])],
      requireSiteOperator: record.index === "site"
    })));
    siteData.search = search;
    return { chapter, manifest, siteData };
  }

  function parseRoute(address, currentUrl) {
    const input = String(address ?? "").trim();
    if (!input) return null;
    let url;
    try {
      if (/^[/?#]/.test(input) && !input.startsWith("//")) {
        url = new URL(input, currentUrl);
      } else {
        const absolute = /^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(input);
        url = new URL(absolute ? input.replace(/^\/\//, "https://") : "https://" + input);
      }
    } catch {
      return null;
    }
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.port) return null;
    url.protocol = "https:";
    url.pathname = url.pathname.replace(/\/+$/, "") || "/";
    return {
      rawUrl: url.href,
      domain: url.hostname,
      path: url.pathname,
      segments: url.pathname.split("/").filter(Boolean),
      query: Object.fromEntries(url.searchParams)
    };
  }

  function errorPage(code, title, description) {
    return {
      pageTitle: title,
      html: '<section class="mystery-page-error"><div>' + escapeHtml(code) +
        '</div><h1 class="mystery-page-error-title">' + escapeHtml(title) +
        '</h1><p class="mystery-page-error-desc">' + escapeHtml(description) + "</p></section>"
    };
  }

  function create(data, ui) {
    const { chapter, manifest, siteData } = data;
    const store = window.MysteryStateStore.open(chapter.storageKey, chapter.caseId);
    let route;
    let snapshot = false;
    const context = {
      ...store,
      chapter,
      manifest,
      get isTimeMachine() { return snapshot; },
      resolveAssetUrl,
      navigate: ui.navigate,
      rerender: () => render(route, snapshot, true),
      toggleTimeMachine: ui.toggleSnapshot,
      openSourceViewer: ui.openSourceViewer,
      showToast: ui.showStatus
    };

    function render(nextRoute, nextSnapshot, keepScroll = false) {
      route = nextRoute;
      snapshot = nextSnapshot;
      const renderers = window.MysteryRenderers;
      let page;
      try {
        const legacy = (manifest.sites || []).find(site => site.domain === route.domain);
        if (route.domain === siteData.search.domain) {
          page = renderers.search(route, siteData.search, context);
        } else if (legacy) {
          page = renderers[legacy.siteKey](route, siteData[legacy.siteKey], context);
        } else if (manifest.portal && route.domain === "darun.local" && ["/", "/portal"].includes(route.path)) {
          page = renderers.portal(route, manifest, context);
        } else {
          const archiveSite = chapter.sites.find(site => site.domain === route.domain);
          page = archiveSite ? renderers.archive(route, archiveSite, context) :
            errorPage("404", "该网址没有存入本卷", "请核对网址，或从本卷导航重新查找。");
        }
      } catch (error) {
        window.console.error(error);
        page = errorPage("500", "无法读取此页", "可重新加载此页，或返回本卷导航。");
      }
      ui.onRender(route, page, snapshot, keepScroll);
    }
    return { render, context };
  }

  window.MysteryEngine = { create, loadCase, parseRoute, resolveAssetUrl, escapeHtml, errorPage };
}(window));
