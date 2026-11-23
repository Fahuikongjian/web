(function (window, document) {
  "use strict";

  const root = document.querySelector("[data-mystery-app]");
  if (!root) return;
  const api = window.MysteryEngine;
  const viewport = root.querySelector("[data-viewport]");
  const address = root.querySelector("#archive-address");
  const snapshotButton = root.querySelector("[data-snapshot]");
  const sourceDialog = root.querySelector("[data-source-dialog]");
  const status = root.querySelector("[data-reader-status]");
  let route;
  let page;

  function localUrl(target, snapshot = false) {
    const url = new URL(window.location.pathname, window.location.origin);
    url.searchParams.set("page", target);
    if (snapshot) url.searchParams.set("version", "archive");
    return url.pathname + url.search;
  }

  function showStatus(message) {
    status.textContent = message;
    status.hidden = !message;
  }

  function openSourceViewer() {
    if (!page) return;
    const title = api.escapeHtml(page.pageTitle);
    const comment = page.sourceComment ? "\n    " + page.sourceComment : "";
    const markup = page.html.replace(/></g, ">\n<");
    sourceDialog.querySelector("[data-source-text]").textContent =
      '<!doctype html>\n<html lang="zh-CN">\n<head>\n' +
      '  <link rel="canonical" href="' + api.escapeHtml(route.rawUrl) + '">\n' +
      "  <title>" + title + "</title>\n</head>\n<body>" + comment + "\n" +
      markup + "\n</body>\n</html>";
    sourceDialog.showModal();
  }

  function connect(data) {
    const engine = api.create(data, {
      navigate,
      toggleSnapshot: function (force) {
        if (page?.snapshotMeta?.supported) show(route, force ?? !engine.context.isTimeMachine);
      },
      openSourceViewer,
      showStatus,
      onRender
    });
    const home = root.querySelector("[data-local-home]");
    const search = root.querySelector("[data-local-search]");
    home.href = localUrl(data.chapter.homeUrl);
    home.dataset.mysteryLink = data.chapter.homeUrl;
    search.hidden = !data.chapter.searchUrl;
    if (data.chapter.searchUrl) {
      search.href = localUrl(data.chapter.searchUrl);
      search.dataset.mysteryLink = data.chapter.searchUrl;
    }

    function show(next, snapshot) {
      const url = localUrl(next.rawUrl, snapshot);
      if (url !== window.location.pathname + window.location.search) {
        window.history.pushState(null, "", url);
      }
      showStatus("");
      engine.render(next, snapshot);
    }

    function navigate(target) {
      const next = api.parseRoute(target, route?.rawUrl);
      if (!next) {
        showStatus("请输入存档网址或域名。");
        return false;
      }
      show(next, false);
      viewport.focus({ preventScroll: true });
      return true;
    }

    function restore() {
      const params = new URLSearchParams(window.location.search);
      const next = api.parseRoute(params.get("page")) || api.parseRoute(data.chapter.homeUrl);
      showStatus("");
      engine.render(next, params.get("version") === "archive");
    }

    function onRender(next, rendered, snapshot, keepScroll) {
      route = next;
      page = rendered;
      address.value = route.rawUrl;
      document.title = page.pageTitle + " · 旧网拾遗";
      snapshotButton.hidden = !page.snapshotMeta?.supported;
      snapshotButton.setAttribute("aria-pressed", String(snapshot));
      snapshotButton.textContent = snapshot ? "返回现行版" : "历史版本";
      if (!keepScroll || snapshot) {
        showStatus(snapshot && page.snapshotMeta?.supported
          ? (page.snapshotMeta.bannerText || "存档日期 " + page.snapshotMeta.snapshotDate)
          : "");
      }

      const content = document.createElement("div");
      content.className = rendered.themeClass || "";
      content.innerHTML = rendered.html;
      for (const anchor of content.querySelectorAll("a[data-mystery-link]")) {
        const target = api.parseRoute(anchor.dataset.mysteryLink, route.rawUrl);
        if (target) anchor.href = localUrl(target.rawUrl);
        anchor.removeAttribute("target");
      }
      viewport.replaceChildren(content);
      rendered.onMount?.(content);
      if (!keepScroll) window.scrollTo(0, 0);
    }

    root.querySelector("[data-address-form]").addEventListener("submit", event => {
      event.preventDefault();
      navigate(address.value);
    });
    root.addEventListener("click", event => {
      const anchor = event.target.closest("a[data-mystery-link]");
      if (!anchor || event.defaultPrevented || event.button || event.metaKey ||
          event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      navigate(anchor.dataset.mysteryLink);
    });
    snapshotButton.addEventListener("click", () => engine.context.toggleTimeMachine());
    root.querySelector("[data-source]").addEventListener("click", openSourceViewer);
    window.addEventListener("popstate", restore);
    restore();
  }

  api.loadCase(root.dataset.archiveConfig).then(connect).catch(error => {
    window.console.error(error);
    viewport.innerHTML = api.errorPage("503", "存档暂时无法读取", "刷新页面可重新连接本地备份。").html;
  });
}(window, document));
