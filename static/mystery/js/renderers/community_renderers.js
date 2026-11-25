(function () {
  "use strict";

  var BLOG_HOME = "https://blog.shanye.lh/";
  var FORUM_HOME = "https://bbs.huangli.lh/";
  var verdictDraft = Object.create(null);

  function escapeHtml(value) {
    if (value === null || value === undefined) {
      return "";
    }
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
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
    return String(raw || "")
      .trim()
      .toLowerCase()
      .replace(/[\s\-_:：]+/g, "");
  }

  function isGateUnlocked(context, gateId) {
    if (!gateId) {
      return true;
    }
    if (context && typeof context.isGateUnlocked === "function") {
      return Boolean(context.isGateUnlocked(gateId));
    }
    return false;
  }

  function isHiddenInkRevealed(context, inkId) {
    if (!inkId) {
      return false;
    }
    if (context && typeof context.isHiddenInkRevealed === "function") {
      return Boolean(context.isHiddenInkRevealed(inkId));
    }
    return false;
  }

  function manifestFor(siteData, context) {
    if (context && context.manifest) {
      return context.manifest;
    }
    if (siteData && siteData.manifest) {
      return siteData.manifest;
    }
    return siteData || {};
  }

  function renderParagraphs(paragraphs) {
    if (!Array.isArray(paragraphs)) {
      return "";
    }
    return paragraphs
      .filter(function (p) {
        return typeof p === "string" && p.trim().length > 0;
      })
      .map(function (p) {
        return "<p>" + escapeHtml(p) + "</p>";
      })
      .join("");
  }

  function renderMultiline(text) {
    if (!text) {
      return "";
    }
    return String(text)
      .split(/\r?\n/)
      .filter(function (line) {
        return line.trim().length > 0;
      })
      .map(function (line) {
        return '<p style="margin:0 0 8px;">' + escapeHtml(line) + "</p>";
      })
      .join("");
  }

  function renderPortal(route, siteData, context) {
    var manifest = manifestFor(siteData, context);
    var data = manifest.portal || {};
    var cards = Array.isArray(data.directoryCards) ? data.directoryCards : [];
    var footer = data.icpFooter || {};

    var cardsHtml = cards
      .map(function (card) {
        var target = escapeHtml(card.url || "");
        return (
          '<a class="site-portal-card" href="' +
          target +
          '" data-mystery-link="' +
          target +
          '" style="text-decoration:none;color:inherit;">' +
          '<div class="site-portal-card-head">' +
          '<span class="site-portal-card-name">' +
          escapeHtml(card.title || "") +
          "</span>" +
          '<span class="site-portal-card-tag">' +
          escapeHtml(card.category || "归档站") +
          "</span>" +
          "</div>" +
          '<div class="site-portal-card-domain">' +
          escapeHtml(card.domain || "") +
          "</div>" +
          '<p class="site-portal-card-desc">' +
          escapeHtml(card.description || "") +
          "</p>" +
          "</a>"
        );
      })
      .join("");

    var quickLinksHtml = cards
      .map(function (card) {
        var target = escapeHtml(card.url || "");
        return (
          '<a href="' +
          target +
          '" data-mystery-link="' +
          target +
          '" style="color:#1e40af;text-decoration:none;">' +
          escapeHtml(card.title || "") +
          "</a>"
        );
      })
      .join("");

    var html =
      '<div class="site-portal-wrapper">' +
      '<header class="site-portal-header">' +
      '<div style="display:flex;align-items:center;gap:12px;">' +
      '<span class="archive-wordmark" aria-hidden="true">丰宁<br>旧网</span>' +
      "<div>" +
      '<h1 class="site-portal-title">' +
      escapeHtml(data.title || "旧网拾遗 · 丰宁地方网页归档导航") +
      "</h1>" +
      '<p class="site-portal-subtitle">' +
      escapeHtml(data.subtitle || "") +
      "</p>" +
      "</div>" +
      "</div>" +
      '<div style="font-family:var(--font-mono,monospace);font-size:11.5px;color:#475569;">' +
      "镜像范围：1998–2024" +
      "</div>" +
      "</header>" +
      '<div class="site-portal-notice">' +
      escapeHtml(data.notice || "") +
      (data.noticeLink ? ' <a href="' + escapeHtml(data.noticeLink) + '" data-mystery-link="' +
        escapeHtml(data.noticeLink) + '">查看复核收件</a>' : "") +
      "</div>" +
      '<section class="site-portal-section">' +
      '<h2 class="site-portal-section-title">丰宁地方旧网收录目录（共 ' +
      cards.length +
      " 处静态镜像）</h2>" +
      '<div class="site-portal-grid">' +
      cardsHtml +
      "</div>" +
      "</section>" +
      '<div class="site-portal-links-box">' +
      "<strong>快速友情链接：</strong>" +
      quickLinksHtml +
      '<button type="button" class="site-forum-back-link" data-portal-open-source="true" style="margin-left:auto;">检视本页源码</button>' +
      "</div>" +
      '<footer class="site-portal-footer">' +
      "<div>" +
      escapeHtml(footer.maintainer || "归档维护：丰宁地方旧网互助组") +
      "</div>" +
      '<div style="margin:6px 0;display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:10px;">' +
      "<span>备案登记：</span>" +
      '<span class="site-portal-icp">' + escapeHtml(footer.icpCode || "") + "</span></div>" +
      "</footer>" +
      "</div>";

    return {
      html: html,
      pageTitle: data.title || "旧网拾遗 · 丰宁地方网页归档导航",
      themeClass: "site-theme-portal",
      sourceComment: data.sourceComment || "",
      sourceClueId: null,
      snapshotMeta: {
        supported: false
      },
      onMount: function (containerEl) {
        if (!containerEl) {
          return;
        }
        var srcBtn = containerEl.querySelector("[data-portal-open-source]");
        if (srcBtn) {
          srcBtn.addEventListener("click", function () {
            if (context && typeof context.openSourceViewer === "function") {
              context.openSourceViewer();
            }
          });
        }
      }
    };
  }

  /* ========================================================================
   * 2. BLOG RENDERER (blog.shanye.lh)
   * ======================================================================== */
  function renderBlog(route, siteData, context) {
    var data = siteData || {};
    var profile = data.profile || {};
    var posts = Array.isArray(data.posts) ? data.posts : [];
    var publicPosts = posts.filter(function (post) {
      return !post.isUnlisted;
    });
    var tags = Array.isArray(data.tags) ? data.tags : [];
    var segments = route && Array.isArray(route.segments) ? route.segments : [];
    var query = route && route.query ? route.query : {};
    var activeTag = typeof query.tag === "string" ? query.tag.trim() : "";

    var isDetail = segments.length >= 2 && segments[0] === "post";
    var detailSlug = isDetail ? segments[1] : "";
    var currentPost = isDetail
      ? posts.find(function (post) {
          return (post.slug || post.id) === detailSlug;
        })
      : null;

    var avatarSrc = resolveAsset(
      context,
      profile.avatarUrl || "/static/mystery/assets/blog-avatar.svg"
    );

    var navHtml = [
      {
        label: "手记首页",
        url: BLOG_HOME,
        active: !isDetail && !activeTag
      },
      {
        label: "太平社老戏台",
        url: BLOG_HOME + "post/taiping-stage",
        active: detailSlug === "taiping-stage"
      },
      {
        label: "寒露记",
        url: BLOG_HOME + "post/temple-smoke",
        active: detailSlug === "temple-smoke"
      },
      {
        label: "加密日志 · 404B",
        url: BLOG_HOME + "post/locked-404b",
        active: detailSlug === "locked-404b"
      }
    ]
      .map(function (item) {
        return (
          '<a class="site-blog-nav-link' +
          (item.active ? " is-active" : "") +
          '" href="' +
          escapeHtml(item.url) +
          '" data-mystery-link="' +
          escapeHtml(item.url) +
          '" style="text-decoration:none;">' +
          escapeHtml(item.label) +
          "</a>"
        );
      })
      .join("");

    var tagsHtml =
      '<a class="site-blog-tag' +
      (!activeTag && !isDetail ? " is-active" : "") +
      '" href="' +
      BLOG_HOME +
      '" data-mystery-link="' +
      BLOG_HOME +
      '" style="text-decoration:none;">全部</a>' +
      tags
        .map(function (tag) {
          var tagUrl = BLOG_HOME + "?tag=" + encodeURIComponent(tag);
          return (
            '<a class="site-blog-tag' +
            (activeTag === tag ? " is-active" : "") +
            '" href="' +
            escapeHtml(tagUrl) +
            '" data-mystery-link="' +
            escapeHtml(tagUrl) +
            '" style="text-decoration:none;">#' +
            escapeHtml(tag) +
            "</a>"
          );
        })
        .join("");

    var archiveListHtml = publicPosts
      .map(function (post) {
        var slug = post.slug || post.id;
        var postUrl = BLOG_HOME + "post/" + encodeURIComponent(slug);
        var lockPrefix = post.isLocked
          ? isGateUnlocked(context, post.gateId)
            ? "[已解锁] "
            : "[加密] "
          : "";
        return (
          '<li class="site-blog-archive-item">' +
          '<a href="' +
          escapeHtml(postUrl) +
          '" data-mystery-link="' +
          escapeHtml(postUrl) +
          '" style="color:inherit;text-decoration:none;">' +
          escapeHtml(lockPrefix + post.title) +
          "</a>" +
          '<div style="font-size:11px;color:#938170;">' +
          escapeHtml(post.date || "") +
          "</div>" +
          "</li>"
        );
      })
      .join("");

    var sidebarHtml =
      '<aside class="site-blog-sidebar">' +
      '<section class="site-blog-widget site-blog-profile">' +
      '<h3 class="site-blog-widget-title">摄影师名片</h3>' +
      '<img class="site-blog-avatar" src="' +
      escapeHtml(avatarSrc) +
      '" alt="' +
      escapeHtml(profile.author || "林野") +
      '" />' +
      '<div class="site-blog-author">' +
      escapeHtml(profile.author || "林野") +
      ' <span style="font-size:12px;color:#8a7665;">(@' +
      escapeHtml(profile.handle || "shanye_lens") +
      ")</span></div>" +
      '<div class="site-blog-bio">' +
      escapeHtml(profile.bio || "") +
      "</div>" +
      '<div class="site-blog-stats">' +
      "<div>驻留地：" +
      escapeHtml(profile.location || "") +
      "</div>" +
      "<div>最后更新：" +
      escapeHtml(profile.lastUpdated || "") +
      "</div>" +
      (profile.visitCount
        ? "<div>访客记录：" + escapeHtml(profile.visitCount) + "</div>"
        : "") +
      "</div>" +
      "</section>" +
      '<section class="site-blog-widget">' +
      '<h3 class="site-blog-widget-title">胶片归档注</h3>' +
      '<div class="site-blog-bio" style="margin-bottom:8px;">' +
      escapeHtml(profile.archiveNotice || "") +
      "</div>" +
      '<a href="https://search.qiandu.lh/" data-mystery-link="https://search.qiandu.lh/" style="font-size:12px;color:#c0564b;font-family:var(--font-sans,sans-serif);">前往千度旧网检索尝试 site: 语法 →</a>' +
      "</section>" +
      '<section class="site-blog-widget">' +
      '<h3 class="site-blog-widget-title">手记标签</h3>' +
      '<div class="site-blog-tags">' +
      tagsHtml +
      "</div>" +
      "</section>" +
      '<section class="site-blog-widget">' +
      '<h3 class="site-blog-widget-title">公开手记目录</h3>' +
      '<ul class="site-blog-archive-list">' +
      archiveListHtml +
      "</ul>" +
      "</section>" +
      "</aside>";

    var mainHtml = "";
    var pageTitle = data.blogTitle || "山野拾影 · 民俗摄影手记";
    var sourceComment =
      "<!-- BLOG_ARCHIVE: blog.shanye.lh | AUTHOR: shanye_lens | LAST_SYNC: 2024-11-12 -->";
    var sourceClueId = null;

    if (isDetail) {
      if (!currentPost) {
        pageTitle = "手记未找到 - " + (data.blogTitle || "山野拾影");
        mainHtml =
          '<article class="site-blog-post">' +
          '<div class="site-blog-post-header">' +
          '<h2 class="site-blog-post-title">未找到该篇手记</h2>' +
          "</div>" +
          '<div class="site-blog-post-body">' +
          "<p>请求的日志路径不存在，或已在旧站镜像迁移中失效。</p>" +
          '<p><a href="' +
          BLOG_HOME +
          '" data-mystery-link="' +
          BLOG_HOME +
          '" style="color:#c0564b;">← 返回手记首页</a></p>' +
          "</div>" +
          "</article>";
      } else {
        pageTitle = currentPost.title + " - " + (data.blogTitle || "山野拾影");
        if (currentPost.sourceComment) {
          sourceComment = currentPost.sourceComment;
        }
        if (currentPost.sourceClueId) {
          sourceClueId = currentPost.sourceClueId;
        }

        var lockedNow =
          Boolean(currentPost.isLocked) &&
          !isGateUnlocked(context, currentPost.gateId);

        var unlistedNoticeHtml = currentPost.isUnlisted
          ? '<div class="mystery-snapshot-callout" style="margin-top:0;">' +
            "本篇未列于主页公开目录，经地方旧网缓存索引收录。" +
            "</div>"
          : "";

        var postMetaHtml =
          '<div class="site-blog-post-meta">' +
          "<span>发布于 " +
          escapeHtml(currentPost.date || "") +
          "</span>" +
          "<span>作者：" +
          escapeHtml(profile.author || "林野") +
          "</span>" +
          "<span>标签：" +
          escapeHtml((currentPost.tags || []).join(" / ")) +
          "</span>" +
          "</div>";

        var bodySectionHtml = "";
        if (lockedNow) {
          bodySectionHtml =
            '<div class="site-blog-lock-box">' +
            '<div style="margin-bottom:6px;">此日志设有访问口令</div>' +
            '<p style="margin:0 0 12px;font-size:13.5px;line-height:1.7;">' +
            escapeHtml(currentPost.passwordHint || "请输入访问口令解锁阅读。") +
            "</p>" +
            '<form class="mystery-gate-card-form" data-blog-lock-form="true">' +
            '<input type="text" class="mystery-gate-input" data-blog-lock-input="true" aria-label="加密日志口令" placeholder="输入八位口令" autocomplete="off" style="background:#fffcf6;color:#3a271c;border:1px solid #cbb89f;height:36px;padding:0 10px;border-radius:4px;flex:1 1 200px;" />' +
            '<button type="submit" class="mystery-gate-submit" style="height:36px;padding:0 16px;border-radius:4px;border:1px solid #8c3f34;background:#c0564b;color:#fff;font-weight:700;cursor:pointer;">解锁日志</button>' +
            "</form>" +
            '<div data-blog-lock-error="true" role="alert" style="margin-top:8px;font-size:12.5px;color:#b91c1c;min-height:18px;"></div>' +
            "</div>";
        } else {
          var hiddenInkHtml = "";
          if (currentPost.hiddenInk) {
            var ink = currentPost.hiddenInk;
            var revealed = isHiddenInkRevealed(context, ink.inkId);
            hiddenInkHtml =
              '<div style="margin-top:16px;padding:12px 14px;border:1px dashed #e2d4c0;border-radius:4px;background:#fffcf6;">' +
              '<div style="margin-bottom:6px;font-family:var(--font-sans,sans-serif);font-size:12px;color:#938170;">' +
              escapeHtml(ink.label || "文末似乎藏着反白文字") +
              ' <button type="button" class="mystery-hidden-ink-hint" data-reveal-ink="' +
              escapeHtml(ink.inkId) +
              '">' +
              (revealed ? "已显影" : "点击显影空白处") +
              "</button>" +
              "</div>" +
              '<div><span class="mystery-hidden-ink' +
              (revealed ? " is-revealed" : "") +
              '" data-hidden-ink="' +
              escapeHtml(ink.inkId) +
              '" tabindex="0">' +
              escapeHtml(ink.text || "") +
              "</span></div>" +
              "</div>";
          }

          var extraLinksHtml =
            Array.isArray(currentPost.links) && currentPost.links.length > 0
              ? '<div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:8px;font-family:var(--font-sans,sans-serif);font-size:12.5px;">' +
                currentPost.links
                  .map(function (linkItem) {
                    var target = escapeHtml(linkItem.url || "");
                    return (
                      '<a class="site-blog-tag" href="' +
                      target +
                      '" data-mystery-link="' +
                      target +
                      '" style="text-decoration:none;">' +
                      escapeHtml(linkItem.label || "") +
                      " →</a>"
                    );
                  })
                  .join("") +
                "</div>"
              : "";

          var comments = Array.isArray(currentPost.comments)
            ? currentPost.comments
            : [];
          var commentsHtml =
            '<section class="site-blog-comments">' +
            '<h3 class="site-blog-comments-title">访客留言（' +
            comments.length +
            "）</h3>" +
            (comments.length === 0
              ? '<div style="font-size:12.5px;color:#938170;">暂无公开留言。</div>'
              : comments
                  .map(function (c) {
                    return (
                      '<div class="site-blog-comment">' +
                      '<div class="site-blog-comment-meta">' +
                      '<span class="site-blog-comment-author">' +
                      escapeHtml(c.author || "匿名访客") +
                      "</span>" +
                      '<span class="site-blog-comment-date">' +
                      escapeHtml(c.date || "") +
                      "</span>" +
                      "</div>" +
                      '<div class="site-blog-comment-body">' +
                      escapeHtml(c.content || "") +
                      "</div>" +
                      "</div>"
                    );
                  })
                  .join("")) +
            "</section>";

          bodySectionHtml =
            '<div class="site-blog-post-body">' +
            renderParagraphs(currentPost.paragraphs) +
            hiddenInkHtml +

            extraLinksHtml +
            "</div>" +
            commentsHtml;
        }

        mainHtml =
          '<article class="site-blog-post' +
          (lockedNow ? " is-locked" : "") +
          '">' +
          unlistedNoticeHtml +
          '<div class="site-blog-post-header">' +
          '<h2 class="site-blog-post-title">' +
          escapeHtml(currentPost.title) +
          "</h2>" +
          postMetaHtml +
          "</div>" +
          bodySectionHtml +
          '<div style="margin-top:18px;padding-top:12px;border-top:1px dashed #d8cab8;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;font-family:var(--font-sans,sans-serif);font-size:12.5px;">' +
          '<a href="' +
          BLOG_HOME +
          '" data-mystery-link="' +
          BLOG_HOME +
          '" style="color:#8c3f34;text-decoration:none;">← 返回手记目录</a>' +
          '<a href="' +
          FORUM_HOME +
          '" data-mystery-link="' +
          FORUM_HOME +
          '" style="color:#6d5848;text-decoration:none;">友情链接：老黄历民俗茶馆 BBS →</a>' +
          "</div>" +
          "</article>";
      }
    } else {
      var filteredPosts = activeTag
        ? publicPosts.filter(function (post) {
            return Array.isArray(post.tags) && post.tags.indexOf(activeTag) !== -1;
          })
        : publicPosts;

      var filterBanner = activeTag
        ? '<div class="site-blog-widget" style="display:flex;align-items:center;justify-content:space-between;gap:10px;">' +
          '<span style="font-size:13px;">当前标签筛选：<strong>#' +
          escapeHtml(activeTag) +
          "</strong>（共 " +
          filteredPosts.length +
          " 篇公开手记）</span>" +
          '<a href="' +
          BLOG_HOME +
          '" data-mystery-link="' +
          BLOG_HOME +
          '" style="font-size:12px;color:#c0564b;">清除筛选</a>' +
          "</div>"
        : "";

      if (filteredPosts.length === 0) {
        mainHtml =
          filterBanner +
          '<article class="site-blog-post">' +
          '<div class="site-blog-post-body"><p>该标签下暂无公开手记。</p></div>' +
          "</article>";
      } else {
        mainHtml =
          filterBanner +
          filteredPosts
            .map(function (post) {
              var slug = post.slug || post.id;
              var postUrl = BLOG_HOME + "post/" + encodeURIComponent(slug);
              var isLockedCard =
                Boolean(post.isLocked) && !isGateUnlocked(context, post.gateId);
              var excerpt = isLockedCard
                ? "此日志设有访问口令：" +
                  (post.passwordHint || "需输入正确口令后方可阅读正文。")
                : Array.isArray(post.paragraphs) && post.paragraphs[0]
                  ? post.paragraphs[0]
                  : "";
              return (
                '<article class="site-blog-post' +
                (isLockedCard ? " is-locked" : "") +
                '">' +
                '<div class="site-blog-post-header">' +
                '<h2 class="site-blog-post-title">' +
                '<a href="' +
                escapeHtml(postUrl) +
                '" data-mystery-link="' +
                escapeHtml(postUrl) +
                '" style="color:inherit;text-decoration:none;">' +
                escapeHtml(post.title) +
                "</a>" +
                "</h2>" +
                '<div class="site-blog-post-meta">' +
                "<span>" +
                escapeHtml(post.date || "") +
                "</span>" +
                "<span>" +
                escapeHtml((post.tags || []).join(" · ")) +
                "</span>" +
                "<span>留言 " +
                (Array.isArray(post.comments) ? post.comments.length : 0) +
                "</span>" +
                "</div>" +
                "</div>" +
                '<div class="site-blog-post-body">' +
                "<p>" +
                escapeHtml(excerpt) +
                "</p>" +
                '<a href="' +
                escapeHtml(postUrl) +
                '" data-mystery-link="' +
                escapeHtml(postUrl) +
                '" style="font-family:var(--font-sans,sans-serif);font-size:13px;color:#8c3f34;text-decoration:none;">' +
                (isLockedCard ? "输入口令解锁阅读 →" : "阅读全文 →") +
                "</a>" +
                "</div>" +
                "</article>"
              );
            })
            .join("");
      }
    }

    var html =
      '<div class="site-blog-wrapper">' +
      '<header class="site-blog-banner">' +
      '<h1 class="site-blog-title">' +
      escapeHtml(data.blogTitle || "山野拾影 · 民俗摄影手记") +
      "</h1>" +
      '<p class="site-blog-subtitle">' +
      escapeHtml(data.subtitle || "") +
      "</p>" +
      '<nav class="site-blog-nav">' +
      navHtml +
      "</nav>" +
      "</header>" +
      '<div class="site-blog-layout">' +
      sidebarHtml +
      '<main class="site-blog-main">' +
      mainHtml +
      "</main>" +
      "</div>" +
      "</div>";

    return {
      html: html,
      pageTitle: pageTitle,
      themeClass: "site-theme-blog",
      sourceComment: sourceComment,
      sourceClueId: sourceClueId,
      snapshotMeta: {
        supported: false
      },
      onMount: function (containerEl) {
        if (!containerEl) {
          return;
        }

        var revealInkById = function (inkId) {
          if (!inkId) {
            return;
          }
          if (context && typeof context.revealHiddenInk === "function") {
            context.revealHiddenInk(inkId);
          }
          var inkSpan = containerEl.querySelector(
            '.mystery-hidden-ink[data-hidden-ink="' + inkId + '"]'
          );
          if (inkSpan) {
            inkSpan.classList.add("is-revealed");
          }
          var hintBtn = containerEl.querySelector(
            '[data-reveal-ink="' + inkId + '"]'
          );
          if (hintBtn) {
            hintBtn.textContent = "已显影";
          }
        };

        containerEl.querySelectorAll("[data-reveal-ink]").forEach(function (btn) {
          btn.addEventListener("click", function () {
            var inkId = btn.getAttribute("data-reveal-ink");
            revealInkById(inkId);
            if (context && typeof context.showToast === "function") {
              context.showToast("已显影文末反白隐藏文字！", "info");
            }
          });
        });

        containerEl.querySelectorAll(".mystery-hidden-ink").forEach(function (node) {
          var handleReveal = function () {
            revealInkById(node.getAttribute("data-hidden-ink"));
          };
          node.addEventListener("click", handleReveal);
          node.addEventListener("mouseup", handleReveal);
          node.addEventListener("keydown", function (ev) {
            if (ev.key === "Enter" || ev.key === " ") {
              ev.preventDefault();
              handleReveal();
            }
          });
        });

        var lockForm = containerEl.querySelector("[data-blog-lock-form]");
        if (lockForm && currentPost) {
          lockForm.addEventListener("submit", function (ev) {
            ev.preventDefault();
            var inputEl = lockForm.querySelector("[data-blog-lock-input]");
            var errEl = containerEl.querySelector("[data-blog-lock-error]");
            var normalizedInput = normalizeSecret(context, inputEl ? inputEl.value : "");

            var candidates = [];
            if (currentPost.password) {
              candidates.push(currentPost.password);
            }
            if (Array.isArray(currentPost.acceptedPasswords)) {
              currentPost.acceptedPasswords.forEach(function (item) {
                candidates.push(item);
              });
            }

            var matched = candidates.some(function (cand) {
              var normalizedCand = normalizeSecret(context, cand);
              return normalizedCand && normalizedCand === normalizedInput;
            });

            if (matched) {
              if (context && typeof context.unlockGate === "function") {
                context.unlockGate(currentPost.gateId || "gate-blog-locked");
              }
              if (context && typeof context.showToast === "function") {
                context.showToast("口令正确，已解锁《11月夜探槐安里》！", "success");
              }
              if (context && typeof context.rerender === "function") {
                context.rerender();
              }
            } else {
              if (errEl) {
                errEl.textContent =
                  "口令不符：请核对《寒露记》源码注释中的 4 位字母与《太平社老戏台》中的 4 位公历年份。";
              }
              if (context && typeof context.showToast === "function") {
                context.showToast("加密日志口令不正确，请重试。", "error");
              }
            }
          });
        }
      }
    };
  }

  /* ========================================================================
   * 3. FORUM RENDERER (bbs.huangli.lh)
   * ======================================================================== */
  function renderAlmanac(widget) {
    if (!widget) {
      return "";
    }
    return (
      '<aside class="site-forum-almanac" aria-label="茶馆老黄历万年历">' +
      '<div class="site-almanac-head">' +
      "<span>丰宁老黄历 · 万年历挂件</span>" +
      "<span>" +
      escapeHtml(widget.ganzhi || "第六十一甲子 · 无名太岁值日") +
      "</span>" +
      "</div>" +
      '<div class="site-almanac-date is-intercalary">' +
      "<div>" +
      escapeHtml(widget.lunarDate || "甲辰年 闰腊月 廿九") +
      "</div>" +
      '<div style="font-size:12.5px;font-family:var(--font-mono,monospace);margin-top:4px;letter-spacing:0.04em;">' +
      escapeHtml(widget.gregorianDate || "2019年02月30日（岁差异常）") +
      "</div>" +
      "</div>" +
      '<div class="site-almanac-grid">' +
      '<div class="site-almanac-yi">' +
      '<span class="site-almanac-badge">宜</span>' +
      escapeHtml(widget.yi || "补缺 · 代位 · 换名") +
      "</div>" +
      '<div class="site-almanac-ji">' +
      '<span class="site-almanac-badge">忌</span>' +
      escapeHtml(widget.ji || "拆梁 · 查谱 · 照影") +
      "</div>" +
      "</div>" +
      '<div class="site-almanac-note">' +
      escapeHtml(widget.anomalyNote || "") +
      "</div>" +
      "</aside>"
    );
  }

  function renderForum(route, siteData, context) {
    var data = siteData || {};
    var boards = Array.isArray(data.boards) ? data.boards : [];
    var threads = Array.isArray(data.threads) ? data.threads : [];
    var privateMessages = Array.isArray(data.privateMessages)
      ? data.privateMessages
      : [];
    var segments = route && Array.isArray(route.segments) ? route.segments : [];
    var isTimeMachine = Boolean(context && context.isTimeMachine);

    var view = "list";
    var activeBoardId = "";
    var activeThreadId = "";

    if (segments[0] === "board" && segments[1]) {
      view = "list";
      activeBoardId = segments[1];
    } else if (segments[0] === "thread" && segments[1]) {
      view = "thread";
      activeThreadId = segments[1];
    } else if (segments[0] === "messages") {
      view = "messages";
    }

    var boardNameMap = {};
    boards.forEach(function (b) {
      boardNameMap[b.id] = b.name;
    });

    var boardTabsHtml =
      '<a class="site-forum-board-tab' +
      (view === "list" && !activeBoardId ? " is-active" : "") +
      '" href="' +
      FORUM_HOME +
      '" data-mystery-link="' +
      FORUM_HOME +
      '" style="text-decoration:none;">全部主题</a>' +
      boards
        .map(function (b) {
          var url = FORUM_HOME + "board/" + encodeURIComponent(b.id);
          return (
            '<a class="site-forum-board-tab' +
            (view === "list" && activeBoardId === b.id ? " is-active" : "") +
            '" href="' +
            escapeHtml(url) +
            '" data-mystery-link="' +
            escapeHtml(url) +
            '" style="text-decoration:none;">' +
            escapeHtml(b.name) +
            "</a>"
          );
        })
        .join("") +
      '<a class="site-forum-board-tab' +
      (view === "messages" ? " is-active" : "") +
      '" href="' +
      FORUM_HOME +
      'messages" data-mystery-link="' +
      FORUM_HOME +
      'messages" style="text-decoration:none;">站内私信 (' +
      privateMessages.length +
      ")</a>";

    var bodyHtml = "";
    var pageTitle = data.siteName || "老黄历民俗茶馆 BBS";
    var sourceComment =
      "<!-- BBS_HUANGLI: bbs.huangli.lh | ALMANAC_ERR: 2019-02-30 | SNAPSHOT_THREAD: 610 -->";
    var snapshotMeta = { supported: false };

    if (view === "messages") {
      pageTitle = "站内私信 - " + (data.siteName || "老黄历民俗茶馆 BBS");
      bodyHtml =
        '<div class="site-forum-thread-header">' +
        '<a class="site-forum-back-link" href="' +
        FORUM_HOME +
        '" data-mystery-link="' +
        FORUM_HOME +
        '" style="text-decoration:none;">← 返回版块列表</a>' +
        '<h2 class="site-forum-thread-title">站内私信归档</h2>' +
        "</div>" +
        '<div class="site-forum-pm-box">' +
        privateMessages
          .map(function (pm) {
            var pmBody = pm.body || pm.content || "";
            return (
              '<div class="site-forum-pm-item">' +
              '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:6px;font-size:12px;color:#475569;">' +
              "<span><strong>发件人：</strong>" +
              escapeHtml(pm.from || "匿名") +
              (pm.to ? " → <strong>收件人：</strong>" + escapeHtml(pm.to) : "") +
              "</span>" +
              (pm.sentAt
                ? '<span style="font-family:var(--font-mono,monospace);">' +
                  escapeHtml(pm.sentAt) +
                  "</span>"
                : "") +
              "</div>" +
              '<div style="font-weight:700;color:#1e3a8a;margin-bottom:6px;">主题：' +
              escapeHtml(pm.subject || "") +
              "</div>" +
              '<div style="line-height:1.7;color:#334155;">' +
              escapeHtml(pmBody) +
              "</div>" +
              "</div>"
            );
          })
          .join("") +
        '<div style="margin-top:12px;display:flex;flex-wrap:wrap;gap:10px;font-size:12.5px;">' +
        '<a class="site-forum-back-link" href="https://bbs.huangli.lh/thread/610" data-mystery-link="https://bbs.huangli.lh/thread/610" style="text-decoration:none;">直达 610 号帖 →</a>' +
        '<a class="site-forum-back-link" href="https://bbs.huangli.lh/thread/618" data-mystery-link="https://bbs.huangli.lh/thread/618" style="text-decoration:none;">直达 618 号水楼 →</a>' +
        '<a class="site-forum-back-link" href="https://wy.huaianli.lh/notice/building7-demolition" data-mystery-link="https://wy.huaianli.lh/notice/building7-demolition" style="text-decoration:none;">查验槐安里 7 号楼拆迁公示 →</a>' +
        "</div>" +
        "</div>";
    } else if (view === "thread") {
      var thread = threads.find(function (t) {
        return String(t.id) === String(activeThreadId);
      });

      if (!thread) {
        pageTitle = "帖子不存在 - " + (data.siteName || "老黄历民俗茶馆 BBS");
        bodyHtml =
          '<div class="site-forum-thread-header">' +
          '<a class="site-forum-back-link" href="' +
          FORUM_HOME +
          '" data-mystery-link="' +
          FORUM_HOME +
          '" style="text-decoration:none;">← 返回版块列表</a>' +
          '<h2 class="site-forum-thread-title">该主题帖不存在或已被清除</h2>' +
          "</div>";
      } else {
        pageTitle = thread.title + " - " + (data.siteName || "老黄历民俗茶馆 BBS");
        if (thread.sourceComment) {
          sourceComment = thread.sourceComment;
        }
        if (thread.hasSnapshotRestore) {
          snapshotMeta = {
            supported: true,
            snapshotDate: data.snapshotDate || "2019-02-30",
            bannerText:
              "当前正在浏览老黄历茶馆 " +
              (data.snapshotDate || "2019-02-30") +
              " 岁差时光机快照（已还原被屏蔽楼层 2F / 5F / 8F）"
          };
        }

        var snapshotCalloutHtml = "";
        if (thread.hasSnapshotRestore) {
          if (isTimeMachine) {
            snapshotCalloutHtml =
              '<div class="mystery-snapshot-callout" style="margin:12px 14px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">' +
              "<span>历史镜像存档（" +
              escapeHtml(data.snapshotDate || "2019-02-30") +
              "）：显示当时保留的帖子，楼层时间按原样抄录。</span>" +
              '<button type="button" class="site-forum-back-link" data-forum-wayback="off">收起历史镜像</button>' +
              "</div>";
          } else {
            snapshotCalloutHtml =
              '<div class="mystery-snapshot-callout" style="margin:12px 14px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">' +
              "<span>版面注记：本帖部分早期回复已不可见，可通过 " +
              escapeHtml(data.snapshotDate || "2019-02-30") +
              " 历史镜像查阅原貌。</span>" +
              '<button type="button" class="site-forum-back-link" data-forum-wayback="true">查阅历史镜像</button>' +
              "</div>";
          }
        }

        var floorsHtml = (thread.posts || [])
          .map(function (post) {
            var avatarChar = post.author ? String(post.author).slice(0, 1) : "客";
            var isOp = post.floor === 1;
            var contentHtml = "";

            if (post.isDeleted) {
              if (isTimeMachine) {
                contentHtml =
                  '<div class="mystery-restored-post">' +
                  '<div class="mystery-restored-badge">' +
                  escapeHtml(data.snapshotDate || "2019-02-30") +
                  " 存档抄本</div>" +
                  '<div style="margin-bottom:10px;">' +
                  renderMultiline(post.restoredContent || "") +
                  "</div>" +
                  "</div>";
              } else {
                contentHtml =
                  '<div class="site-forum-deleted-post">' +
                  '<div style="margin-bottom:8px;">' +
                  escapeHtml(
                    post.deletedNotice || "[该楼层因违反社区规范已被管理员屏蔽]"
                  ) +
                  "</div>" +
                  (thread.hasSnapshotRestore
                    ? '<button type="button" class="site-forum-back-link" data-forum-wayback="true" style="font-style:normal;">查看本帖 2019-02-30 存档</button>'
                    : "") +
                  "</div>";
              }
            } else {
              contentHtml = renderMultiline(post.content || "");
            }

            var signatureHtml =
              post.signature && (!post.isDeleted || isTimeMachine)
                ? '<div class="site-forum-signature">—— ' +
                  escapeHtml(post.signature) +
                  "</div>"
                : "";

            return (
              '<article class="site-forum-floor" data-floor="' +
              escapeHtml(post.floor) +
              '">' +
              '<div class="site-forum-author-col">' +
              '<div class="site-forum-avatar-box">' +
              escapeHtml(avatarChar) +
              "</div>" +
              '<div class="site-forum-username">' +
              escapeHtml(post.author || "匿名") +
              "</div>" +
              '<span class="site-forum-user-badge' +
              (isOp ? " is-op" : "") +
              '">' +
              escapeHtml(isOp ? "楼主 · " + (post.badge || "茶客") : post.badge || "茶客") +
              "</span>" +
              '<div class="site-forum-user-meta">' +
              (post.userId ? "<div>账号：" + escapeHtml(post.userId) + "</div>" : "") +
              "<div>楼层：#" +
              escapeHtml(post.floor) +
              "F</div>" +
              "</div>" +
              "</div>" +
              '<div class="site-forum-content-col">' +
              '<div class="site-forum-floor-meta">' +
              "<span>发表于 " +
              escapeHtml(post.postedAt || post.date || "") +
              "</span>" +
              '<span class="site-forum-floor-num">#' +
              escapeHtml(post.floor) +
              "F</span>" +
              "</div>" +
              '<div class="site-forum-post-body">' +
              contentHtml +
              "</div>" +
              signatureHtml +
              "</div>" +
              "</article>"
            );
          })
          .join("");

        bodyHtml =
          '<div class="site-forum-thread-header">' +
          '<a class="site-forum-back-link" href="' +
          FORUM_HOME +
          '" data-mystery-link="' +
          FORUM_HOME +
          '" style="text-decoration:none;">← 返回版块列表</a>' +
          '<h2 class="site-forum-thread-title">[' +
          escapeHtml(boardNameMap[thread.boardId] || "茶座") +
          "] " +
          escapeHtml(thread.title) +
          "</h2>" +
          '<span style="font-size:12px;color:#475569;font-family:var(--font-mono,monospace);">浏览 ' +
          escapeHtml(thread.views || 0) +
          " · 回复 " +
          (Array.isArray(thread.posts) ? thread.posts.length : 0) +
          "</span>" +
          "</div>" +
          snapshotCalloutHtml +
          floorsHtml;
      }
    } else {
      var visibleThreads = activeBoardId
        ? threads.filter(function (t) {
            return t.boardId === activeBoardId;
          })
        : threads;

      var boardDescHtml = activeBoardId
        ? boards
            .filter(function (b) {
              return b.id === activeBoardId;
            })
            .map(function (b) {
              return (
                '<div style="padding:9px 14px;background:#f4f7fb;border-bottom:1px solid #d5e0ec;font-size:12.5px;color:#475569;">' +
                "<strong>" +
                escapeHtml(b.name) +
                "：</strong>" +
                escapeHtml(b.description || "") +
                "</div>"
              );
            })
            .join("")
        : "";

      bodyHtml =
        boardDescHtml +
        '<div class="site-forum-thread-list">' +
        visibleThreads
          .map(function (t) {
            var url = FORUM_HOME + "thread/" + encodeURIComponent(t.id);
            var badges = "";
            if (t.isPinned) {
              badges += '<span class="site-forum-badge-top">置顶</span>';
            }
            if ((t.views || 0) >= 1500) {
              badges += '<span class="site-forum-badge-hot">热议</span>';
            }
            if (t.hasSnapshotRestore) {
              badges += '<span class="site-forum-badge-del">有存档</span>';
            }
            return (
              '<a class="site-forum-thread-row' +
              (t.isPinned ? " is-pinned" : "") +
              '" href="' +
              escapeHtml(url) +
              '" data-mystery-link="' +
              escapeHtml(url) +
              '" style="text-decoration:none;color:inherit;">' +
              '<div class="site-forum-thread-subject">' +
              badges +
              "<span>" +
              escapeHtml(t.title) +
              "</span>" +
              "</div>" +
              '<div class="site-forum-thread-meta">' +
              escapeHtml(t.author || "") +
              "</div>" +
              '<div class="site-forum-thread-meta">' +
              escapeHtml((t.createdAt || "").slice(0, 10)) +
              "</div>" +
              "</a>"
            );
          })
          .join("") +
        "</div>";
    }

    var html =
      '<div class="site-forum-wrapper">' +
      '<header class="site-forum-header">' +
      "<div>" +
      '<h1 class="site-forum-title">' +
      escapeHtml(data.siteName || "老黄历民俗茶馆 BBS") +
      "</h1>" +
      '<div style="font-size:12px;color:#dbeafe;margin-top:2px;">' +
      escapeHtml(data.tagline || "") +
      "</div>" +
      "</div>" +
      '<div class="site-forum-stats">' +
      "主题 " +
      threads.length +
      " · 岁差基准 " +
      escapeHtml(data.snapshotDate || "2019-02-30") +
      (isTimeMachine ? " · [时光机已开启]" : "") +
      "</div>" +
      "</header>" +
      '<nav class="site-forum-boards">' +
      boardTabsHtml +
      "</nav>" +
      renderAlmanac(data.almanacWidget) +
      '<div class="site-forum-sticky-bar">' +
      '<span class="site-forum-sticky-badge">站务</span>' +
      "<span>" +
      escapeHtml(data.announcement || "") +
      "</span>" +
      "</div>" +
      bodyHtml +
      "</div>";

    return {
      html: html,
      pageTitle: pageTitle,
      themeClass: "site-theme-forum",
      sourceComment: sourceComment,
      sourceClueId: null,
      snapshotMeta: snapshotMeta,
      onMount: function (containerEl) {
        if (!containerEl) {
          return;
        }
        containerEl
          .querySelectorAll('[data-forum-wayback="true"]')
          .forEach(function (btn) {
            btn.addEventListener("click", function () {
              if (context && typeof context.toggleTimeMachine === "function") {
                context.toggleTimeMachine(true);
              }
            });
          });
        containerEl
          .querySelectorAll('[data-forum-wayback="off"]')
          .forEach(function (btn) {
            btn.addEventListener("click", function () {
              if (context && typeof context.toggleTimeMachine === "function") {
                context.toggleTimeMachine(false);
              }
            });
          });
      }
    };
  }

  window.MysteryRenderers = window.MysteryRenderers || {};
  window.MysteryRenderers.blog = renderBlog;
  window.MysteryRenderers.forum = renderForum;
  window.MysteryRenderers.portal = renderPortal;
})();
