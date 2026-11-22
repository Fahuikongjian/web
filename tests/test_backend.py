"""Unit and integration tests for the backend content, Markdown, renderer, feeds, and server."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import threading
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.content_loader import (  # noqa: E402
    count_words,
    estimate_reading_time,
    load_all_content,
    load_posts,
    parse_frontmatter,
)
from backend.feeds import build_robots_txt, build_rss_xml, build_sitemap_xml  # noqa: E402
from backend.markdown_engine import render_markdown, render_toc_html  # noqa: E402
from backend.renderer import (  # noqa: E402
    PLACEHOLDER_RE,
    apply_base_path_to_html,
    normalize_base_path,
    render_site,
    render_template,
)
from scripts.build import main as build_cli_main  # noqa: E402
from scripts.check import check_json_and_posts, check_xml_files  # noqa: E402
from scripts.serve import create_server  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Frontmatter & Content Loader Tests
# ---------------------------------------------------------------------------


def test_parse_frontmatter_inline_and_multiline_lists() -> None:
    raw = (
        "\ufeff---\r\n"
        'title: "测试：Frontmatter 解析"\r\n'
        "slug: test-frontmatter\r\n"
        "date: 2026-11-20\r\n"
        "featured: true\r\n"
        "draft: FALSE\r\n"
        'flag_text: "true"\r\n'
        'tags: [Python, "设计, 系统", 独立博客]\r\n'
        "categories:\r\n"
        "  - 系统架构\r\n"
        "  - '排版'\r\n"
        "---\r\n"
        "\r\n"
        "正文第一段。\r\n"
    )
    meta, body = parse_frontmatter(raw)
    assert meta["title"] == "测试：Frontmatter 解析"
    assert meta["slug"] == "test-frontmatter"
    assert meta["date"] == "2026-11-20"
    assert meta["featured"] is True
    assert meta["draft"] is False
    assert meta["flag_text"] == "true"
    assert meta["tags"] == ["Python", "设计, 系统", "独立博客"]
    assert meta["categories"] == ["系统架构", "排版"]
    assert body.strip() == "正文第一段。"


def test_parse_frontmatter_without_header_and_unclosed_error() -> None:
    meta, body = parse_frontmatter("## 纯 Markdown\n\n无头部。")
    assert meta == {}
    assert body.startswith("## 纯 Markdown")

    with pytest.raises(ValueError, match="Unclosed frontmatter"):
        parse_frontmatter("---\ntitle: broken\n正文")


def test_word_count_and_reading_time() -> None:
    assert count_words("") == 0
    assert estimate_reading_time(0) == 1
    assert count_words("你好世界 hello world") == 6
    assert estimate_reading_time(350) == 1
    assert estimate_reading_time(351) == 2
    assert estimate_reading_time(1050) == 3


def test_load_posts_filters_drafts_sorts_desc_and_computes_neighbors(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    posts_dir = content_dir / "posts"
    posts_dir.mkdir(parents=True)

    (posts_dir / "a.md").write_text(
        "---\ntitle: Older\nslug: older\ndate: 2026-10-01\ncategory: CatA\ntags: [t1, t2]\ndraft: false\n---\n\n旧文章。",
        encoding="utf-8",
    )
    (posts_dir / "b.md").write_text(
        "---\ntitle: Newer\nslug: newer\ndate: 2026-11-10\ncategory: CatA\ntags: [t1]\ndraft: false\n---\n\n新文章。",
        encoding="utf-8",
    )
    (posts_dir / "c.md").write_text(
        "---\ntitle: Middle\nslug: middle\ndate: 2026-11-01\ncategory: CatB\ntags: [t2]\ndraft: false\n---\n\n中文章。",
        encoding="utf-8",
    )
    (posts_dir / "d.md").write_text(
        "---\ntitle: Secret Draft\nslug: secret\ndate: 2026-12-01\ncategory: CatA\ntags: [t1]\ndraft: true\n---\n\n草稿。",
        encoding="utf-8",
    )

    posts = load_posts(content_dir)
    assert [p.slug for p in posts] == ["newer", "middle", "older"]

    newest, middle, oldest = posts
    assert newest.prev_post is None
    assert newest.next_post is not None and newest.next_post["slug"] == "middle"
    assert middle.prev_post is not None and middle.prev_post["slug"] == "newer"
    assert middle.next_post is not None and middle.next_post["slug"] == "older"
    assert oldest.next_post is None
    # Newest shares tag t1 + category CatA with older, so older ranks first in related
    assert newest.related_posts[0]["slug"] == "older"


def test_load_real_content_repository() -> None:
    loaded = load_all_content(PROJECT_ROOT / "content")
    assert loaded["site"]["site_title"] == "ASTRA YAO · 星环手记"
    assert loaded["site"]["site_url"] == "https://astrayao.xyz"
    assert len(loaded["projects"]) >= 4
    dates = [p.date for p in loaded["posts"]]
    assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# 2. Markdown Engine Tests
# ---------------------------------------------------------------------------


def test_markdown_headings_unique_ids_and_toc() -> None:
    md = (
        "# 一级标题\n\n"
        "## 章节 A\n\n"
        "### 子节 `Code`\n\n"
        "## 章节 A\n\n"
        "#### 四级标题\n"
    )
    body_html, toc = render_markdown(md)
    assert [item["level"] for item in toc] == [2, 3, 2]
    assert [item["id"] for item in toc] == ["章节-a", "子节-code", "章节-a-2"]
    assert [item["text"] for item in toc] == ["章节 A", "子节 Code", "章节 A"]
    assert '<h2 id="章节-a">' in body_html
    assert '<h2 id="章节-a-2">' in body_html
    assert '<h4 id="四级标题">' in body_html

    toc_html = render_toc_html(toc)
    assert 'class="toc-nav"' in toc_html
    assert 'href="#章节-a-2"' in toc_html
    assert 'data-level="3"' in toc_html

    empty_toc_html = render_toc_html([])
    assert "toc-empty" in empty_toc_html


def test_markdown_code_blocks_pygments_and_fallback() -> None:
    md = (
        "```python\n"
        "def greet(name):\n"
        "    return f'hi {name}'\n"
        "```\n\n"
        "```unknownlang99\n"
        "raw text <tag>\n"
        "```\n"
    )
    body_html, _ = render_markdown(md)
    assert body_html.count('class="code-block-wrapper"') == 2
    assert '<span class="code-lang">python</span>' in body_html
    assert '<button type="button" class="code-copy-btn" aria-label="复制代码">复制</button>' in body_html
    assert '<div class="highlight"><pre>' in body_html
    assert '<span class="code-lang">unknownlang99</span>' in body_html
    assert "&lt;tag&gt;" in body_html


def test_markdown_table_blockquote_lists_hr_and_inline_protection() -> None:
    md = (
        "| 列一 | 列二 | 列三 |\n"
        "| :--- | :---: | ---: |\n"
        "| `a_b` | **粗体** | *斜体* |\n\n"
        "> 第一行引用\n"
        "> 第二行引用\n\n"
        "- 无序一\n"
        "  1. 嵌套有序\n"
        "- 无序二\n\n"
        "---\n\n"
        "行内代码保护 `*not_italic*` 与 `snake_case_var` 以及图片 ![示例](/static/images/cover-01.svg) 和 [链接](/articles/)。\n"
    )
    html_out, _ = render_markdown(md)
    assert '<div class="table-wrap"><table>' in html_out
    assert '<th style="text-align:left">列一</th>' in html_out
    assert '<th style="text-align:center">列二</th>' in html_out
    assert '<th style="text-align:right">列三</th>' in html_out
    assert "<code>a_b</code>" in html_out
    assert "<strong>粗体</strong>" in html_out
    assert "<em>斜体</em>" in html_out
    assert "<blockquote>\n<p>第一行引用 第二行引用</p>\n</blockquote>" in html_out
    assert "<ul>" in html_out and "<ol>" in html_out
    assert "<hr>" in html_out
    assert "<code>*not_italic*</code>" in html_out
    assert "snake_case_var" in html_out and "<em>case</em>" not in html_out
    assert '<img src="/static/images/cover-01.svg" alt="示例" loading="lazy">' in html_out
    assert '<a href="/articles/">链接</a>' in html_out


def test_markdown_xss_escaping_and_placeholder_neutralization() -> None:
    md = (
        '危险脚本 <script>alert("xss")</script> 和 <img src=x onerror=alert(1)>。\n\n'
        "危险链接 [点击](javascript:alert(1)) 与 ![坏图](javascript:alert(2))。\n\n"
        "模板字面量 `{{secret_key}}` 与 {{another_key}}。\n"
    )
    html_out, _ = render_markdown(md)
    assert "<script>" not in html_out
    assert "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;" in html_out
    assert "<img src=x" not in html_out
    assert "javascript:" not in html_out
    assert "点击" in html_out
    assert not PLACEHOLDER_RE.search(html_out)


# ---------------------------------------------------------------------------
# 3. Renderer, Feeds, Build & Serve Tests
# ---------------------------------------------------------------------------


def test_template_renderer_single_pass_and_escaping() -> None:
    tpl = "<title>{{title}}</title><div>{{body_html}}</div>"
    rendered = render_template(tpl, {"title": "A & <B>", "body_html": "<p>{{not_expanded}}</p>"})
    assert rendered == "<title>A &amp; &lt;B&gt;</title><div><p>{{not_expanded}}</p></div>"

    with pytest.raises(KeyError):
        render_template("{{missing_key}}", {})


def test_feeds_xml_escaping_and_validity(populated_site_root: Path) -> None:
    site = {
        "site_title": "测试 & 站点 <1>",
        "site_tagline": "副标题 & 描述",
        "site_url": "https://example.com",
    }
    posts = load_posts(populated_site_root / "content")
    rss_xml = build_rss_xml(site, posts)
    rss_root = ET.fromstring(rss_xml)
    assert rss_root.tag == "rss"
    channel = rss_root.find("channel")
    assert channel is not None
    assert channel.findtext("title") == "测试 & 站点 <1>"
    assert len(channel.findall("item")) == len(posts)

    sitemap_xml = build_sitemap_xml(site, posts)
    sm_root = ET.fromstring(sitemap_xml)
    assert sm_root.tag.endswith("urlset")
    assert len(list(sm_root)) == 4 + len(posts)

    robots = build_robots_txt(site)
    assert "Sitemap: https://example.com/sitemap.xml" in robots


def test_full_build_completeness_and_valid_artifacts(tmp_path: Path, populated_site_root: Path) -> None:
    dist_dir = tmp_path / "dist"
    stats = render_site(populated_site_root, dist_dir=dist_dir, clean=True)
    assert stats["posts_count"] == 2
    assert stats["html_pages_count"] == 7

    expected_paths = [
        ".nojekyll",
        "index.html",
        "articles/index.html",
        "projects/index.html",
        "about/index.html",
        "404.html",
        "api/posts.json",
        "api/search-index.json",
        "rss.xml",
        "sitemap.xml",
        "robots.txt",
        "static/css/tokens.css",
        "static/js/search.js",
        "static/images/starloop-cover.jpg",
        "static/images/astra-portrait.jpg",
        "static/images/author-mark.svg",
        "static/images/favicon.svg",
        "static/images/cover-01.svg",
        "static/images/cover-02.svg",
        "static/images/cover-03.svg",
        "static/images/cover-04.svg",
        "static/images/cover-05.svg",
    ]
    for rel in expected_paths:
        assert (dist_dir / rel).is_file(), f"Missing built file: {rel}"
    assert not (dist_dir / "static/images/astra-hero.jpg").exists()
    assert not (dist_dir / "static/images/astra-hero-cover.jpg").exists()

    posts_api = json.loads((dist_dir / "api" / "posts.json").read_text(encoding="utf-8"))
    assert posts_api["total"] == 2
    assert len(posts_api["posts"]) == 2
    assert len(posts_api["tags"]) > 0

    search_index = json.loads((dist_dir / "api" / "search-index.json").read_text(encoding="utf-8"))
    assert len(search_index) == 2
    for item in search_index:
        for field in (
            "title",
            "slug",
            "url",
            "date",
            "category",
            "tags",
            "summary",
            "excerpt",
            "reading_time",
        ):
            assert field in item
        assert (dist_dir / "articles" / item["slug"] / "index.html").is_file()

    ET.fromstring((dist_dir / "rss.xml").read_text(encoding="utf-8"))
    ET.fromstring((dist_dir / "sitemap.xml").read_text(encoding="utf-8"))

    assert stats["base_path"] == ""
    assert stats["has_cname"] is False
    assert not (dist_dir / "CNAME").exists()
    assert (dist_dir / ".nojekyll").read_text(encoding="utf-8") == ""

    home_html = (dist_dir / "index.html").read_text(encoding="utf-8")
    assert '<meta name="site-base-path" content="">' in home_html
    assert "沪ICP备" not in home_html
    assert 'id="section-featured"' in home_html
    assert 'id="section-recent"' in home_html
    assert 'id="section-topics"' in home_html
    assert '<a class="project-link" href="/articles/build-fixture/">' in home_html

    for html_file in dist_dir.rglob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        assert not PLACEHOLDER_RE.findall(text), f"Unreplaced placeholder in {html_file}"


def test_clean_build_removes_published_articles_and_feeds(
    tmp_path: Path, populated_site_root: Path, empty_site_root: Path
) -> None:
    dist_dir = tmp_path / "dist"
    render_site(populated_site_root, dist_dir=dist_dir, clean=True)
    assert (dist_dir / "articles" / "build-fixture" / "index.html").is_file()

    stats = render_site(empty_site_root, dist_dir=dist_dir, clean=True)
    assert stats["posts_count"] == 0
    assert stats["html_pages_count"] == 5
    assert list((dist_dir / "articles").glob("*/index.html")) == []
    assert check_json_and_posts(dist_dir, content_dir=empty_site_root / "content") == ([], 0, 0)
    assert check_xml_files(dist_dir, posts_count=0) == []
    assert "build-fixture" not in (dist_dir / "sitemap.xml").read_text(encoding="utf-8")
    assert "暂无已发布文章。" in (dist_dir / "articles" / "index.html").read_text(encoding="utf-8")
    home = (dist_dir / "index.html").read_text(encoding="utf-8")
    assert 'id="section-featured"' not in home
    assert 'id="section-recent"' not in home
    assert 'id="section-topics"' not in home
    assert 'id="section-projects"' in home


def test_normalize_base_path_and_html_rewriting() -> None:
    assert normalize_base_path(None) == ""
    assert normalize_base_path("") == ""
    assert normalize_base_path("/") == ""
    assert normalize_base_path("/astrayao-blog/") == "/astrayao-blog"
    assert normalize_base_path("astrayao-blog") == "/astrayao-blog"

    sample = (
        '<link rel="stylesheet" href="/static/css/tokens.css">'
        '<a href="/">Home</a>'
        '<a href="/articles/?tag=CSS">CSS</a>'
        '<a href="/astrayao-blog/about/">AlreadyPrefixed</a>'
        '<a href="https://github.com/astrayao">Ext</a>'
        '<a href="//cdn.example.com/app.js">ProtoRel</a>'
        '<div data-src="/should-not-touch"></div>'
        '<code>&lt;a href="/inside-inline-code"&gt;</code>'
        '<pre><span class="s">href="/inside-pre-code"</span> <img src="/raw-in-pre.png"></pre>'
    )
    out = apply_base_path_to_html(sample, "/astrayao-blog")
    assert 'href="/astrayao-blog/static/css/tokens.css"' in out
    assert 'href="/astrayao-blog/"' in out
    assert 'href="/astrayao-blog/articles/?tag=CSS"' in out
    assert 'href="/astrayao-blog/about/"' in out
    assert "/astrayao-blog/astrayao-blog" not in out
    assert 'href="https://github.com/astrayao"' in out
    assert 'href="//cdn.example.com/app.js"' in out
    assert 'data-src="/should-not-touch"' in out
    assert '<code>&lt;a href="/inside-inline-code"&gt;</code>' in out
    assert 'href="/inside-pre-code"' in out
    assert 'src="/raw-in-pre.png"' in out


def test_github_pages_subpath_and_cname_build(tmp_path: Path, populated_site_root: Path) -> None:
    subpath_dist = tmp_path / "dist-subpath"
    stats = render_site(
        populated_site_root,
        dist_dir=subpath_dist,
        clean=True,
        base_path="/astrayao-blog",
        site_url="https://example.github.io/astrayao-blog",
    )
    assert stats["base_path"] == "/astrayao-blog"
    assert stats["has_cname"] is False
    assert (subpath_dist / ".nojekyll").is_file()
    assert not (subpath_dist / "CNAME").exists()

    home_html = (subpath_dist / "index.html").read_text(encoding="utf-8")
    assert '<meta name="site-base-path" content="/astrayao-blog">' in home_html
    assert 'href="/astrayao-blog/static/css/tokens.css"' in home_html
    assert 'src="/astrayao-blog/static/js/search.js?v=3"' in home_html
    assert 'rel="preload" as="image" href="/astrayao-blog/static/images/starloop-cover.jpg"' in home_html
    assert 'href="/astrayao-blog/articles/"' in home_html
    assert 'href="https://example.github.io/astrayao-blog/"' in home_html
    assert "/astrayao-blog/astrayao-blog/" not in home_html

    post_html = (
        subpath_dist / "articles" / "deployment-fixture" / "index.html"
    ).read_text(encoding="utf-8")
    # Ensure code snippets inside <pre> are not corrupted by subpath rewriting
    assert "/var/www/test-site/dist" in post_html
    assert "/astrayao-blog/var/www" not in post_html

    search_index = json.loads(
        (subpath_dist / "api" / "search-index.json").read_text(encoding="utf-8")
    )
    assert all(item["url"].startswith("/astrayao-blog/articles/") for item in search_index)

    posts_api = json.loads(
        (subpath_dist / "api" / "posts.json").read_text(encoding="utf-8")
    )
    assert all(p["url"].startswith("/astrayao-blog/articles/") for p in posts_api["posts"])
    assert all(p["cover"].startswith("/astrayao-blog/static/") for p in posts_api["posts"])

    rss_text = (subpath_dist / "rss.xml").read_text(encoding="utf-8")
    assert "https://example.github.io/astrayao-blog/articles/" in rss_text
    assert "/astrayao-blog/astrayao-blog/" not in rss_text
    ET.fromstring(rss_text)

    sitemap_text = (subpath_dist / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://example.github.io/astrayao-blog/articles/" in sitemap_text
    assert "/astrayao-blog/astrayao-blog/" not in sitemap_text
    ET.fromstring(sitemap_text)

    robots_text = (subpath_dist / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://example.github.io/astrayao-blog/sitemap.xml" in robots_text

    # CNAME generation via CLI flags
    cname_dist = tmp_path / "dist-cname"
    rc = build_cli_main(
        [
            "--root",
            str(PROJECT_ROOT),
            "--dist",
            str(cname_dist),
            "--site-url",
            "https://astrayao.com",
            "--cname",
            "https://astrayao.com/",
        ]
    )
    assert rc == 0
    assert (cname_dist / ".nojekyll").is_file()
    assert (cname_dist / "CNAME").read_text(encoding="utf-8") == "astrayao.com\n"


def test_preview_server_serves_pages_and_custom_404(tmp_path: Path, populated_site_root: Path) -> None:
    dist_dir = tmp_path / "dist"
    render_site(populated_site_root, dist_dir=dist_dir, clean=True)

    server = create_server(host="127.0.0.1", port=0, directory=dist_dir)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    try:
        base = f"http://127.0.0.1:{port}"
        with opener.open(f"{base}/") as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")
            home_html = resp.read().decode("utf-8")
            assert "ASTRA YAO · 星环手记" in home_html
            assert "/static/images/starloop-cover.jpg" in home_html

        with opener.open(f"{base}/articles/build-fixture/") as resp:
            assert resp.status == 200
            assert "测试样例（设计）" in resp.read().decode("utf-8")

        with opener.open(f"{base}/static/css/tokens.css") as resp:
            assert resp.status == 200
            assert "text/css" in resp.headers.get("Content-Type", "")

        with opener.open(f"{base}/static/images/starloop-cover.jpg") as resp:
            assert resp.status == 200
            assert "image/jpeg" in resp.headers.get("Content-Type", "")

        with opener.open(f"{base}/api/search-index.json") as resp:
            assert resp.status == 200
            assert "application/json" in resp.headers.get("Content-Type", "")
            assert len(json.loads(resp.read().decode("utf-8"))) == 2

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            opener.open(f"{base}/non-existent-page-404/")
        err = exc_info.value
        assert err.code == 404
        body = err.read().decode("utf-8")
        assert "404" in body
        assert "这一段星环旋律似乎尚未灌录" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
