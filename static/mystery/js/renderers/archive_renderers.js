(function (window) {
  "use strict";

  const STYLE_LABELS = {
    directory: "目录导航",
    public: "政务公示",
    community: "民间论坛",
    library: "方志典藏",
    hydro: "水文遥测",
    maritime: "航道海事",
    office: "站务办公",
    registry: "总录密档"
  };

  function escapeHtml(value) {
    return window.MysteryEngine.escapeHtml(value);
  }

  function link(target, label, className = "", isCurrent = false) {
    const url = escapeHtml(target);
    const cls = className ? ' class="' + escapeHtml(className) + '"' : "";
    const cur = isCurrent ? ' aria-current="page"' : "";
    return '<a' + cls + cur + ' data-mystery-link="' + url + '" href="' + url + '">' + escapeHtml(label) + "</a>";
  }

  function paragraphs(values = []) {
    return (values || []).map(value => "<p>" + escapeHtml(value) + "</p>").join("");
  }

  function attachments(links = [], heading = "相关页") {
    if (!links || !links.length) return "";
    return "<h2>" + escapeHtml(heading) + '</h2><ul class="archive-links">' +
      links.map(item => "<li>" + link(item.url, item.label) + "</li>").join("") + "</ul>";
  }

  function table(columns, rows) {
    return '<div class="archive-table-wrap"><table class="archive-table"><thead><tr>' +
      columns.map(text => '<th scope="col">' + escapeHtml(text) + "</th>").join("") +
      "</tr></thead><tbody>" + rows.map(row =>
        "<tr>" + row.map(cell => "<td>" + (cell && typeof cell === "object"
          ? link(cell.url, cell.label) : escapeHtml(cell)) + "</td>").join("") + "</tr>"
      ).join("") + "</tbody></table></div>";
  }

  function recordUrl(record) {
    return "https://" + record.site + "/" + record.id;
  }

  function reviewUrl(site, id) {
    return "https://" + site.domain + (id ? "/" + id : "/");
  }

  function isFiled(context, id) {
    return context.isGateUnlocked("filed:" + id);
  }

  function listedRecordsForSite(site, context) {
    return (context.chapter.records || []).filter(
      item => item.site === site.domain && item.listed !== false
    );
  }

  function navList(items = [], currentUrl = "") {
    if (!items.length) return "";
    return '<ul class="arch-side-list">' + items.map(item => {
      const active = Boolean(currentUrl && item.url === currentUrl);
      return "<li" + (active ? ' class="is-active"' : "") + ">" + link(item.url, item.label, active ? "is-active" : "", active) + "</li>";
    }).join("") + "</ul>";
  }

  function renderBbsFloors(view, record, links) {
    const postDate = view.date || record.date || "";
    const notes = view.notes || [];
    const opFloor =
      '<article class="arch-bbs-floor is-op">' +
        '<div class="arch-bbs-author">' +
          '<div class="arch-bbs-avatar" aria-hidden="true">楼</div>' +
          '<div class="arch-bbs-poster">原帖作者</div>' +
          '<span class="arch-bbs-badge">楼主 · #1F</span>' +
          '<div class="arch-bbs-meta">编号 ' + escapeHtml(record.id) + "</div>" +
        "</div>" +
        '<div class="arch-bbs-body">' +
          '<div class="arch-bbs-floor-head"><time class="archive-date">' + escapeHtml(postDate) + "</time><span>#1F</span></div>" +
          paragraphs(view.paragraphs) +
          (view.table ? table(view.table.columns, view.table.rows) : "") +
        "</div>" +
      "</article>";

    const replyFloors = notes.map((note, idx) =>
      '<article class="arch-bbs-floor is-reply">' +
        '<div class="arch-bbs-author">' +
          '<div class="arch-bbs-avatar" aria-hidden="true">议</div>' +
          '<div class="arch-bbs-poster">跟帖附注</div>' +
          '<span class="arch-bbs-badge">#' + (idx + 2) + "F</span>" +
        "</div>" +
        '<div class="arch-bbs-body">' +
          '<div class="arch-bbs-floor-head"><span>附注楼层</span><span>#' + (idx + 2) + "F</span></div>" +
          "<p>" + escapeHtml(note) + "</p>" +
        "</div>" +
      "</article>"
    ).join("");

    return '<div class="arch-bbs-thread-bar"><span>主题编号：' + escapeHtml(record.id) +
      "</span><span>共 " + (notes.length + 1) + " 楼</span></div>" +
      '<div class="arch-bbs-floors">' + opFloor + replyFloors + "</div>" +
      attachments(links);
  }

  function renderRecord(record, context, site) {
    const view = context.isTimeMachine && record.snapshot ? record.snapshot : record;
    const links = view.links?.filter(item => !item.requiresGate || context.isGateUnlocked(item.requiresGate));
    const style = site?.style || "";
    const dateText = view.date || record.date || "";
    let html = "";

    if (style === "community") {
      html = renderBbsFloors(view, record, links);
    } else if (style === "library") {
      const notesHtml = (view.notes || []).length
        ? '<blockquote class="arch-folio-quote">' + paragraphs(view.notes) + "</blockquote>"
        : "";
      html = '<time class="archive-date">' + escapeHtml(dateText) + "</time>" +
        paragraphs(view.paragraphs) +
        (view.table ? table(view.table.columns, view.table.rows) : "") +
        notesHtml +
        attachments(links);
    } else if (style === "hydro") {
      const logHead = '<div class="arch-hydro-log-head"><span>测站：' + escapeHtml(record.site) +
        "</span><span>档号：" + escapeHtml(record.id) +
        "</span><span>模式：" + (context.isTimeMachine && record.snapshot ? "ARCHIVE_SNAPSHOT" : "DEFAULT_LOG") +
        "</span></div>";
      html = logHead +
        '<time class="archive-date">' + escapeHtml(dateText) + "</time>" +
        paragraphs(view.paragraphs) +
        (view.table ? table(view.table.columns, view.table.rows) : "") +
        paragraphs(view.notes) +
        attachments(links);
    } else {
      html = '<time class="archive-date">' + escapeHtml(dateText) + "</time>" +
        paragraphs(view.paragraphs) +
        (view.table ? table(view.table.columns, view.table.rows) : "") +
        paragraphs(view.notes) +
        attachments(links);
    }

    return {
      title: view.title || record.title,
      html,
      metaId: record.id,
      metaDate: dateText,
      sourceComment: view.source,
      snapshotMeta: record.snapshot ? {
        supported: true,
        snapshotDate: record.snapshot.date,
        bannerText: record.snapshot.bannerText || ("存档日期 " + record.snapshot.date + "　正在查看原版")
      } : null
    };
  }

  function renderDirectoryIndex(site, context, records) {
    const directory = (site.links || []).map(item => {
      const linkedSite = context.chapter.sites.find(target => item.url === "https://" + target.domain + "/");
      return {
        item,
        domain: linkedSite?.domain || item.url.replace(/^https?:\/\/|\/$/g, ""),
        strap: linkedSite?.strap || "",
        tag: STYLE_LABELS[linkedSite?.style] || "收录站点"
      };
    });

    let gridHtml = "";
    let tableHtml = "";
    if (directory.length) {
      gridHtml = '<div class="arch-dir-grid">' + directory.map(entry =>
        '<section class="arch-dir-card">' +
          "<h3>" + link(entry.item.url, entry.item.label) + "</h3>" +
          "<code>" + escapeHtml(entry.domain) + " · " + escapeHtml(entry.tag) + "</code>" +
          (entry.strap ? "<p>" + escapeHtml(entry.strap) + "</p>" : "") +
        "</section>"
      ).join("") + "</div>";
      tableHtml = table(
        ["站点名称", "站群域名", "收录范围"],
        directory.map(entry => [entry.item.label, { url: entry.item.url, label: entry.domain }, entry.strap])
      );
    } else if (records.length) {
      const rows = records.map(record => [{ url: recordUrl(record), label: record.title }, record.date]);
      tableHtml = table(["条目", "存档日期"], rows);
    }

    return {
      title: site.heading || "公开目录",
      html: '<div class="arch-dir-notice">' + paragraphs(site.intro) + "</div>" + gridHtml + tableHtml,
      sourceComment: site.source
    };
  }

  function renderIndex(site, context) {
    const records = listedRecordsForSite(site, context);
    if (site.style === "directory") {
      return renderDirectoryIndex(site, context, records);
    }
    if (site.style === "community") {
      const rows = records.map(record => [
        { url: recordUrl(record), label: record.title },
        site.title || "版面摘录",
        String((record.notes || []).length),
        record.date
      ]);
      const notice = (site.intro || []).length
        ? '<div class="arch-bbs-notice">' + paragraphs(site.intro) + "</div>"
        : "";
      const threadTable = rows.length ? table(["主题", "作者/来源", "附注数", "发表日期"], rows) : "";
      return {
        title: site.heading || "讨论区目录",
        html: notice + threadTable,
        sourceComment: site.source
      };
    }

    const rows = records.map(record => [{ url: recordUrl(record), label: record.title }, record.date]);
    const entries = rows.length ? table(["条目", "存档日期"], rows) : "";
    return {
      title: site.heading || "公开目录",
      html: paragraphs(site.intro) + entries,
      sourceComment: site.source
    };
  }

  function draft(key, values) {
    try {
      if (values === null) window.sessionStorage.removeItem(key);
      else if (values) window.sessionStorage.setItem(key, JSON.stringify(values));
      else return JSON.parse(window.sessionStorage.getItem(key)) || [];
    } catch {
      // Review forms remain usable when session storage is unavailable.
    }
    return [];
  }

  function reviewForm(work, context, doneHtml, afterFiling = context.rerender) {
    if (isFiled(context, work.id)) return { title: work.title, html: doneHtml };
    const form = '<form class="archive-review-form" data-review-form autocomplete="off">' +
      work.fields.map((field, index) => '<label for="record-field-' + index + '">' +
        escapeHtml(field.label) + '<input id="record-field-' + index + '" name="field-' + index +
        '" type="text" required maxlength="120" spellcheck="false"></label>').join("") +
      '<button type="submit">' + escapeHtml(work.submit || "提交核对") + '</button>' +
      '<p class="archive-feedback" data-review-feedback role="status"></p></form>';
    const help = work.hints?.length ? '<details class="archive-help"><summary>查阅说明</summary><ol>' +
      work.hints.map(hint => "<li>" + escapeHtml(hint) + "</li>").join("") + "</ol></details>" : "";
    return {
      title: work.title,
      html: paragraphs(work.intro) + attachments(work.leads, "调阅起点") + form + help,
      onMount(container) {
        const element = container.querySelector("[data-review-form]");
        const feedback = element.querySelector("[data-review-feedback]");
        const inputs = [...element.querySelectorAll("input")];
        const draftKey = context.chapter.storageKey + ":draft:" + work.id;
        const saved = draft(draftKey);
        inputs.forEach((input, index) => { input.value = saved[index] || ""; });
        element.addEventListener("input", event => {
          event.target.removeAttribute("aria-invalid");
          draft(draftKey, inputs.map(input => input.value));
        });
        element.addEventListener("submit", event => {
          event.preventDefault();
          let wrong = 0;
          work.fields.forEach((field, index) => {
            const input = element.elements.namedItem("field-" + index);
            const value = context.normalizeSecret(input.value);
            const valid = value && field.accept.some(answer => context.normalizeSecret(answer) === value);
            input.setAttribute("aria-invalid", String(!valid));
            if (!valid) wrong += 1;
          });
          if (wrong) {
            feedback.textContent = "有 " + wrong + " 项与原件不符，请按字段核对。";
            element.querySelector('[aria-invalid="true"]').focus();
            return;
          }
          const pending = (work.requires || []).filter(requirement => !context.isGateUnlocked(requirement.gate));
          if (pending.length) {
            feedback.textContent = "仍缺原件查阅记录：" + pending.map(item => item.label).join("、") + "。";
            return;
          }
          draft(draftKey, null);
          context.unlockGate("filed:" + work.id);
          afterFiling();
          window.document.querySelector("#archive-document-title")?.focus();
        });
      }
    };
  }

  function renderReviewSteps(route, site, context) {
    const { checks, conclusion } = context.chapter;
    const total = checks.length;
    const filedCount = checks.filter(work => isFiled(context, work.id)).length;
    const allFiled = total > 0 && filedCount === total;
    const conclusionFiled = isFiled(context, conclusion.id);
    const onCheck = checks.some(work => route.path === "/" + work.id);
    const onConclusion = route.path === "/" + conclusion.id;

    const step1Class = (route.path !== "/" || filedCount > 0) ? "is-done" : "is-active";
    const step2Class = allFiled ? "is-done" : (onCheck || filedCount > 0 ? "is-active" : "");
    const step3Class = conclusionFiled ? "is-done" : (onConclusion || allFiled ? "is-active" : "");
    const pct = total ? Math.round((filedCount / total) * 100) : 0;

    return '<div class="arch-hall-steps" role="list" aria-label="核对办理流程">' +
        '<div class="arch-hall-step ' + step1Class + '" role="listitem"><span>1</span>调阅卷宗</div>' +
        '<div class="arch-hall-step ' + step2Class + '" role="listitem"><span>2</span>逐项核对</div>' +
        '<div class="arch-hall-step ' + step3Class + '" role="listitem"><span>3</span>签发回执</div>' +
      "</div>" +
      '<div class="arch-hall-progress">' +
        '<div class="arch-hall-progress-label">已核对 ' + filedCount + " / " + total + " 项分件" +
        (conclusionFiled ? "（汇总回执已签发）" : "") + "</div>" +
        '<div class="arch-hall-meter" aria-hidden="true"><div class="arch-hall-progress-fill" style="width:' + pct + '%"></div></div>' +
      "</div>";
  }

  function renderReview(route, site, context) {
    const { checks, conclusion } = context.chapter;
    const mainUrl = reviewUrl(site);
    const queue = checks.map(work => [
      { url: reviewUrl(site, work.id), label: work.title },
      isFiled(context, work.id) ? "已核对" : "待核对"
    ]);
    const stepsHeader = renderReviewSteps(route, site, context);

    if (route.path === "/") {
      return {
        title: site.heading,
        reviewHeader: stepsHeader,
        html: paragraphs(site.intro) + table(["待办件", "收件记录"], queue) +
          attachments([{ url: reviewUrl(site, conclusion.id), label: conclusion.title }], "汇总件")
      };
    }
    if (route.path === "/" + conclusion.id) {
      const missing = checks.filter(work => !isFiled(context, work.id));
      if (missing.length) {
        return {
          title: conclusion.title,
          reviewHeader: stepsHeader,
          html: "<p>以下分件尚未核对。收齐原件后，汇总件可受理。</p>" +
            attachments(missing.map(work => ({ url: reviewUrl(site, work.id), label: work.title })), "待补材料")
        };
      }
      const conclusionLinks = (conclusion.links || []).filter(
        item => !item.requiresGate || context.isGateUnlocked(item.requiresGate)
      );
      const rendered = reviewForm(conclusion, context,
        '<div class="archive-receipt">' + paragraphs(conclusion.receipt) + "</div>" +
        attachments(conclusionLinks, "后续登记"));
      rendered.reviewHeader = stepsHeader;
      return rendered;
    }
    const curIdx = checks.findIndex(item => route.path === "/" + item.id);
    const work = curIdx >= 0 ? checks[curIdx] : null;
    if (!work) return null;

    const next = checks.find((c, i) => i > curIdx && !isFiled(context, c.id)) ||
      checks.find(c => !isFiled(context, c.id));
    const nextLinks = next
      ? [
          { url: reviewUrl(site, next.id), label: "下一步：继续核对《" + next.title + "》" },
          { url: mainUrl, label: "返回收件目录" }
        ]
      : [
          { url: reviewUrl(site, conclusion.id), label: "下一步：前往汇总件《" + conclusion.title + "》" },
          { url: mainUrl, label: "返回收件目录" }
        ];

    const rendered = reviewForm(work, context,
      '<div class="archive-receipt">' + paragraphs(work.receipt) + "</div>" +
      attachments(nextLinks, "下一步"));
    rendered.reviewHeader = stepsHeader;
    return rendered;
  }

  function buildSidebar(site, context, currentUrl, records) {
    const style = site.style || "";
    const navItems = site.nav || [];
    const homeUrl = "https://" + site.domain + "/";
    const onIndex = currentUrl === homeUrl;
    const recItems = onIndex ? [] : records.map(item => ({ url: recordUrl(item), label: item.title }));

    if (style === "public") {
      return '<aside class="arch-sidebar">' +
        '<section class="arch-side-box"><h2>政务栏目</h2>' + navList(navItems, currentUrl) + "</section>" +
        (recItems.length ? '<section class="arch-side-box"><h2>本栏公示</h2>' + navList(recItems, currentUrl) + "</section>" : "") +
        '<section class="arch-side-box arch-side-meta"><h2>机构信息</h2>' +
          '<p>' + escapeHtml(site.title) + "</p>" +
          (site.strap ? "<p>" + escapeHtml(site.strap) + "</p>" : "") +
          "<p>站点：" + escapeHtml(site.domain) + "</p>" +
        "</section></aside>";
    }
    if (style === "library") {
      const code = currentUrl.replace(/^https?:\/\//, "").replace(/\/$/, "");
      return '<aside class="arch-sidebar arch-biblio-card">' +
        '<section class="arch-side-box"><h2>典藏书目卡</h2>' +
          '<dl class="arch-biblio-dl">' +
            "<dt>索书号</dt><dd>" + escapeHtml(code) + "</dd>" +
            "<dt>卷目归属</dt><dd>" + escapeHtml(site.title) + "</dd>" +
            "<dt>馆藏摘要</dt><dd>" + escapeHtml(site.strap || "地方纸本转录") + "</dd>" +
          "</dl>" +
        "</section>" +
        (recItems.length ? '<section class="arch-side-box"><h2>本馆卷目</h2>' + navList(recItems, currentUrl) + "</section>" : "") +
        (navItems.length ? '<section class="arch-side-box"><h2>馆藏分目</h2>' + navList(navItems, currentUrl) + "</section>" : "") +
        "</aside>";
    }
    if (style === "hydro") {
      return '<aside class="arch-sidebar arch-hydro-tree">' +
        '<section class="arch-side-box"><h2>测站目录树</h2>' +
          (recItems.length ? navList(recItems, currentUrl) : "<p>暂无公开报表</p>") +
        "</section>" +
        (navItems.length ? '<section class="arch-side-box"><h2>关联站网</h2>' + navList(navItems, currentUrl) + "</section>" : "") +
        "</aside>";
    }
    if (style === "maritime") {
      return '<aside class="arch-sidebar arch-maritime-duty">' +
        '<section class="arch-side-box"><h2>海事值守台</h2>' +
          "<p>" + escapeHtml(site.title) + "</p>" +
          (site.strap ? "<p>" + escapeHtml(site.strap) + "</p>" : "") +
          "<p>台号：" + escapeHtml(site.domain) + "</p>" +
        "</section>" +
        (navItems.length ? '<section class="arch-side-box"><h2>航道栏目</h2>' + navList(navItems, currentUrl) + "</section>" : "") +
        (recItems.length ? '<section class="arch-side-box"><h2>在档通告</h2>' + navList(recItems, currentUrl) + "</section>" : "") +
        "</aside>";
    }
    if (style === "office") {
      return '<aside class="arch-sidebar arch-unit-box">' +
        '<section class="arch-side-box"><h2>单位名片</h2>' +
          "<p><strong>" + escapeHtml(site.title) + "</strong></p>" +
          (site.strap ? "<p>" + escapeHtml(site.strap) + "</p>" : "") +
          "<p>内网地址：" + escapeHtml(site.domain) + "</p>" +
        "</section>" +
        (recItems.length ? '<section class="arch-side-box"><h2>站内公文速览</h2>' + navList(recItems, currentUrl) + "</section>" : "") +
        "</aside>";
    }
    if (style === "registry") {
      if (site.kind === "review") {
        const { checks, conclusion } = context.chapter;
        const checkItems = (checks || []).map(work => ({
          url: reviewUrl(site, work.id),
          label: (isFiled(context, work.id) ? "[已核] " : "[待核] ") + work.title
        }));
        checkItems.push({ url: reviewUrl(site, conclusion.id), label: conclusion.title });
        return '<aside class="arch-sidebar arch-vault-rail">' +
          '<section class="arch-side-box"><h2>会勘件清单</h2>' + navList(checkItems, currentUrl) + "</section>" +
          (navItems.length ? '<section class="arch-side-box"><h2>联动档库</h2>' + navList(navItems, currentUrl) + "</section>" : "") +
          "</aside>";
      }
      return '<aside class="arch-sidebar arch-vault-rail">' +
        (recItems.length ? '<section class="arch-side-box"><h2>入柜卷宗</h2>' + navList(recItems, currentUrl) + "</section>" : "") +
        (navItems.length ? '<section class="arch-side-box"><h2>密档分柜</h2>' + navList(navItems, currentUrl) + "</section>" : "") +
        "</aside>";
    }
    return "";
  }

  function docClassFor(site) {
    const style = site.style || "";
    if (style === "public") return "archive-document arch-doc--redhead";
    if (style === "community") return "archive-document arch-doc--bbs";
    if (style === "library") return "archive-document arch-doc--folio";
    if (style === "hydro") return "archive-document arch-doc--hydro";
    if (style === "maritime") return "archive-document arch-doc--dispatch";
    if (style === "office") return site.kind === "review" ? "archive-document arch-doc--hall" : "archive-document arch-doc--unit";
    if (style === "registry") return "archive-document arch-doc--vault";
    return "archive-document";
  }

  function renderArticle(site, page, home) {
    const style = site.style || "";
    const docCls = docClassFor(site);
    const crumb = '<div class="archive-crumb">' + link(home, site.title) + " / " + escapeHtml(page.title) + "</div>";
    const titleEl = '<h1 id="archive-document-title" tabindex="-1">' + escapeHtml(page.title) + "</h1>";
    let prefix = "";
    let suffix = "";

    if (style === "public") {
      const docCode = page.metaId || site.domain;
      const docDate = page.metaDate || "公开目录";
      prefix = '<div class="arch-redhead-banner">' + escapeHtml(site.title) + "</div>" +
        '<div class="arch-redhead-meta"><span>索引号：' + escapeHtml(docCode) +
        "</span><span>日期：" + escapeHtml(docDate) +
        "</span><span>公开方式：主动公开</span></div>";
      suffix = '<footer class="arch-doc-seal-footer"><span class="arch-seal-stamp" aria-hidden="true">归档<br>用印</span>' +
        "<div><div>" + escapeHtml(site.title) + "</div><div>" + escapeHtml(site.strap || "公开文书留存") + "</div></div></footer>";
    } else if (style === "maritime") {
      prefix = '<div class="arch-dispatch-head"><span>航道调度公电 / 通航纪要</span><span>' +
        escapeHtml(site.domain) + "</span></div>";
    } else if (page.reviewHeader) {
      prefix = page.reviewHeader;
    }

    return '<article class="' + docCls + '">' + crumb + prefix + titleEl + page.html + suffix + "</article>";
  }

  function renderLayoutBody(site, context, page, route, home) {
    const style = site.style || "";
    const records = listedRecordsForSite(site, context);
    const articleHtml = renderArticle(site, page, home);
    const sidebarHtml = buildSidebar(site, context, route.rawUrl, records);

    if (style === "public") {
      return '<div class="arch-shell arch-layout--sidebar-left">' + sidebarHtml + articleHtml + "</div>";
    }
    if (style === "library") {
      return '<div class="arch-shell arch-layout--library">' + sidebarHtml + articleHtml + "</div>";
    }
    if (style === "hydro") {
      return '<div class="arch-shell arch-layout--hydro">' + sidebarHtml + articleHtml + "</div>";
    }
    if (style === "maritime" || (style === "office" && site.kind !== "review")) {
      return '<div class="arch-shell arch-layout--sidebar-right">' + articleHtml + sidebarHtml + "</div>";
    }
    if (style === "registry") {
      return '<div class="arch-shell arch-layout--workbench">' + sidebarHtml + articleHtml + "</div>";
    }
    return articleHtml;
  }

  function renderTopUtility(site, context) {
    const style = site.style || "";
    const records = listedRecordsForSite(site, context);
    if (style === "directory") {
      const searchLink = context.chapter.searchUrl
        ? link(context.chapter.searchUrl, "站群检索（site:）")
        : "";
      const totalSites = (site.links || []).length || (context.chapter.sites || []).length;
      return '<div class="arch-dir-util"><span>' + escapeHtml(context.chapter.archiveBrand || "地方旧网镜像") +
        "</span><span>收录站点 " + totalSites + " 处</span>" +
        (searchLink ? "<span>" + searchLink + "</span>" : "") + "</div>";
    }
    if (style === "hydro") {
      return '<div class="arch-hydro-telemetry"><span>测站主机：' + escapeHtml(site.domain) +
        "</span><span>在线归档：" + records.length + " 份</span><span>视图状态：" +
        (context.isTimeMachine ? "极枯水位快照" : "常规水位") + "</span></div>";
    }
    if (style === "registry") {
      const countLabel = site.kind === "review"
        ? ((context.chapter.checks || []).length + " 项会勘分件")
        : (records.length + " 份入柜卷宗");
      return '<div class="arch-vault-bar"><span>密档库区：' + escapeHtml(site.domain) +
        "</span><span>" + escapeHtml(countLabel) + "</span><span>阅览状态：" +
        (context.isTimeMachine ? "历史底本对照" : "原件调阅") + "</span></div>";
    }
    return "";
  }

  function renderArchive(route, site, context) {
    const home = "https://" + site.domain + "/";
    const record = context.chapter.records.find(item => item.site === site.domain && route.path === "/" + item.id);
    let page;
    if (site.kind === "review") page = renderReview(route, site, context);
    else if (site.kind === "entry" && route.path === "/") {
      const entry = context.chapter.entry;
      page = reviewForm(entry, context,
        '<div class="archive-receipt">' + paragraphs(entry.receipt) + "</div>" +
        attachments(entry.links, "可查阅卷册"), () => window.location.reload());
    } else if (record && (!record.requiresGate || context.isGateUnlocked(record.requiresGate))) {
      page = renderRecord(record, context, site);
    } else if (route.path === "/") {
      page = renderIndex(site, context);
    }
    if (!page) return window.MysteryEngine.errorPage("404", "此页未归档", "请从站点首页查询已公开的文件。");

    const navbar = [{ label: "首页", url: home }, ...(site.nav || [])]
      .map(item => link(item.url, item.label, item.url === route.rawUrl ? "is-active" : "", item.url === route.rawUrl)).join("");
    const style = site.style || "directory";
    const utilBar = renderTopUtility(site, context);
    const isDir = style === "directory";
    const mastStats = style === "community"
      ? '<span class="arch-mast-badge">主题 ' + listedRecordsForSite(site, context).length + "</span>"
      : "";
    const mastHtml = '<header class="archive-mast"><div class="archive-mast-row"><div><span class="archive-brand">' +
      link(home, site.title) + "</span><p>" + escapeHtml(site.strap) + "</p></div>" + mastStats + "</div></header>";
    const navHtml = '<nav class="archive-site-nav" aria-label="站点栏目">' + navbar + "</nav>";
    const bodyHtml = renderLayoutBody(site, context, page, route, home);
    const footerHtml = '<footer class="archive-site-footer">' +
      escapeHtml(site.footer || site.title + "　资料仅供查阅") + "</footer>";

    return {
      pageTitle: page.title + " | " + site.title,
      themeClass: "archive-folio",
      sourceComment: page.sourceComment,
      snapshotMeta: page.snapshotMeta,
      onMount: page.onMount,
      html: '<div class="archive-site" data-style="' + escapeHtml(style) + '"><div class="archive-frame">' +
        (isDir ? utilBar + mastHtml + navHtml : mastHtml + utilBar + navHtml) +
        bodyHtml + footerHtml + "</div></div>"
    };
  }

  window.MysteryRenderers = window.MysteryRenderers || {};
  window.MysteryRenderers.archive = renderArchive;
}(window));
