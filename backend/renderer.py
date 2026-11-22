"""Lightweight single-pass ``{{key}}`` HTML renderer and static site builder."""

from __future__ import annotations

from datetime import datetime
import html
from pathlib import Path
import re
import shutil
import time
from typing import Any, Mapping
import urllib.parse

from backend.content_loader import Post, load_all_content
from backend.feeds import effective_site_url, prefix_url, write_feeds
from backend.markdown_engine import render_markdown, render_toc_html


PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")
RAW_HTML_KEYS = frozenset({"page_content", "extra_head", "extra_scripts"})
PROTECTED_CODE_HTML_RE = re.compile(
    r"(?:<pre\b[^>]*>.*?</pre>|<code\b[^>]*>.*?</code>)",
    re.DOTALL | re.IGNORECASE,
)
HTML_ATTR_ROOT_URL_RE = re.compile(
    r"""(?<![A-Za-z0-9_:-])((?:href|src)\s*=\s*)(["'])(/(?!/)[^"']*)\2""",
    re.IGNORECASE,
)


def normalize_base_path(raw: str | None) -> str:
    """Normalize a site subpath into ``''`` (root) or ``'/subpath'``."""
    if raw is None:
        return ""
    stripped = raw.strip().strip("/")
    return f"/{stripped}" if stripped else ""


def _normalize_cname(raw: str | None) -> str:
    """Extract bare hostname for GitHub Pages ``CNAME`` from a domain or URL."""
    if not raw:
        return ""
    text = raw.strip()
    if not text:
        return ""
    parsed = urllib.parse.urlsplit(text if "://" in text else f"//{text}")
    host = (parsed.netloc or parsed.path.split("/", 1)[0]).strip().rstrip("/")
    if ":" in host:
        host = host.split(":", 1)[0]
    return host


def apply_base_path_to_html(html_text: str, base_path: str) -> str:
    """Prefix root-relative ``href``/``src`` attributes outside ``<pre>``/``<code>``."""
    bp = normalize_base_path(base_path)
    if not bp:
        return html_text

    protected: list[str] = []

    def _mask_code(match: re.Match[str]) -> str:
        token = f"\x00__CODE_BLOCK_{len(protected)}__\x00"
        protected.append(match.group(0))
        return token

    masked = PROTECTED_CODE_HTML_RE.sub(_mask_code, html_text)

    def _rewrite_attr(match: re.Match[str]) -> str:
        attr_prefix = match.group(1)
        quote = match.group(2)
        raw_url = match.group(3)
        rewritten = prefix_url(raw_url, bp)
        return f"{attr_prefix}{quote}{rewritten}{quote}"

    rewritten_html = HTML_ATTR_ROOT_URL_RE.sub(_rewrite_attr, masked)

    for idx, original in enumerate(protected):
        rewritten_html = rewritten_html.replace(f"\x00__CODE_BLOCK_{idx}__\x00", original)

    return rewritten_html


def _neutralize_braces(text: str) -> str:
    """Replace literal ``{{key}}`` in content strings so output stays placeholder-free."""
    return PLACEHOLDER_RE.sub(r"&#123;&#123;\1&#125;&#125;", text)


def render_template(template_text: str, context: Mapping[str, Any]) -> str:
    """Perform single-pass ``{{key}}`` substitution with strict missing-key checks.

    Keys ending in ``_html`` or listed in ``RAW_HTML_KEYS`` are injected directly;
    all other scalar values are escaped with ``html.escape(..., quote=True)``.
    """

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise KeyError(f"Missing template variable '{{{{{key}}}}}'")
        raw_val = context[key]
        text_val = "" if raw_val is None else str(raw_val)
        if key in RAW_HTML_KEYS or key.endswith("_html"):
            return text_val
        return _neutralize_braces(html.escape(text_val, quote=True))

    return PLACEHOLDER_RE.sub(_replace, template_text)


class TemplateEngine:
    """Loads and caches HTML page templates and partials from ``templates/``."""

    def __init__(self, templates_dir: Path) -> None:
        self.templates_dir = templates_dir
        self._cache: dict[str, str] = {}

    def _load(self, rel_path: str) -> str:
        if rel_path not in self._cache:
            target = self.templates_dir / rel_path
            if not target.is_file():
                raise FileNotFoundError(f"Template not found: {target}")
            self._cache[rel_path] = target.read_text(encoding="utf-8")
        return self._cache[rel_path]

    def render(self, rel_path: str, context: Mapping[str, Any]) -> str:
        """Render a template at ``templates/<rel_path>`` with ``context``."""
        return render_template(self._load(rel_path), context)

    def render_partial(self, partial_name: str, context: Mapping[str, Any]) -> str:
        """Render a partial template from ``templates/partials/<partial_name>``."""
        return self.render(f"partials/{partial_name}", context)


def _render_inline_tag_pills(tags: list[str]) -> str:
    """Render clickable tag pills (without counts) for cards and post headers."""
    pills: list[str] = []
    for tag in tags:
        href_tag = urllib.parse.quote(tag, safe="")
        esc_tag = _neutralize_braces(html.escape(tag, quote=True))
        pills.append(
            f'<a class="tag-pill" href="/articles/?tag={href_tag}" '
            f'data-filter-tag="{esc_tag}">{esc_tag}</a>'
        )
    return "\n".join(pills)


def _render_filter_buttons(posts: list[Post], tag_stats: list[dict[str, Any]]) -> str:
    """Render archive filter pill buttons for ``all`` plus every tag."""
    buttons = [
        '<button type="button" class="filter-pill is-active" '
        'data-filter-tag="all" aria-pressed="true">'
        f'全部 <span class="filter-pill-count">{len(posts)}</span></button>'
    ]
    for item in tag_stats:
        tag_name = str(item["name"])
        count = int(item["count"])
        esc_tag = _neutralize_braces(html.escape(tag_name, quote=True))
        buttons.append(
            f'<button type="button" class="filter-pill" '
            f'data-filter-tag="{esc_tag}" aria-pressed="false">'
            f'{esc_tag} <span class="filter-pill-count">{count}</span></button>'
        )
    return "\n".join(buttons)


def _render_icp_html(site: dict[str, Any]) -> str:
    """Render footer ICP filing number link when configured."""
    icp_number = _neutralize_braces(html.escape(str(site.get("icp_number", "")), quote=True))
    icp_url = str(site.get("icp_url", "")).strip()
    if not icp_number:
        return ""
    if icp_url:
        esc_url = html.escape(icp_url, quote=True)
        return (
            f'<a class="icp-link" href="{esc_url}" '
            f'target="_blank" rel="noopener noreferrer">{icp_number}</a>'
        )
    return f'<span class="icp-link">{icp_number}</span>'


def _render_social_links(social_links: list[dict[str, Any]]) -> str:
    """Render social link pills for the About page."""
    pills: list[str] = []
    for item in social_links:
        label = _neutralize_braces(html.escape(str(item.get("label", "")), quote=True))
        url = str(item.get("url", "#")).strip()
        esc_url = html.escape(url, quote=True)
        extra_attrs = (
            ' target="_blank" rel="noopener noreferrer"'
            if url.startswith(("http://", "https://"))
            else ""
        )
        pills.append(f'<a class="social-pill" href="{esc_url}"{extra_attrs}>{label}</a>')
    return "\n".join(pills)


def _render_project_card(engine: TemplateEngine, project: dict[str, Any]) -> str:
    """Render one project card using ``partials/project_card.html``."""
    stack_html = "\n".join(
        f'<span class="stack-tag">{_neutralize_braces(html.escape(tech, quote=True))}</span>'
        for tech in project.get("stack", [])
    )
    name_html = render_template("{{name}}", project)
    link_html = ""
    if project["url"]:
        name_html = render_template('<a href="{{url}}">{{name}}</a>', project)
        link_html = render_template('\n    <a class="project-link" href="{{url}}">查看详情 →</a>', project)
    return engine.render_partial(
        "project_card.html",
        {
            "name_html": name_html,
            "status": project["status"],
            "year": project["year"],
            "summary": project["summary"],
            "stack_html": stack_html,
            "link_html": link_html,
        },
    )


def _render_post_row(engine: TemplateEngine, post: Post) -> str:
    """Render one archive row using ``partials/post_row.html``."""
    return engine.render_partial(
        "post_row.html",
        {
            "url": post.url,
            "date": post.date,
            "date_short": post.date_short,
            "year": post.year,
            "category": post.category,
            "tags_csv": post.tags_csv,
            "title": post.title,
            "summary": post.summary,
            "reading_time": str(post.reading_time),
            "tags_html": _render_inline_tag_pills(post.tags),
        },
    )


def _render_related_posts_html(related_posts: list[dict[str, str]]) -> str:
    """Render related-reading cards inside ``.related-grid``."""
    cards: list[str] = []
    for rel in related_posts:
        url = html.escape(rel["url"], quote=True)
        meta = _neutralize_braces(
            html.escape(f"{rel['category']} · {rel['date']} · {rel['reading_time']} 分钟", quote=True)
        )
        title = _neutralize_braces(html.escape(rel["title"], quote=True))
        cards.append(
            f'<a class="related-card" href="{url}">'
            f'<span class="nav-post-label related-card-meta">{meta}</span>'
            f'<span class="nav-post-title related-card-title">{title}</span>'
            "</a>"
        )
    return "\n".join(cards)


def _wrap_base(
    engine: TemplateEngine,
    site: dict[str, Any],
    *,
    page_title: str,
    page_description: str,
    route_path: str,
    active_nav: str,
    page_content: str,
    base_path: str = "",
    extra_head: str = "",
    extra_scripts: str = "",
) -> str:
    """Wrap rendered page body in ``templates/base.html``."""
    normalized_bp = normalize_base_path(base_path)
    site_root = effective_site_url(str(site["site_url"]), normalized_bp)
    canonical = f"{site_root}{route_path}"
    icp_html = _render_icp_html(site)
    current_year = str(datetime.now().year)

    rendered = engine.render(
        "base.html",
        {
            "base_path": normalized_bp,
            "page_title": page_title,
            "page_description": page_description,
            "canonical_url": canonical,
            "site_title": site["site_title"],
            "site_tagline": site["site_tagline"],
            "author_name": site["author_name"],
            "icp_html": icp_html,
            "nav_home_active": "is-active" if active_nav == "home" else "",
            "nav_articles_active": "is-active" if active_nav == "articles" else "",
            "nav_projects_active": "is-active" if active_nav == "projects" else "",
            "nav_about_active": "is-active" if active_nav == "about" else "",
            "extra_head": extra_head,
            "page_content": page_content,
            "extra_scripts": extra_scripts,
            "current_year": current_year,
        },
    )
    return apply_base_path_to_html(rendered, normalized_bp)


def _write_html(path: Path, html_content: str) -> None:
    """Write UTF-8 HTML file and verify zero unreplaced template placeholders remain."""
    leftover = PLACEHOLDER_RE.findall(html_content)
    if leftover:
        raise ValueError(f"Unreplaced template placeholder(s) {leftover} in {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")


def render_site(
    project_root: Path,
    dist_dir: Path | None = None,
    clean: bool = True,
    base_path: str = "",
    site_url: str | None = None,
    cname: str = "",
) -> dict[str, Any]:
    """Build the entire static site into ``dist/`` and return build metrics."""
    started = time.perf_counter()

    normalized_base_path = normalize_base_path(base_path)
    content_dir = project_root / "content"
    templates_dir = project_root / "templates"
    static_dir = project_root / "static"
    out_dir = dist_dir if dist_dir is not None else project_root / "dist"

    if clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Always emit .nojekyll so GitHub Pages skips Jekyll processing
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    # 1. Copy static assets cleanly
    static_files_count = 0
    if static_dir.is_dir():
        dest_static = out_dir / "static"
        if dest_static.exists():
            shutil.rmtree(dest_static)
        shutil.copytree(static_dir, dest_static)
        static_files_count = sum(1 for item in dest_static.rglob("*") if item.is_file())

    # 2. Load content and render Markdown posts + about page
    loaded = load_all_content(content_dir)
    site: dict[str, Any] = dict(loaded["site"])
    if site_url is not None and site_url.strip():
        site["site_url"] = site_url.strip().rstrip("/")

    # Optional CNAME file for custom domain hosting on GitHub Pages
    raw_cname = cname if (cname and cname.strip()) else str(site.get("custom_domain", ""))
    cname_domain = _normalize_cname(raw_cname)
    cname_path = out_dir / "CNAME"
    if cname_domain:
        cname_path.write_text(f"{cname_domain}\n", encoding="utf-8")
        has_cname = True
    else:
        if cname_path.exists():
            cname_path.unlink()
        has_cname = False

    projects: list[dict[str, Any]] = loaded["projects"]
    posts: list[Post] = loaded["posts"]
    tag_stats: list[dict[str, Any]] = loaded["tag_stats"]
    category_stats: list[dict[str, Any]] = loaded["category_stats"]

    for post in posts:
        body_html, toc = render_markdown(post.body_md)
        post.body_html = body_html
        post.toc = toc

    about_body_html, _ = render_markdown(loaded["about_md"])

    engine = TemplateEngine(templates_dir)
    html_pages_count = 0

    # 3. Render Homepage: dist/index.html
    home_body = engine.render("home.html", {})
    _write_html(
        out_dir / "index.html",
        _wrap_base(
            engine,
            site,
            page_title=f"{site['site_title']} — {site['site_tagline']}",
            page_description=site["site_tagline"],
            route_path="/",
            active_nav="home",
            page_content=home_body,
            base_path=normalized_base_path,
            extra_head=(
                '<link rel="stylesheet" href="/static/css/home-cover.css?v=9">\n'
                '  <link rel="preload" as="image" href="/static/images/starloop-cover.jpg" fetchpriority="high">'
            ),
            extra_scripts='<script src="/static/js/home-cover.js?v=8" defer></script>',
        ),
    )
    html_pages_count += 1

    # 4. Render Articles Archive: dist/articles/index.html
    archive_html = (
        engine.render_partial(
            "articles_list.html",
            {
                "total_posts": str(len(posts)),
                "tag_filters_html": _render_filter_buttons(posts, tag_stats),
                "articles_list_html": "\n".join(_render_post_row(engine, post) for post in posts),
            },
        )
        if posts else '<p class="search-empty">暂无已发布文章。</p>'
    )
    articles_body = engine.render(
        "articles.html",
        {
            "archive_subtitle": (
                "全部专栏随笔与工程手记按时间倒序排列，支持按主题标签就地筛选。"
                if posts else "专栏随笔与工程手记。"
            ),
            "archive_html": archive_html,
        },
    )
    _write_html(
        out_dir / "articles" / "index.html",
        _wrap_base(
            engine,
            site,
            page_title=f"文章归档 · {site['site_title']}",
            page_description=f"{site['site_title']} 全部专栏文章与工程随笔归档。",
            route_path="/articles/",
            active_nav="articles",
            page_content=articles_body,
            base_path=normalized_base_path,
        ),
    )
    html_pages_count += 1

    # 5. Render Article Detail Pages: dist/articles/<slug>/index.html
    for post in posts:
        post_cover_html = (
            f'<img class="post-cover" src="{html.escape(post.cover, quote=True)}" '
            f'alt="{_neutralize_braces(html.escape(post.title, quote=True))}" '
            'width="800" height="480">'
            if post.cover
            else ""
        )
        prev_post_html = (
            engine.render_partial(
                "nav_post_card.html",
                {
                    "direction_label": "← 上一篇",
                    "direction_class": "nav-post-card--prev",
                    "url": post.prev_post["url"],
                    "title": post.prev_post["title"],
                    "date": post.prev_post["date"],
                },
            )
            if post.prev_post
            else ('<div aria-hidden="true"></div>' if post.next_post else "")
        )
        next_post_html = (
            engine.render_partial(
                "nav_post_card.html",
                {
                    "direction_label": "下一篇 →",
                    "direction_class": "nav-post-card--next",
                    "url": post.next_post["url"],
                    "title": post.next_post["title"],
                    "date": post.next_post["date"],
                },
            )
            if post.next_post
            else ""
        )
        post_body = engine.render(
            "post.html",
            {
                "post_title": post.title,
                "post_subtitle": post.summary,
                "post_date": post.date,
                "post_reading_time": str(post.reading_time),
                "post_word_count": str(post.word_count),
                "post_category": post.category,
                "post_tags_html": _render_inline_tag_pills(post.tags),
                "post_cover_html": post_cover_html,
                "post_body_html": post.body_html,
                "post_toc_html": render_toc_html(post.toc),
                "prev_post_html": prev_post_html,
                "next_post_html": next_post_html,
                "related_posts_html": _render_related_posts_html(post.related_posts),
            },
        )
        _write_html(
            out_dir / "articles" / post.slug / "index.html",
            _wrap_base(
                engine,
                site,
                page_title=f"{post.title} · {site['site_title']}",
                page_description=post.summary or post.excerpt,
                route_path=post.url,
                active_nav="articles",
                page_content=post_body,
                base_path=normalized_base_path,
            ),
        )
        html_pages_count += 1

    # 6. Render Projects Page: dist/projects/index.html
    project_cards = "\n".join(_render_project_card(engine, project) for project in projects)
    projects_body = engine.render(
        "projects.html",
        {
            "projects_list_html": (
                f'<div class="projects-grid projects-grid--catalog">\n{project_cards}\n</div>'
                if project_cards else '<p class="search-empty">暂无已发布项目。</p>'
            ),
        },
    )
    _write_html(
        out_dir / "projects" / "index.html",
        _wrap_base(
            engine,
            site,
            page_title=f"项目 · {site['site_title']}",
            page_description=f"{site['author_name']} 的开源工具、排版设计系统与运维实践项目。",
            route_path="/projects/",
            active_nav="projects",
            page_content=projects_body,
            base_path=normalized_base_path,
        ),
    )
    html_pages_count += 1

    # 7. Render About Page: dist/about/index.html
    about_body = engine.render(
        "about.html",
        {
            "author_name": site["author_name"],
            "author_role": site["author_role"],
            "author_location": site["author_location"],
            "author_bio": site["author_bio"],
            "about_body_html": about_body_html,
            "social_links_html": _render_social_links(site.get("social_links", [])),
        },
    )
    _write_html(
        out_dir / "about" / "index.html",
        _wrap_base(
            engine,
            site,
            page_title=f"关于与建造说明 · {site['site_title']}",
            page_description=site["author_bio"],
            route_path="/about/",
            active_nav="about",
            page_content=about_body,
            base_path=normalized_base_path,
        ),
    )
    html_pages_count += 1

    # 8. Render 404 Page: dist/404.html
    not_found_body = engine.render("404.html", {})
    _write_html(
        out_dir / "404.html",
        _wrap_base(
            engine,
            site,
            page_title=f"404 页面未找到 · {site['site_title']}",
            page_description="请求的页面未找到，可返回首页或使用站内搜索。",
            route_path="/404.html",
            active_nav="",
            page_content=not_found_body,
            base_path=normalized_base_path,
        ),
    )
    html_pages_count += 1

    # 9. Write JSON APIs, RSS 2.0, Sitemap XML, robots.txt
    feed_paths = write_feeds(
        out_dir,
        site,
        posts,
        tag_stats,
        category_stats,
        base_path=normalized_base_path,
    )

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "dist_dir": str(out_dir),
        "base_path": normalized_base_path,
        "has_cname": has_cname,
        "posts_count": len(posts),
        "projects_count": len(projects),
        "tags_count": len(tag_stats),
        "html_pages_count": html_pages_count,
        "static_files_count": static_files_count,
        "feed_files_count": len(feed_paths),
        "elapsed_ms": round(elapsed_ms, 2),
    }
