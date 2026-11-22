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


CATEGORY_ICONS: dict[str, str] = {
    "all": (
        '<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true">'
        '<ellipse cx="9" cy="9" rx="7.2" ry="3.2" transform="rotate(-22 9 9)" '
        'stroke="currentColor" stroke-width="1.2" stroke-opacity="0.72"/>'
        '<path d="M9 3.6L10.15 7.85L14.4 9L10.15 10.15L9 14.4L7.85 10.15L3.6 9L7.85 7.85Z" '
        'fill="currentColor"/>'
        "</svg>"
    ),
    "code": (
        '<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true">'
        '<path d="M6.2 5.2L2.5 9L6.2 12.8M11.8 5.2L15.5 9L11.8 12.8" '
        'stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M9 6.6L10.3 9L9 11.4L7.7 9Z" fill="currentColor" fill-opacity="0.85"/>'
        "</svg>"
    ),
    "image": (
        '<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true">'
        '<rect x="2.6" y="3.2" width="12.8" height="11.6" rx="2.2" '
        'stroke="currentColor" stroke-width="1.25"/>'
        '<path d="M3.4 12.6L6.9 9.2L9.6 11.6L11.7 9.8L14.6 12.6" '
        'stroke="currentColor" stroke-width="1.2" stroke-linecap="round" '
        'stroke-linejoin="round" stroke-opacity="0.8"/>'
        '<path d="M12.2 5.2L12.7 6.5L14 7L12.7 7.5L12.2 8.8L11.7 7.5L10.4 7L11.7 6.5Z" '
        'fill="currentColor"/>'
        "</svg>"
    ),
    "engineering": (
        '<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true">'
        '<circle cx="9" cy="9" r="5.6" stroke="currentColor" stroke-width="1.25"/>'
        '<circle cx="9" cy="9" r="2" fill="currentColor"/>'
        '<path d="M9 1.8V3.4M9 14.6V16.2M1.8 9H3.4M14.6 9H16.2" '
        'stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>'
        "</svg>"
    ),
    "character": (
        '<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true">'
        '<circle cx="9" cy="6.6" r="2.7" stroke="currentColor" stroke-width="1.25"/>'
        '<path d="M4.2 14.8C4.8 11.9 6.6 10.6 9 10.6C11.4 10.6 13.2 11.9 13.8 14.8" '
        'stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/>'
        '<path d="M13.6 2.6L14.15 4.05L15.6 4.6L14.15 5.15L13.6 6.6L13.05 5.15L11.6 4.6L13.05 4.05Z" '
        'fill="currentColor"/>'
        "</svg>"
    ),
    "scene": (
        '<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true">'
        '<path d="M2.2 13.8H15.8" stroke="currentColor" stroke-width="1.2" '
        'stroke-linecap="round" stroke-opacity="0.65"/>'
        '<path d="M3 13.6L7.1 8.5L10.3 11.7L12.6 9.3L15.2 13.6" stroke="currentColor" '
        'stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M12.4 3.2L12.95 4.65L14.4 5.2L12.95 5.75L12.4 7.2L11.85 5.75L10.4 5.2L11.85 4.65Z" '
        'fill="currentColor"/>'
        "</svg>"
    ),
    "default": (
        '<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true">'
        '<circle cx="9" cy="9" r="6.2" stroke="currentColor" stroke-width="1.15" '
        'stroke-opacity="0.65"/>'
        '<path d="M9 4.5L9.9 8.1L13.5 9L9.9 9.9L9 13.5L8.1 9.9L4.5 9L8.1 8.1Z" '
        'fill="currentColor"/>'
        "</svg>"
    ),
}


def _render_category_tabs(
    items: list[Any] | int,
    category_stats: list[dict[str, Any]],
    aria_label: str = "文章分类",
) -> str:
    """Render top-level extensible category rail with sliding indicator."""
    total_count = items if isinstance(items, int) else len(items)
    esc_aria = _neutralize_braces(html.escape(aria_label, quote=True))
    tabs: list[str] = [
        '<button type="button" class="category-tab is-active" role="tab" '
        'aria-selected="true" data-filter-category="all">'
        f'<span class="category-tab-icon" aria-hidden="true">{CATEGORY_ICONS["all"]}</span>'
        '<span class="category-tab-label">全部</span>'
        f'<span class="category-tab-count">{total_count}</span>'
        "</button>"
    ]
    for cat in category_stats:
        cat_name = str(cat.get("name", "")).strip()
        if not cat_name:
            continue
        icon_key = str(cat.get("icon") or "default").strip()
        icon_svg = CATEGORY_ICONS.get(icon_key, CATEGORY_ICONS["default"])
        count = int(cat.get("count", 0))
        esc_name = _neutralize_braces(html.escape(cat_name, quote=True))
        tabs.append(
            f'<button type="button" class="category-tab" role="tab" '
            f'aria-selected="false" data-filter-category="{esc_name}">'
            f'<span class="category-tab-icon" aria-hidden="true">{icon_svg}</span>'
            f'<span class="category-tab-label">{esc_name}</span>'
            f'<span class="category-tab-count">{count}</span>'
            "</button>"
        )

    tabs_inner = "\n      ".join(tabs)
    return (
        '<div class="category-bar" data-category-bar>\n'
        f'  <div class="category-tabs" data-category-tabs role="tablist" aria-label="{esc_aria}">\n'
        '    <span class="category-indicator" data-category-indicator aria-hidden="true"></span>\n'
        f"    {tabs_inner}\n"
        "  </div>\n"
        "</div>"
    )


def _render_inline_tag_pills(tags: list[str], route_prefix: str = "/articles/") -> str:
    """Render clickable tag pills (without counts) for cards and post headers."""
    base_route = route_prefix if route_prefix.endswith("/") else f"{route_prefix}/"
    pills: list[str] = []
    for tag in tags:
        href_tag = urllib.parse.quote(tag, safe="")
        esc_tag = _neutralize_braces(html.escape(tag, quote=True))
        pills.append(
            f'<a class="tag-pill" href="{base_route}?tag={href_tag}" '
            f'data-filter-tag="{esc_tag}">{esc_tag}</a>'
        )
    return "\n".join(pills)


def _render_filter_buttons(items: list[Any] | int, tag_stats: list[dict[str, Any]]) -> str:
    """Render archive filter pill buttons for ``all`` plus every tag."""
    total_count = items if isinstance(items, int) else len(items)
    buttons = [
        '<button type="button" class="filter-pill is-active" '
        'data-filter-tag="all" aria-pressed="true">'
        f'全部 <span class="filter-pill-count">{total_count}</span></button>'
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
    category = str(project.get("category") or "").strip()
    esc_cat = _neutralize_braces(html.escape(category, quote=True))
    category_badge_html = (
        f'<button type="button" class="project-category-badge" '
        f'data-filter-category="{esc_cat}">{esc_cat}</button>'
        if category
        else ""
    )
    tags = list(project.get("tags") or project.get("stack") or [])
    tags_csv = str(project.get("tags_csv") or ",".join(tags))
    tags_html = _render_inline_tag_pills(tags, route_prefix="/projects/")

    name_html = render_template("{{name}}", project)
    link_html = ""
    if project["url"]:
        name_html = render_template('<a href="{{url}}">{{name}}</a>', project)
        link_html = render_template('\n    <a class="project-link" href="{{url}}">查看详情 →</a>', project)
    return engine.render_partial(
        "project_card.html",
        {
            "category": category,
            "tags_csv": tags_csv,
            "category_badge_html": category_badge_html,
            "name_html": name_html,
            "status": project["status"],
            "year": project["year"],
            "summary": project["summary"],
            "tags_html": tags_html,
            "link_html": link_html,
        },
    )


def _render_gallery_card(
    engine: TemplateEngine,
    item: dict[str, Any],
    base_path: str = "",
) -> str:
    """Render one gallery prompt+image card using ``partials/gallery_card.html``."""
    category = str(item.get("category") or "").strip()
    esc_cat = _neutralize_braces(html.escape(category, quote=True))
    category_badge_html = (
        f'<button type="button" class="gallery-category-badge" '
        f'data-filter-category="{esc_cat}">{esc_cat}</button>'
        if category
        else ""
    )
    model = str(item.get("model") or "").strip()
    esc_model = _neutralize_braces(html.escape(model, quote=True))
    model_chip_html = (
        f'<span class="gallery-model-chip">{esc_model}</span>'
        if model
        else ""
    )
    tags = list(item.get("tags") or [])
    tags_html = _render_inline_tag_pills(tags, route_prefix="/gallery/")
    image_src = str(item["image"])
    data_image = prefix_url(image_src, base_path)

    return engine.render_partial(
        "gallery_card.html",
        {
            "id": item["id"],
            "title": item["title"],
            "image": image_src,
            "data_image": data_image,
            "prompt": item["prompt"],
            "negative_prompt": item.get("negative_prompt", ""),
            "model": model,
            "params": item.get("params", ""),
            "date": item.get("date", ""),
            "category": category,
            "tags_csv": item.get("tags_csv", ",".join(tags)),
            "category_badge_html": category_badge_html,
            "model_chip_html": model_chip_html,
            "tags_html": tags_html,
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
            "nav_gallery_active": "is-active" if active_nav == "gallery" else "",
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
    project_category_stats: list[dict[str, Any]] = loaded["project_category_stats"]
    project_tag_stats: list[dict[str, Any]] = loaded["project_tag_stats"]
    gallery: list[dict[str, Any]] = loaded["gallery"]
    gallery_category_stats: list[dict[str, Any]] = loaded["gallery_category_stats"]
    gallery_tag_stats: list[dict[str, Any]] = loaded["gallery_tag_stats"]
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
                '<link rel="stylesheet" href="/static/css/home-cover.css?v=10">\n'
                '  <link rel="preload" as="image" href="/static/images/starloop-cover.jpg" fetchpriority="high">'
            ),
            extra_scripts='<script src="/static/js/home-cover.js?v=8" defer></script>',
        ),
    )
    html_pages_count += 1

    # 4. Render Articles Archive: dist/articles/index.html
    empty_stage_svg = (
        '<svg class="empty-stage-mark" viewBox="0 0 88 56" width="88" height="56" fill="none" aria-hidden="true">'
        '<circle cx="44" cy="28" r="21" stroke="var(--gold)" stroke-opacity="0.34" stroke-width="1"/>'
        '<ellipse cx="44" cy="28" rx="38" ry="11" transform="rotate(-14 44 28)" stroke="var(--gold)" stroke-opacity="0.52" stroke-width="1"/>'
        '<path d="M44 19l1.7 4.3 4.3 1.7-4.3 1.7L44 31l-1.7-4.3L38 25l4.3-1.7Z" fill="var(--accent)"/>'
        '</svg>'
    )
    archive_html = (
        engine.render_partial(
            "articles_list.html",
            {
                "total_posts": str(len(posts)),
                "tag_filters_html": _render_filter_buttons(posts, tag_stats),
                "articles_list_html": "\n".join(_render_post_row(engine, post) for post in posts),
            },
        )
        if posts
        else (
            '<div class="empty-stage" aria-live="polite">'
            f'{empty_stage_svg}<p class="search-empty" data-articles-empty>暂无已发布文章。</p>'
            "</div>"
        )
    )
    articles_body = engine.render(
        "articles.html",
        {
            "category_tabs_html": _render_category_tabs(posts, category_stats),
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
                "post_category_url": urllib.parse.quote(post.category, safe=""),
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
    projects_list_html = (
        engine.render_partial(
            "projects_list.html",
            {
                "total_projects": str(len(projects)),
                "tag_filters_html": _render_filter_buttons(projects, project_tag_stats),
                "projects_cards_html": "\n".join(
                    _render_project_card(engine, project) for project in projects
                ),
            },
        )
        if projects
        else (
            '<div class="empty-stage" aria-live="polite">'
            f'{empty_stage_svg}<p class="search-empty" data-projects-empty data-filter-empty>暂无已发布项目。</p>'
            "</div>"
        )
    )
    projects_body = engine.render(
        "projects.html",
        {
            "category_tabs_html": _render_category_tabs(
                projects, project_category_stats, aria_label="项目分类"
            ),
            "projects_list_html": projects_list_html,
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

    # 7. Render Gallery Page: dist/gallery/index.html
    gallery_html = (
        engine.render_partial(
            "gallery_list.html",
            {
                "total_gallery": str(len(gallery)),
                "tag_filters_html": _render_filter_buttons(gallery, gallery_tag_stats),
                "gallery_cards_html": "\n".join(
                    _render_gallery_card(engine, item, base_path=normalized_base_path)
                    for item in gallery
                ),
            },
        )
        if gallery
        else (
            '<div class="empty-stage" aria-live="polite">'
            f'{empty_stage_svg}<p class="search-empty" data-gallery-empty data-filter-empty>暂无已发布图像。</p>'
            "</div>"
        )
    )
    gallery_body = engine.render(
        "gallery.html",
        {
            "category_tabs_html": _render_category_tabs(
                gallery, gallery_category_stats, aria_label="图像分类"
            ),
            "gallery_html": gallery_html,
        },
    )
    _write_html(
        out_dir / "gallery" / "index.html",
        _wrap_base(
            engine,
            site,
            page_title=f"图像 · {site['site_title']}",
            page_description=f"{site['author_name']} 的图像生成作品与提示词画廊。",
            route_path="/gallery/",
            active_nav="gallery",
            page_content=gallery_body,
            base_path=normalized_base_path,
        ),
    )
    html_pages_count += 1

    # 8. Render About Page: dist/about/index.html
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

    # 9. Render 404 Page: dist/404.html
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

    # 10. Write JSON APIs, RSS 2.0, Sitemap XML, robots.txt
    feed_paths = write_feeds(
        out_dir,
        site,
        posts,
        tag_stats,
        category_stats,
        base_path=normalized_base_path,
        projects=projects,
        project_tag_stats=project_tag_stats,
        project_category_stats=project_category_stats,
        gallery=gallery,
        gallery_tag_stats=gallery_tag_stats,
        gallery_category_stats=gallery_category_stats,
    )

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "dist_dir": str(out_dir),
        "base_path": normalized_base_path,
        "has_cname": has_cname,
        "posts_count": len(posts),
        "projects_count": len(projects),
        "gallery_count": len(gallery),
        "categories_count": len(category_stats),
        "tags_count": len(tag_stats),
        "html_pages_count": html_pages_count,
        "static_files_count": static_files_count,
        "feed_files_count": len(feed_paths),
        "elapsed_ms": round(elapsed_ms, 2),
    }
