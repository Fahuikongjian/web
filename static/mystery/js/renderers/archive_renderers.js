(function (window) {
  "use strict";

  function escapeHtml(value) {
    return window.MysteryEngine.escapeHtml(value);
  }

  function link(target, label) {
    const url = escapeHtml(target);
    return '<a data-mystery-link="' + url + '" href="' + url + '">' + escapeHtml(label) + "</a>";
  }

  function paragraphs(values = []) {
    return values.map(value => "<p>" + escapeHtml(value) + "</p>").join("");
  }

  function attachments(links = [], heading = "相关页") {
    if (!links.length) return "";
    return "<h2>" + heading + '</h2><ul class="archive-links">' +
      links.map(item => "<li>" + link(item.url, item.label) + "</li>").join("") + "</ul>";
  }

  function table(columns, rows) {
    return '<div class="archive-table-wrap"><table class="archive-table"><thead><tr>' +
      columns.map(text => '<th scope="col">' + escapeHtml(text) + "</th>").join("") +
      "</tr></thead><tbody>" + rows.map(row =>
        "<tr>" + row.map(cell => "<td>" + (typeof cell === "object"
          ? link(cell.url, cell.label) : escapeHtml(cell)) + "</td>").join("") + "</tr>"
      ).join("") + "</tbody></table></div>";
  }

  function recordUrl(record) {
    return "https://" + record.site + "/" + record.id;
  }

  function renderRecord(record, context) {
    const view = context.isTimeMachine && record.snapshot ? record.snapshot : record;
    const html = '<time class="archive-date">' + escapeHtml(view.date || record.date) + "</time>" +
      paragraphs(view.paragraphs) +
      (view.table ? table(view.table.columns, view.table.rows) : "") +
      paragraphs(view.notes) + attachments(view.links);
    return {
      title: view.title || record.title,
      html,
      sourceComment: view.source,
      snapshotMeta: record.snapshot ? {
        supported: true,
        snapshotDate: record.snapshot.date,
        bannerText: "存档日期 " + record.snapshot.date + "　正在查看原版"
      } : null
    };
  }

  function renderIndex(site, context) {
    const records = context.chapter.records.filter(record => record.site === site.domain && record.listed !== false);
    const rows = records.map(record => [{ url: recordUrl(record), label: record.title }, record.date]);
    const directory = (site.links || []).map(item => {
      const linkedSite = context.chapter.sites.find(target => item.url === "https://" + target.domain + "/");
      return [item, linkedSite?.strap || ""];
    });
    let entries = "";
    if (directory.length && site.style === "directory") {
      entries = table(["站点", "收录范围"], directory);
    } else if (records.length && site.style === "community") {
      entries = '<ul class="archive-bulletin">' + records.map(record => "<li>" +
        '<time class="archive-record-note">' + escapeHtml(record.date) + "</time>" +
        link(recordUrl(record), record.title) +
        "<p>" + escapeHtml(record.paragraphs[0].split("。")[0] + "。") + "</p></li>").join("") + "</ul>";
    } else if (rows.length) {
      entries = table(["条目", "存档日期"], rows);
    }
    return {
      title: site.heading || "公开目录",
      html: paragraphs(site.intro) + entries,
      sourceComment: site.source
    };
  }

  function reviewUrl(site, id) {
    return "https://" + site.domain + (id ? "/" + id : "/");
  }

  function isFiled(context, id) {
    return context.isGateUnlocked("filed:" + id);
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

  function reviewForm(work, context, doneHtml) {
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
          context.rerender();
          window.document.querySelector("#archive-document-title")?.focus();
        });
      }
    };
  }

  function renderReview(route, site, context) {
    const { checks, conclusion } = context.chapter;
    const mainUrl = reviewUrl(site);
    const queue = checks.map(work => [
      { url: reviewUrl(site, work.id), label: work.title },
      isFiled(context, work.id) ? "已核对" : "待核对"
    ]);
    if (route.path === "/") {
      return {
        title: site.heading,
        html: paragraphs(site.intro) + table(["待办件", "收件记录"], queue) +
          attachments([{ url: reviewUrl(site, conclusion.id), label: conclusion.title }], "汇总件")
      };
    }
    if (route.path === "/" + conclusion.id) {
      const missing = checks.filter(work => !isFiled(context, work.id));
      if (missing.length) {
        return {
          title: conclusion.title,
          html: "<p>以下分件尚未核对。收齐原件后，汇总件可受理。</p>" +
            attachments(missing.map(work => ({ url: reviewUrl(site, work.id), label: work.title })), "待补材料")
        };
      }
      return reviewForm(conclusion, context,
        '<div class="archive-receipt">' + paragraphs(conclusion.receipt) + "</div>" +
        attachments(conclusion.links, "后续登记"));
    }
    const work = checks.find(item => route.path === "/" + item.id);
    if (!work) return null;
    return reviewForm(work, context,
      '<div class="archive-receipt">' + paragraphs(work.receipt) + "</div>" +
      attachments([{ url: mainUrl, label: "返回收件目录" }], "下一步"));
  }

  function renderArchive(route, site, context) {
    const home = "https://" + site.domain + "/";
    const record = context.chapter.records.find(item => item.site === site.domain && route.path === "/" + item.id);
    let page;
    if (site.kind === "review") page = renderReview(route, site, context);
    else if (record) page = renderRecord(record, context);
    else if (route.path === "/") page = renderIndex(site, context);
    if (!page) return window.MysteryEngine.errorPage("404", "此页未归档", "请从站点首页查询已公开的文件。");
    const navbar = [{ label: "首页", url: home }, ...(site.nav || [])]
      .map(item => link(item.url, item.label)).join("");
    return {
      pageTitle: page.title + " | " + site.title,
      themeClass: "archive-folio",
      sourceComment: page.sourceComment,
      snapshotMeta: page.snapshotMeta,
      onMount: page.onMount,
      html: '<div class="archive-site" data-style="' + escapeHtml(site.style) + '"><div class="archive-frame">' +
        '<header class="archive-mast"><span class="archive-brand">' + link(home, site.title) + "</span>" +
        "<p>" + escapeHtml(site.strap) + '</p></header><nav class="archive-site-nav" aria-label="站点栏目">' + navbar +
        '</nav><article class="archive-document"><div class="archive-crumb">' + link(home, site.title) +
        ' / ' + escapeHtml(page.title) + '</div><h1 id="archive-document-title" tabindex="-1">' + escapeHtml(page.title) +
        "</h1>" + page.html + '</article><footer class="archive-site-footer">' +
        escapeHtml(site.footer || site.title + "　资料仅供查阅") + "</footer></div></div>"
    };
  }

  window.MysteryRenderers = window.MysteryRenderers || {};
  window.MysteryRenderers.archive = renderArchive;
}(window));
