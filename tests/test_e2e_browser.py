from __future__ import annotations

import functools
import http.server
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
CHROME_EXECUTABLE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEFAULT_BRAIN_DIR = Path(
    r"C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e"
)


def _try_ensure_writable_dir(path: Path) -> bool:
    """Create directory if needed and verify write/delete permission."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".qa-write-probe-{os.getpid()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def get_screenshot_dir() -> Path:
    """Resolve a writable output directory for visual QA screenshots."""
    env_dir = os.environ.get("QA_SCREENSHOT_DIR")
    if env_dir:
        path = Path(env_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
    if _try_ensure_writable_dir(DEFAULT_BRAIN_DIR):
        return DEFAULT_BRAIN_DIR
    return Path(tempfile.mkdtemp(prefix="qa-screenshots-"))


class DistStaticHandler(http.server.SimpleHTTPRequestHandler):
    """Static HTTP handler serving dist/ with explicit MIME types and custom 404."""

    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        "": "application/octet-stream",
        ".html": "text/html; charset=utf-8",
        ".htm": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".mjs": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".xml": "application/xml; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".ico": "image/x-icon",
    }

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        if code == HTTPStatus.NOT_FOUND:
            not_found_path = Path(self.directory) / "404.html"
            if not_found_path.is_file():
                body = not_found_path.read_bytes()
                self.send_response(HTTPStatus.NOT_FOUND)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)
                return
        super().send_error(code, message, explain)

    def log_message(self, format: str, *args: object) -> None:
        return


class QuietThreadingHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class SubpathDistHandler(DistStaticHandler):
    """Strict subpath mount handler: only serves files under /astrayao-blog/."""

    mount_prefix = "/astrayao-blog"

    def send_head(self):
        parsed = urlsplit(self.path)
        req_path = parsed.path
        if req_path == self.mount_prefix:
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", f"{self.mount_prefix}/")
            self.end_headers()
            return None
        prefix_slash = f"{self.mount_prefix}/"
        if req_path.startswith(prefix_slash):
            stripped = req_path[len(self.mount_prefix) :] or "/"
            self.path = f"{stripped}?{parsed.query}" if parsed.query else stripped
            return super().send_head()
        http.server.SimpleHTTPRequestHandler.send_error(
            self, HTTPStatus.NOT_FOUND, "Not mounted under subpath"
        )
        return None


@pytest.fixture(scope="module")
def static_server() -> str:
    """Start an in-process static HTTP server for dist/ and shut it down cleanly."""
    if not DIST_DIR.is_dir() or not (DIST_DIR / "index.html").is_file():
        pytest.fail(f"dist/ build output not found at {DIST_DIR}. Run scripts/build.py first.")

    handler = functools.partial(DistStaticHandler, directory=str(DIST_DIR))
    server = QuietThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def browser() -> Browser:
    """Launch local Google Chrome via Playwright."""
    if not Path(CHROME_EXECUTABLE).is_file():
        pytest.fail(f"Local Chrome executable not found at {CHROME_EXECUTABLE}")

    with sync_playwright() as p:
        launched = p.chromium.launch(executable_path=CHROME_EXECUTABLE, headless=True)
        try:
            yield launched
        finally:
            launched.close()


def _attach_error_collectors(page: Page) -> dict[str, list]:
    records: dict[str, list] = {
        "console_errors": [],
        "page_errors": [],
        "failed_responses": [],
        "request_failures": [],
    }
    page.on(
        "console",
        lambda msg: records["console_errors"].append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: records["page_errors"].append(str(err)))
    page.on(
        "response",
        lambda resp: records["failed_responses"].append((resp.status, resp.url))
        if resp.status >= 400
        else None,
    )
    page.on(
        "requestfailed",
        lambda req: records["request_failures"].append((req.url, str(req.failure))),
    )
    return records


def _assert_clean_page(records: dict[str, list], context_label: str) -> None:
    assert records["console_errors"] == [], f"{context_label} console errors: {records['console_errors']}"
    assert records["page_errors"] == [], f"{context_label} page errors: {records['page_errors']}"
    assert records["failed_responses"] == [], f"{context_label} HTTP >=400: {records['failed_responses']}"
    assert records["request_failures"] == [], f"{context_label} requestfailed: {records['request_failures']}"


def _load_post_routes() -> list[str]:
    posts_json = DIST_DIR / "api" / "posts.json"
    assert posts_json.is_file(), f"Missing {posts_json}"
    payload = json.loads(posts_json.read_text(encoding="utf-8"))
    posts = payload.get("posts", [])
    assert len(posts) >= 5, f"Expected at least 5 posts in posts.json, got {len(posts)}"
    return [post["url"] for post in posts]


def _assert_no_horizontal_overflow(page: Page, route: str, viewport_name: str) -> None:
    dims = page.evaluate(
        "() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth })"
    )
    assert dims["scrollWidth"] <= dims["clientWidth"], (
        f"Horizontal overflow on {route} ({viewport_name}): "
        f"scrollWidth={dims['scrollWidth']} > clientWidth={dims['clientWidth']}"
    )


def _assert_images_loaded(page: Page, route: str) -> None:
    broken = page.evaluate(
        """() => {
            const imgs = Array.from(document.querySelectorAll('img'));
            return imgs
              .filter(img => !img.complete || img.naturalWidth === 0)
              .map(img => img.getAttribute('src') || '(no src)');
        }"""
    )
    assert broken == [], f"Broken images on {route}: {broken}"


def test_routes_zero_errors_and_responsive_viewports(browser: Browser, static_server: str) -> None:
    post_routes = _load_post_routes()
    routes = ["/", "/articles/", "/projects/", "/about/", *post_routes]

    for viewport_name, viewport in [
        ("desktop-1440x900", {"width": 1440, "height": 900}),
        ("mobile-390x844", {"width": 390, "height": 844}),
    ]:
        context = browser.new_context(viewport=viewport)
        page = context.new_page()
        records = _attach_error_collectors(page)
        try:
            for route in routes:
                response = page.goto(f"{static_server}{route}", wait_until="networkidle")
                assert response is not None, f"No response for {route}"
                assert response.status == 200, f"Expected 200 on {route}, got {response.status}"
                assert "{{" not in page.content(), f"Unreplaced template placeholder found on {route}"
                _assert_no_horizontal_overflow(page, route, viewport_name)
                _assert_images_loaded(page, route)

            if viewport_name == "mobile-390x844":
                page.goto(f"{static_server}/", wait_until="networkidle")
                drawer = page.locator("[data-mobile-drawer]")
                toggle = page.locator("[data-mobile-menu-toggle]")
                assert toggle.is_visible()
                toggle.click()
                assert "is-open" in (drawer.get_attribute("class") or "")
                page.keyboard.press("Escape")
                assert "is-open" not in (drawer.get_attribute("class") or "")

            _assert_clean_page(records, viewport_name)
        finally:
            context.close()


def test_custom_404_page_and_assets(browser: Browser, static_server: str) -> None:
    for viewport_name, viewport in [
        ("desktop-1440x900", {"width": 1440, "height": 900}),
        ("mobile-390x844", {"width": 390, "height": 844}),
    ]:
        context = browser.new_context(viewport=viewport)
        page = context.new_page()
        records = _attach_error_collectors(page)
        try:
            response = page.goto(
                f"{static_server}/non-existent-page-404/",
                wait_until="networkidle",
            )
            assert response is not None
            assert response.status == 404, f"Expected 404 status, got {response.status}"
            error_section = page.locator(".error-page")
            assert error_section.is_visible()
            assert "404" in error_section.inner_text()
            _assert_no_horizontal_overflow(page, "/non-existent-page-404/", viewport_name)

            assert records["page_errors"] == [], f"404 page errors: {records['page_errors']}"
            assert records["request_failures"] == [], f"404 requestfailed: {records['request_failures']}"
            non_doc_failures = [
                (status, url)
                for status, url in records["failed_responses"]
                if not url.endswith("/non-existent-page-404/")
            ]
            assert non_doc_failures == [], f"Subresource failures on 404 page: {non_doc_failures}"
        finally:
            context.close()


def test_theme_toggle_and_persistence(browser: Browser, static_server: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="light")
    page = context.new_page()
    records = _attach_error_collectors(page)
    try:
        page.goto(f"{static_server}/", wait_until="networkidle")
        assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"

        page.locator("[data-theme-toggle]").click()
        assert page.evaluate("() => document.documentElement.dataset.theme") == "light"
        assert page.evaluate("() => localStorage.getItem('blog-theme')") == "light"

        page.reload(wait_until="networkidle")
        assert page.evaluate("() => document.documentElement.dataset.theme") == "light"

        page.locator("[data-theme-toggle]").click()
        assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"
        assert page.evaluate("() => localStorage.getItem('blog-theme')") == "dark"

        _assert_clean_page(records, "theme-toggle")
    finally:
        context.close()


def test_vinyl_stage_toggle_and_astra_assets(browser: Browser, static_server: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    records = _attach_error_collectors(page)
    try:
        page.goto(f"{static_server}/", wait_until="networkidle")
        hero_img = page.locator('img[src="/static/images/astra-hero.jpg"]')
        assert hero_img.count() == 1 and hero_img.is_visible()
        assert hero_img.evaluate("img => img.complete && img.naturalWidth > 0")

        stage = page.locator("[data-vinyl-stage]")
        toggle = page.locator("[data-vinyl-toggle]")
        label = page.locator("[data-vinyl-toggle-label]")
        assert stage.is_visible() and toggle.is_visible()
        assert "is-paused" not in (stage.get_attribute("class") or "")
        assert toggle.get_attribute("aria-pressed") == "false"
        assert label.inner_text().strip() == "旋转中"

        toggle.click()
        assert "is-paused" in (stage.get_attribute("class") or "")
        assert toggle.get_attribute("aria-pressed") == "true"
        assert label.inner_text().strip() == "已暂停"

        toggle.click()
        assert "is-paused" not in (stage.get_attribute("class") or "")
        assert toggle.get_attribute("aria-pressed") == "false"
        assert label.inner_text().strip() == "旋转中"

        page.goto(f"{static_server}/about/", wait_until="networkidle")
        portrait_img = page.locator('.about-portrait-frame img[src="/static/images/astra-portrait.jpg"]')
        assert portrait_img.count() == 1 and portrait_img.is_visible()
        assert portrait_img.evaluate("img => img.complete && img.naturalWidth > 0")

        _assert_clean_page(records, "vinyl-and-astra-assets")
    finally:
        context.close()


def test_search_modal_shortcut_and_results(browser: Browser, static_server: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    records = _attach_error_collectors(page)
    try:
        page.goto(f"{static_server}/", wait_until="networkidle")
        modal = page.locator("[data-search-modal]")
        search_input = page.locator("[data-search-input]")
        results = page.locator("[data-search-results]")

        assert not modal.is_visible()
        page.keyboard.press("Control+k")
        modal.wait_for(state="visible")
        assert modal.is_visible()

        for keyword in ["设计", "服务器"]:
            search_input.fill(keyword)
            items = results.locator(".search-result-item")
            items.first.wait_for(state="visible")
            assert items.count() >= 1, f"Expected search results for '{keyword}'"
            assert results.locator("mark.search-highlight").count() >= 1

        page.keyboard.press("Escape")
        modal.wait_for(state="hidden")
        assert not modal.is_visible()

        _assert_clean_page(records, "search-modal")
    finally:
        context.close()


def test_articles_tag_filtering(browser: Browser, static_server: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    records = _attach_error_collectors(page)
    try:
        page.goto(f"{static_server}/articles/", wait_until="networkidle")
        all_rows = page.locator("[data-articles-list] [data-tags]")
        total_count = all_rows.count()
        assert total_count >= 5

        tag_buttons = page.locator('.filter-pills [data-filter-tag]:not([data-filter-tag="all"])')
        assert tag_buttons.count() >= 1

        chosen_tag = None
        expected_count = None
        for idx in range(tag_buttons.count()):
            btn = tag_buttons.nth(idx)
            tag_name = btn.get_attribute("data-filter-tag")
            count_text = btn.locator(".filter-pill-count").inner_text().strip()
            if count_text.isdigit() and 0 < int(count_text) < total_count:
                chosen_tag = tag_name
                expected_count = int(count_text)
                btn.click()
                break

        assert chosen_tag is not None and expected_count is not None, "No subset tag button found"

        visible_rows = page.locator("[data-articles-list] [data-tags]:visible")
        assert visible_rows.count() == expected_count
        assert f"tag={chosen_tag}" in unquote(page.url)

        page.locator('.filter-pills [data-filter-tag="all"]').click()
        assert visible_rows.count() == total_count

        # Verify query param initialization when arriving directly from home tag pill
        page.goto(f"{static_server}/articles/?tag={quote(chosen_tag)}", wait_until="networkidle")
        assert page.locator("[data-articles-list] [data-tags]:visible").count() == expected_count

        _assert_clean_page(records, "tag-filter")
    finally:
        context.close()


def test_post_reading_experience(browser: Browser, static_server: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    records = _attach_error_collectors(page)
    try:
        page.goto(f"{static_server}/articles/python-static-architecture/", wait_until="networkidle")

        toc_links = page.locator(".toc-nav .toc-list .toc-link[href^='#']")
        assert toc_links.count() >= 2, "Expected TOC anchor links on post page"

        progress_bar = page.locator("[data-reading-progress]")
        assert progress_bar.count() == 1

        copy_btn = page.locator(".code-copy-btn").first
        assert copy_btn.is_visible()
        initial_label = copy_btn.inner_text().strip()
        copy_btn.click()
        page.locator(".code-copy-btn.is-copied").first.wait_for(state="visible")
        updated_label = copy_btn.inner_text().strip()
        assert updated_label != initial_label, "Expected copy button text to change on click"

        # Scroll partway through the post and verify reading progress and TOC active state
        page.evaluate("() => window.scrollTo({ top: 750, behavior: 'instant' })")
        page.wait_for_timeout(150)
        progress_width = page.evaluate(
            "() => parseFloat(document.querySelector('[data-reading-progress]').style.width || '0')"
        )
        assert progress_width > 0, f"Expected reading progress > 0 after scroll, got {progress_width}"
        assert page.locator(".toc-nav .toc-link.is-active").count() == 1

        _assert_clean_page(records, "post-reading")
    finally:
        context.close()


def test_capture_visual_acceptance_screenshots(browser: Browser, static_server: str) -> None:
    screenshot_dir = get_screenshot_dir()
    desktop_viewport = {"width": 1440, "height": 900}
    mobile_viewport = {"width": 390, "height": 844}

    context = browser.new_context(viewport=desktop_viewport)
    page = context.new_page()
    records = _attach_error_collectors(page)
    captured: list[Path] = []
    try:
        # 1. Home Dark — primary Starloop Night visual (1440x900)
        page.goto(f"{static_server}/", wait_until="networkidle")
        assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"
        home_dark = screenshot_dir / "home-dark.png"
        page.screenshot(path=str(home_dark), full_page=False)
        captured.append(home_dark)

        # 2. Home Light — Ivory Collector's Edition (1440x900)
        page.locator("[data-theme-toggle]").click()
        assert page.evaluate("() => document.documentElement.dataset.theme") == "light"
        page.wait_for_timeout(200)
        home_light = screenshot_dir / "home-light.png"
        page.screenshot(path=str(home_light), full_page=False)
        captured.append(home_light)

        # Switch back to default dark for remaining primary desktop screenshots
        page.locator("[data-theme-toggle]").click()
        assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"
        page.wait_for_timeout(200)

        # 3. Articles + Search Modal with results in dark mode (1440x900)
        page.goto(f"{static_server}/articles/", wait_until="networkidle")
        page.keyboard.press("Control+k")
        page.locator("[data-search-modal]").wait_for(state="visible")
        page.locator("[data-search-input]").fill("设计")
        page.locator("[data-search-results] .search-result-item").first.wait_for(state="visible")
        page.wait_for_timeout(120)
        articles_search = screenshot_dir / "articles-search.png"
        page.screenshot(path=str(articles_search), full_page=False)
        captured.append(articles_search)
        page.keyboard.press("Escape")

        # 4. Post detail showing prose, code block, and sticky TOC in dark mode (1440x900)
        page.goto(f"{static_server}/articles/python-static-architecture/", wait_until="networkidle")
        page.evaluate(
            """() => {
                const code = document.querySelector('.code-block-wrapper');
                if (code) {
                    const rect = code.getBoundingClientRect();
                    const top = Math.max(0, rect.top + window.scrollY - 260);
                    window.scrollTo({ top: top, behavior: 'instant' });
                }
            }"""
        )
        page.wait_for_timeout(200)
        post_detail = screenshot_dir / "post-detail.png"
        page.screenshot(path=str(post_detail), full_page=False)
        captured.append(post_detail)

        # 5. Projects in dark mode (1440x900)
        page.goto(f"{static_server}/projects/", wait_until="networkidle")
        projects_shot = screenshot_dir / "projects.png"
        page.screenshot(path=str(projects_shot), full_page=False)
        captured.append(projects_shot)

        # 6. About with Astra portrait in dark mode (1440x900)
        page.goto(f"{static_server}/about/", wait_until="networkidle")
        about_shot = screenshot_dir / "about.png"
        page.screenshot(path=str(about_shot), full_page=False)
        captured.append(about_shot)

        _assert_clean_page(records, "screenshots-desktop")
    finally:
        context.close()

    # 7. Mobile Home in default dark mode (390x844)
    mobile_ctx = browser.new_context(viewport=mobile_viewport)
    mobile_page = mobile_ctx.new_page()
    mobile_records = _attach_error_collectors(mobile_page)
    try:
        mobile_page.goto(f"{static_server}/", wait_until="networkidle")
        assert mobile_page.evaluate("() => document.documentElement.dataset.theme") == "dark"
        home_mobile = screenshot_dir / "home-mobile.png"
        mobile_page.screenshot(path=str(home_mobile), full_page=False)
        captured.append(home_mobile)
        _assert_clean_page(mobile_records, "screenshots-mobile")
    finally:
        mobile_ctx.close()

    for path in captured:
        assert path.is_file(), f"Missing screenshot {path}"
        assert path.stat().st_size > 5000, f"Screenshot too small: {path}"


def test_github_pages_subpath_deployment(browser: Browser, tmp_path: Path) -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from backend.renderer import render_site

    subpath_dist = tmp_path / "dist"
    stats = render_site(
        PROJECT_ROOT,
        dist_dir=subpath_dist,
        clean=True,
        base_path="/astrayao-blog",
        site_url="https://example.github.io/astrayao-blog",
    )
    assert stats["base_path"] == "/astrayao-blog"
    assert (subpath_dist / ".nojekyll").is_file()
    assert not (subpath_dist / "CNAME").exists()

    handler = functools.partial(SubpathDistHandler, directory=str(subpath_dist))
    server = QuietThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"

    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    records = _attach_error_collectors(page)
    try:
        # Confirm unprefixed requests strictly return 404 on this server (bypass any env proxy)
        direct_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for unprefixed in ["/static/css/tokens.css", "/api/search-index.json"]:
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                direct_opener.open(f"{base_url}{unprefixed}", timeout=5)
            assert exc_info.value.code == 404, f"{unprefixed} expected 404, got {exc_info.value.code}"

        resp_home = page.goto(f"{base_url}/astrayao-blog/", wait_until="networkidle")
        assert resp_home is not None and resp_home.status == 200
        assert (
            page.locator('meta[name="site-base-path"]').get_attribute("content")
            == "/astrayao-blog"
        )
        hero_img = page.locator('img[src="/astrayao-blog/static/images/astra-hero.jpg"]')
        assert hero_img.count() == 1 and hero_img.is_visible()
        assert hero_img.evaluate("img => img.complete && img.naturalWidth > 0")

        # Ctrl+K search and click jump into /astrayao-blog/articles/...
        page.keyboard.press("Control+k")
        page.locator("[data-search-modal]").wait_for(state="visible")
        page.locator("[data-search-input]").fill("设计")
        first_result = page.locator("[data-search-results] .search-result-item").first
        first_result.wait_for(state="visible")
        href = first_result.get_attribute("href") or ""
        assert href.startswith("/astrayao-blog/articles/"), f"Unexpected search href: {href}"

        first_result.click()
        page.wait_for_url("**/astrayao-blog/articles/**")
        page.wait_for_load_state("networkidle")
        assert "/astrayao-blog/articles/" in page.url

        resp_about = page.goto(f"{base_url}/astrayao-blog/about/", wait_until="networkidle")
        assert resp_about is not None and resp_about.status == 200
        portrait_img = page.locator(
            '.about-portrait-frame img[src="/astrayao-blog/static/images/astra-portrait.jpg"]'
        )
        assert portrait_img.count() == 1 and portrait_img.is_visible()
        assert portrait_img.evaluate("img => img.complete && img.naturalWidth > 0")

        _assert_clean_page(records, "github-pages-subpath")
    finally:
        context.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
