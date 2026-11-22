from __future__ import annotations

import functools
import http.server
import json
import os
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import pytest
from playwright.sync_api import Browser, Page, Request, expect, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.renderer import render_site  # noqa: E402

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


def _serve_directory(directory: Path):
    handler = functools.partial(DistStaticHandler, directory=str(directory))
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
def populated_dist(populated_site_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("browser-populated")
    render_site(populated_site_root, dist_dir=directory)
    return directory


@pytest.fixture(scope="module")
def static_server(populated_dist: Path):
    """Serve the temporary site containing article fixtures."""
    yield from _serve_directory(populated_dist)


@pytest.fixture(scope="module")
def empty_server(empty_site_root: Path, tmp_path_factory: pytest.TempPathFactory):
    directory = tmp_path_factory.mktemp("browser-empty")
    render_site(empty_site_root, dist_dir=directory)
    yield from _serve_directory(directory)


@pytest.fixture(scope="module")
def categorized_server(categorized_site_root: Path, tmp_path_factory: pytest.TempPathFactory):
    directory = tmp_path_factory.mktemp("browser-categorized")
    render_site(categorized_site_root, dist_dir=directory)
    yield from _serve_directory(directory)


@pytest.fixture(scope="module")
def browser() -> Browser:
    """Use an explicit override, Playwright Chromium, or an installed browser."""
    with sync_playwright() as p:
        override = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        if override and not Path(override).is_file():
            pytest.fail(f"PLAYWRIGHT_CHROMIUM_EXECUTABLE does not exist: {override}")
        if not override and not Path(p.chromium.executable_path).is_file():
            override = shutil.which("chromium") or shutil.which("google-chrome")
            windows_chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
            if not override and windows_chrome.is_file():
                override = str(windows_chrome)
        launched = p.chromium.launch(executable_path=override, headless=True)
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
    def record_request_failure(req: Request) -> None:
        # Chromium may cancel a previous page's favicon request during navigation.
        if req.failure == "net::ERR_ABORTED" and urlsplit(req.url).path.endswith("/favicon.svg"):
            return
        records["request_failures"].append((req.url, str(req.failure)))

    page.on("requestfailed", record_request_failure)
    return records


def _assert_clean_page(records: dict[str, list], context_label: str) -> None:
    assert records["console_errors"] == [], f"{context_label} console errors: {records['console_errors']}"
    assert records["page_errors"] == [], f"{context_label} page errors: {records['page_errors']}"
    assert records["failed_responses"] == [], f"{context_label} HTTP >=400: {records['failed_responses']}"
    assert records["request_failures"] == [], f"{context_label} requestfailed: {records['request_failures']}"


def _load_post_routes(dist_dir: Path) -> list[str]:
    posts_json = dist_dir / "api" / "posts.json"
    assert posts_json.is_file(), f"Missing {posts_json}"
    payload = json.loads(posts_json.read_text(encoding="utf-8"))
    posts = payload.get("posts", [])
    assert len(posts) == 2, f"Expected two posts in the test fixture, got {len(posts)}"
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


def _open_home_cover(page: Page) -> None:
    enter = page.locator(".home-cover-enter")
    if enter.is_visible():
        enter.click()
    page.wait_for_function(
        "() => Number(document.querySelector('.home-opening').style.getPropertyValue('--cover-progress')) >= 0.99"
    )


@pytest.mark.parametrize(
    "width,height,flow_axis,min_gap",
    [(1440, 900, "x", 64), (390, 844, "y", 36), (320, 568, "y", 24), (568, 280, "x", 20)],
)
def test_home_cover_fades_as_content_rises_with_scroll(
    browser: Browser, static_server: str, width: int, height: int, flow_axis: str, min_gap: int
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    try:
        page.goto(f"{static_server}/", wait_until="networkidle")
        cover = page.locator(".home-cover")
        artwork = page.locator(".home-cover-artwork")
        header = page.locator(".site-header")
        content = page.locator(".home-entries")
        original_bounds = artwork.bounding_box()
        initial_content_y = content.bounding_box()["y"]
        original_mask = cover.evaluate("el => getComputedStyle(el).maskImage")
        assert original_bounds["height"] == pytest.approx(height, abs=1)
        assert original_mask.startswith("linear-gradient(to top,")
        assert header.evaluate("el => Number(getComputedStyle(el).opacity)") == 0
        assert content.evaluate("el => el.inert")

        travel = page.evaluate(
            """() => document.querySelector('.home-opening').offsetHeight
                     - document.querySelector('.home-opening-stage').offsetHeight"""
        )
        def scroll_to(position: int) -> None:
            page.evaluate("y => window.scrollTo({ top: y, behavior: 'instant' })", position)
            page.wait_for_function(
                """expected => Number(document.querySelector('.home-opening')
                    .style.getPropertyValue('--cover-progress')) === expected""",
                arg=min(1, position / travel),
            )

        middle = round(travel * 0.52)
        scroll_to(middle)
        middle_mask = cover.evaluate("el => getComputedStyle(el).maskImage")
        assert middle_mask != original_mask
        assert artwork.bounding_box() == pytest.approx(original_bounds, abs=1)
        assert content.bounding_box()["y"] == pytest.approx(initial_content_y - middle, abs=2)

        scroll_to(travel)
        final_mask = cover.evaluate("el => getComputedStyle(el).maskImage")
        assert final_mask not in (middle_mask, original_mask)
        assert "100%" in final_mask
        assert artwork.bounding_box() == pytest.approx(original_bounds, abs=1)
        content_y = content.bounding_box()["y"]
        assert content_y == pytest.approx(initial_content_y - travel, abs=2)
        assert not content.evaluate("el => el.inert")
        assert content.is_visible()
        assert content.evaluate("el => el.getBoundingClientRect().bottom") <= height
        _assert_no_horizontal_overflow(page, "/", f"{width}×{height}")
        card_bounds = [card.bounding_box() for card in content.get_by_role("link").all()]
        extent = "width" if flow_axis == "x" else "height"
        gaps = [
            following[flow_axis] - current[flow_axis] - current[extent]
            for current, following in zip(card_bounds, card_bounds[1:])
        ]
        assert len(gaps) == 2
        assert min(gaps) >= min_gap

        scroll_to(middle)
        assert cover.evaluate("el => getComputedStyle(el).maskImage") == middle_mask
        assert content.bounding_box()["y"] == pytest.approx(initial_content_y - middle, abs=2)
        scroll_to(0)
        _open_home_cover(page)
        assert page.evaluate("() => document.activeElement.id") == "home-intro"
    finally:
        page.close()


def test_home_cover_wheel_progress_stays_where_paused(browser: Browser, static_server: str) -> None:
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    try:
        page.goto(f"{static_server}/", wait_until="networkidle")
        content = page.locator(".home-entries")
        original_y = content.bounding_box()["y"]
        travel = page.evaluate(
            """() => document.querySelector('.home-opening').offsetHeight
                     - document.querySelector('.home-opening-stage').offsetHeight"""
        )
        position = 0
        for delta in (40, 205, -115):
            position += delta
            page.mouse.wheel(0, delta)
            page.wait_for_function("y => window.scrollY === y", arg=position)
            page.wait_for_timeout(320)
            assert page.evaluate("() => window.scrollY") == position
            assert content.bounding_box()["y"] == pytest.approx(original_y - position, abs=2)

        page.mouse.wheel(0, travel)
        page.wait_for_function("y => window.scrollY === y", arg=travel)
        assert content.locator("a").count() == 3
    finally:
        page.close()


def test_home_cover_touch_stops_at_a_partial_reveal(browser: Browser, static_server: str) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    touch = page.context.new_cdp_session(page)

    def dispatch(event_type: str, y: int | None = None) -> None:
        points = [{"x": 200, "y": y}] if y is not None else []
        touch.send("Input.dispatchTouchEvent", {"type": event_type, "touchPoints": points})

    try:
        page.goto(f"{static_server}/", wait_until="networkidle")
        content = page.locator(".home-entries")
        original_y = content.bounding_box()["y"]
        dispatch("touchStart", 610)
        for y in (525, 440, 355):
            page.wait_for_timeout(120)
            dispatch("touchMove", y)
        page.wait_for_timeout(180)
        dispatch("touchEnd")
        page.wait_for_timeout(320)
        position = page.evaluate("() => window.scrollY")
        progress = page.locator(".home-opening").evaluate(
            "el => Number(el.style.getPropertyValue('--cover-progress'))"
        )
        assert 0.25 < progress < 0.75
        assert content.bounding_box()["y"] == pytest.approx(original_y - position, abs=2)
    finally:
        page.close()


def test_home_cover_respects_reduced_motion(browser: Browser, static_server: str) -> None:
    page = browser.new_page(reduced_motion="reduce")
    try:
        page.goto(f"{static_server}/", wait_until="networkidle")
        assert not page.locator(".home-opening.is-scroll-cover").count()
        assert page.locator(".site-header").evaluate("el => getComputedStyle(el).position") == "sticky"
        page.locator(".home-cover-enter").click()
        page.wait_for_url("**/#home-intro")
        assert page.locator(".home-entries").is_visible()
    finally:
        page.close()


def test_home_cover_keeps_progress_when_phone_rotates(browser: Browser, static_server: str) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    half_revealed = """() => {
        const value = Number(document.querySelector('.home-opening').style.getPropertyValue('--cover-progress'));
        return Math.abs(value - 0.5) < 0.01;
    }"""
    try:
        page.goto(f"{static_server}/", wait_until="networkidle")
        page.evaluate("""() => {
            const opening = document.querySelector('.home-opening');
            const travel = opening.offsetHeight - opening.querySelector('.home-opening-stage').offsetHeight;
            window.scrollTo({ top: Math.round(travel / 2), behavior: 'instant' });
        }""")
        page.wait_for_function(half_revealed)
        for width, height in [(844, 390), (390, 844)]:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_function("""() => {
                const opening = document.querySelector('.home-opening');
                const travel = opening.offsetHeight - opening.querySelector('.home-opening-stage').offsetHeight;
                return Math.abs(window.scrollY - travel / 2) <= 2;
            }""")
            assert page.evaluate(half_revealed)
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [(280, 653), (320, 568), (568, 280), (700, 360)])
def test_compact_navigation_and_search_fit_viewport(
    browser: Browser, static_server: str, width: int, height: int
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height}, has_touch=True)
    try:
        page.goto(f"{static_server}/articles/", wait_until="networkidle")
        _assert_no_horizontal_overflow(page, "/articles/", f"{width}×{height}")
        actions = page.locator(".header-actions button:visible")
        assert actions.count() == 3
        for button in actions.all():
            bounds = button.bounding_box()
            assert 0 <= bounds["x"] <= width - 44
            assert bounds["width"] >= 44 and bounds["height"] >= 44

        toggle = page.locator("[data-mobile-menu-toggle]")
        drawer = page.locator("[data-mobile-drawer]")
        about_link = drawer.get_by_role("link", name="关于")
        toggle.click()
        expect(drawer).to_be_visible()
        assert drawer.locator(".mobile-drawer-panel").bounding_box()["height"] <= height
        about_link.scroll_into_view_if_needed()
        assert about_link.bounding_box()["y"] + about_link.bounding_box()["height"] <= height
        page.locator(".site-brand").evaluate("el => el.focus()")
        assert drawer.evaluate("el => el.contains(document.activeElement)")

        # Opening search via its shortcut replaces the drawer.
        page.keyboard.press("Control+k")
        expect(drawer).to_be_hidden()
        search = page.locator("[data-search-modal]")
        expect(search).to_be_visible()
        field = page.locator("[data-search-input]")
        expect(field).to_be_focused()
        field.fill("设计")
        expect(search.get_by_role("option").first).to_be_visible()
        page.keyboard.press("ArrowDown")
        selected_id = field.get_attribute("aria-activedescendant")
        assert selected_id
        expect(page.locator(f"#{selected_id}")).to_have_attribute("aria-selected", "true")

        page.set_viewport_size({"width": width, "height": 220})
        page.wait_for_function("document.querySelector('.search-dialog').getBoundingClientRect().bottom <= innerHeight")
        assert search.locator(".search-results").evaluate("el => el.scrollWidth === el.clientWidth")
        close = search.get_by_role("button", name="关闭搜索弹窗")
        close.focus()
        page.keyboard.press("Enter")
        expect(search).to_be_hidden()
        assert page.url.endswith("/articles/")

        toggle.click()
        page.set_viewport_size({"width": 1024, "height": 768})
        expect(drawer).to_be_hidden()
        expect(toggle).to_have_attribute("aria-expanded", "false")
        expect(page.locator(".site-brand")).to_be_focused()
        assert page.evaluate("getComputedStyle(document.documentElement).overflowY") != "hidden"
    finally:
        page.close()


def test_routes_zero_errors_and_responsive_viewports(
    browser: Browser, static_server: str, populated_dist: Path
) -> None:
    post_routes = _load_post_routes(populated_dist)
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
                page.goto(f"{static_server}/articles/", wait_until="networkidle")
                drawer = page.locator("[data-mobile-drawer]")
                toggle = page.locator("[data-mobile-menu-toggle]")
                assert toggle.is_visible()
                toggle.click()
                expect(drawer).to_be_visible()
                page.keyboard.press("Escape")
                expect(drawer).to_be_hidden()

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
        _open_home_cover(page)
        orbits = page.locator(".home-entry-orbits")
        expect(orbits).to_be_visible()

        page.locator("[data-theme-toggle]").click()
        assert page.evaluate("() => document.documentElement.dataset.theme") == "light"
        assert page.evaluate("() => localStorage.getItem('blog-theme')") == "light"
        expect(orbits).to_be_hidden()

        page.reload(wait_until="networkidle")
        assert page.evaluate("() => document.documentElement.dataset.theme") == "light"
        _open_home_cover(page)
        expect(orbits).to_be_hidden()

        page.locator("[data-theme-toggle]").click()
        assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"
        assert page.evaluate("() => localStorage.getItem('blog-theme')") == "dark"
        expect(orbits).to_be_visible()

        _assert_clean_page(records, "theme-toggle")
    finally:
        context.close()


def test_home_cover_loads_and_opens_to_navigation(browser: Browser, static_server: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    records = _attach_error_collectors(page)
    try:
        with page.expect_response("**/static/images/starloop-cover.jpg") as cover_response:
            page.goto(f"{static_server}/", wait_until="networkidle")
        assert cover_response.value.ok
        artwork = page.locator(".home-cover-artwork")
        assert "/static/images/starloop-cover.jpg" in artwork.evaluate(
            "el => getComputedStyle(el).backgroundImage"
        )
        _open_home_cover(page)
        links = page.locator(".home-entries a")
        expect(links).to_have_text(["文章", "项目", "关于"])
        assert [link.get_attribute("href") for link in links.all()] == ["/articles/", "/projects/", "/about/"]
        assert page.locator(".post-row, .project-card, .featured-card").count() == 0
        expect(page.locator(".site-footer")).to_be_hidden()
        links.last.click()
        page.wait_for_url("**/about/")
        portrait_img = page.locator('.about-portrait-frame img[src="/static/images/astra-portrait.jpg"]')
        assert portrait_img.count() == 1 and portrait_img.is_visible()
        assert portrait_img.evaluate("img => img.complete && img.naturalWidth > 0")

        _assert_clean_page(records, "home-cover-and-intro")
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
        assert total_count == 2

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


def test_empty_archive_and_search(browser: Browser, empty_server: str) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 844})
    records = _attach_error_collectors(page)
    try:
        page.goto(f"{empty_server}/", wait_until="networkidle")
        _open_home_cover(page)
        navigation = page.locator(".home-entries")
        navigation.get_by_role("link", name="项目").click()
        page.wait_for_url("**/projects/")
        expect(page.locator("main").get_by_text("暂无已发布项目。")).to_be_visible()
        page.goto(f"{empty_server}/", wait_until="networkidle")
        _open_home_cover(page)
        navigation.get_by_role("link", name="文章").click()
        page.wait_for_url("**/articles/")
        expect(page.locator("main").get_by_text("暂无已发布文章。")).to_be_visible()
        assert page.locator("[data-filter-tag]").count() == 0

        # Empty archive still displays the 4 category tabs with sliding indicator
        tabs = page.locator("[data-category-tabs] [data-filter-category]")
        assert tabs.count() == 4
        assert [t.get_attribute("data-filter-category") for t in tabs.all()] == [
            "all",
            "代码",
            "图像生成",
            "工程",
        ]
        assert [t.locator(".category-tab-label").inner_text().strip() for t in tabs.all()] == [
            "全部",
            "代码",
            "图像生成",
            "工程",
        ]
        assert [t.locator(".category-tab-count").inner_text().strip() for t in tabs.all()] == [
            "0",
            "0",
            "0",
            "0",
        ]

        indicator = page.locator("[data-category-indicator]")
        initial_transform = indicator.evaluate("el => el.style.transform")
        assert "translate3d(" in initial_transform
        expect(page.locator('[data-category-tabs] [data-filter-category="all"]')).to_have_attribute(
            "aria-selected", "true"
        )

        code_tab = page.locator('[data-category-tabs] [data-filter-category="代码"]')
        code_tab.click()
        expect(code_tab).to_have_attribute("aria-selected", "true")
        expect(
            page.locator('[data-category-tabs] [data-filter-category="all"]')
        ).to_have_attribute("aria-selected", "false")
        assert indicator.evaluate("el => el.style.transform") != initial_transform
        assert "category=代码" in unquote(page.url)
        assert page.locator("[data-filter-tag]").count() == 0
        expect(page.locator("main").get_by_text("暂无已发布文章。")).to_be_visible()

        page.locator('[data-category-tabs] [data-filter-category="all"]').click()
        assert "category=" not in unquote(page.url)

        page.locator("[data-search-open]").click()
        dialog = page.locator("[data-search-modal]")
        expect(dialog.get_by_text("暂无已发布文章。")).to_be_visible()
        dialog.get_by_role("combobox").fill("设计")
        expect(dialog.get_by_text("暂无已发布文章。")).to_be_visible()
        assert dialog.get_by_role("option").count() == 0
        _assert_clean_page(records, "empty-archive")
    finally:
        page.close()


def test_categorized_articles_dual_filtering_and_navigation(
    browser: Browser, categorized_server: str, empty_server: str
) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    records = _attach_error_collectors(page)
    try:
        page.goto(f"{categorized_server}/articles/", wait_until="networkidle")
        tabs = page.locator("[data-category-tabs] [data-filter-category]")
        assert [t.get_attribute("data-filter-category") for t in tabs.all()] == [
            "all",
            "代码",
            "图像生成",
            "工程",
        ]
        assert [t.locator(".category-tab-count").inner_text().strip() for t in tabs.all()] == [
            "4",
            "2",
            "1",
            "1",
        ]
        visible_rows = page.locator("[data-articles-list] article.post-row:visible")
        assert visible_rows.count() == 4
        expect(page.locator("[data-articles-count]")).to_have_text("共 4 篇")

        indicator = page.locator("[data-category-indicator]")
        all_transform = indicator.evaluate("el => el.style.transform")

        # 1. Category filtering ('代码') & dynamic tag pill count / availability
        code_tab = page.locator('[data-category-tabs] [data-filter-category="代码"]')
        code_tab.click()
        expect(code_tab).to_have_attribute("aria-selected", "true")
        assert indicator.evaluate("el => el.style.transform") != all_transform
        assert visible_rows.count() == 2
        expect(page.locator("[data-articles-count]")).to_have_text("代码 · 共 2 篇")
        assert "category=代码" in unquote(page.url)
        # '部署' only exists in '工程', so it must be hidden under '代码'
        expect(page.locator('.filter-pills [data-filter-tag="部署"]')).to_be_hidden()
        expect(
            page.locator('.filter-pills [data-filter-tag="设计"] .filter-pill-count')
        ).to_have_text("2")
        expect(
            page.locator('.filter-pills [data-filter-tag="架构"] .filter-pill-count')
        ).to_have_text("1")

        # 2. Second-level Category x Tag filtering ('代码' + '架构')
        arch_tag_btn = page.locator('.filter-pills [data-filter-tag="架构"]')
        arch_tag_btn.click()
        expect(arch_tag_btn).to_have_attribute("aria-pressed", "true")
        assert visible_rows.count() == 1
        expect(page.locator("[data-articles-count]")).to_have_text("代码 · 「架构」· 共 1 篇")
        decoded_url = unquote(page.url)
        assert "category=代码" in decoded_url and "tag=架构" in decoded_url

        # 3. Switching to a category where current tag ('Python') has 0 articles resets tag to 'all'
        page.locator('.filter-pills [data-filter-tag="Python"]').click()
        assert visible_rows.count() == 2
        eng_tab = page.locator('[data-category-tabs] [data-filter-category="工程"]')
        eng_tab.click()
        expect(eng_tab).to_have_attribute("aria-selected", "true")
        expect(page.locator('.filter-pills [data-filter-tag="all"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        assert visible_rows.count() == 1
        expect(page.locator("[data-articles-count]")).to_have_text("工程 · 共 1 篇")
        assert "tag=" not in unquote(page.url)

        # 4. Inline row category button & inline row tag pill click filtering
        page.locator('[data-category-tabs] [data-filter-category="all"]').click()
        assert visible_rows.count() == 4
        page.locator(
            'article.post-row button.post-row-category[data-filter-category="图像生成"]'
        ).first.click()
        expect(
            page.locator('[data-category-tabs] [data-filter-category="图像生成"]')
        ).to_have_attribute("aria-selected", "true")
        assert visible_rows.count() == 1
        assert "category=图像生成" in unquote(page.url)

        page.locator('[data-category-tabs] [data-filter-category="all"]').click()
        assert visible_rows.count() == 4
        page.locator('article.post-row .tag-pill[data-filter-tag="设计"]').first.click()
        expect(page.locator('.filter-pills [data-filter-tag="设计"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        assert visible_rows.count() == 3

        # 5. Direct URL query parameter restoration (?category=代码&tag=CSS)
        page.goto(
            f"{categorized_server}/articles/?category={quote('代码')}&tag={quote('CSS')}",
            wait_until="networkidle",
        )
        expect(code_tab).to_have_attribute("aria-selected", "true")
        expect(page.locator('.filter-pills [data-filter-tag="CSS"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        assert visible_rows.count() == 1
        expect(page.locator("[data-articles-count]")).to_have_text("代码 · 「CSS」· 共 1 篇")

        # 6. Post detail page category link jump & minimal reading time metadata
        page.goto(
            f"{categorized_server}/articles/python-static-pipeline/",
            wait_until="networkidle",
        )
        meta_items_text = page.locator(".post-meta-items").inner_text()
        assert "预计" not in meta_items_text
        meta_cat_link = page.locator("a.post-meta-category")
        expect(meta_cat_link).to_have_text("代码")
        meta_cat_link.click()
        page.wait_for_url("**/articles/?category=*")
        page.wait_for_load_state("networkidle")
        expect(code_tab).to_have_attribute("aria-selected", "true")
        assert visible_rows.count() == 2

        # 7. Zero horizontal overflow across 1440x900, 390x844, 320x568, 280x653
        for width, height in [(1440, 900), (390, 844), (320, 568), (280, 653)]:
            page.set_viewport_size({"width": width, "height": height})
            for target_url, label in [
                (f"{categorized_server}/articles/", f"categorized-articles-{width}x{height}"),
                (
                    f"{categorized_server}/articles/python-static-pipeline/",
                    f"categorized-post-{width}x{height}",
                ),
                (f"{empty_server}/articles/", f"empty-articles-{width}x{height}"),
            ]:
                page.goto(target_url, wait_until="networkidle")
                _assert_no_horizontal_overflow(page, target_url, label)

        _assert_clean_page(records, "categorized-dual-filter")
    finally:
        context.close()


def test_post_reading_experience(browser: Browser, static_server: str) -> None:
    context = browser.new_context(
        viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"]
    )
    page = context.new_page()
    records = _attach_error_collectors(page)
    try:
        page.goto(f"{static_server}/articles/build-fixture/", wait_until="networkidle")

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


def test_mobile_toc_and_clipboard_unavailable(browser: Browser, static_server: str) -> None:
    page = browser.new_page(viewport={"width": 360, "height": 640}, has_touch=True)
    page.add_init_script("""(() => {
        Object.defineProperty(navigator, 'clipboard', {
            value: { writeText: () => Promise.reject(new Error('Clipboard unavailable')) },
        });
        document.execCommand = () => false;
    })()""")
    try:
        page.goto(f"{static_server}/articles/build-fixture/", wait_until="networkidle")
        toc = page.locator("[data-post-toc]")
        assert toc.evaluate("el => !el.open")
        toc.locator("summary").click()
        link = toc.locator(".toc-link").nth(1)
        target = unquote(link.get_attribute("href"))[1:]
        link.click()
        page.wait_for_function("id => document.activeElement.id === id", arg=target)
        assert toc.evaluate("el => !el.open")
        assert unquote(page.url).endswith(f"#{target}")

        copy = page.locator(".code-copy-btn").first
        copy.click()
        expect(copy).to_have_text("复制失败")
        expect(copy).to_be_focused()
        assert "is-copied" not in (copy.get_attribute("class") or "")
    finally:
        page.close()


def test_capture_visual_acceptance_screenshots(
    browser: Browser,
    static_server: str,
    categorized_server: str,
    empty_server: str,
) -> None:
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
        _open_home_cover(page)
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
        page.goto(f"{static_server}/articles/build-fixture/", wait_until="networkidle")
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

        # 7. Categorized Articles List — Dark (1440x900)
        page.goto(f"{categorized_server}/articles/", wait_until="networkidle")
        assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"
        page.wait_for_timeout(200)
        articles_cat_dark = screenshot_dir / "articles-categories-dark.png"
        page.screenshot(path=str(articles_cat_dark), full_page=False)
        captured.append(articles_cat_dark)

        # 8. Categorized Articles List — Light (1440x900)
        page.locator("[data-theme-toggle]").click()
        assert page.evaluate("() => document.documentElement.dataset.theme") == "light"
        page.wait_for_timeout(200)
        articles_cat_light = screenshot_dir / "articles-categories-light.png"
        page.screenshot(path=str(articles_cat_light), full_page=False)
        captured.append(articles_cat_light)

        # Switch back to dark mode
        page.locator("[data-theme-toggle]").click()
        assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"
        page.wait_for_timeout(150)

        # 9. Empty Articles Archive with Category Bar — Dark (1440x900)
        page.goto(f"{empty_server}/articles/", wait_until="networkidle")
        page.wait_for_timeout(150)
        articles_empty_dark = screenshot_dir / "articles-empty-dark.png"
        page.screenshot(path=str(articles_empty_dark), full_page=False)
        captured.append(articles_empty_dark)

        # 10. Post Detail with Clickable Category & Tags — Dark (1440x900)
        page.goto(
            f"{categorized_server}/articles/python-static-pipeline/",
            wait_until="networkidle",
        )
        page.wait_for_timeout(150)
        post_detail_tags = screenshot_dir / "post-detail-tags.png"
        page.screenshot(path=str(post_detail_tags), full_page=False)
        captured.append(post_detail_tags)

        _assert_clean_page(records, "screenshots-desktop")
    finally:
        context.close()

    # 11. Mobile Home & Mobile Categorized Articles in default dark mode (390x844)
    mobile_ctx = browser.new_context(viewport=mobile_viewport)
    mobile_page = mobile_ctx.new_page()
    mobile_records = _attach_error_collectors(mobile_page)
    try:
        mobile_page.goto(f"{static_server}/", wait_until="networkidle")
        assert mobile_page.evaluate("() => document.documentElement.dataset.theme") == "dark"
        home_mobile = screenshot_dir / "home-mobile.png"
        mobile_page.screenshot(path=str(home_mobile), full_page=False)
        captured.append(home_mobile)

        mobile_page.goto(f"{categorized_server}/articles/", wait_until="networkidle")
        mobile_page.wait_for_timeout(150)
        articles_mobile_dark = screenshot_dir / "articles-mobile-dark.png"
        mobile_page.screenshot(path=str(articles_mobile_dark), full_page=False)
        captured.append(articles_mobile_dark)

        _assert_clean_page(mobile_records, "screenshots-mobile")
    finally:
        mobile_ctx.close()

    for path in captured:
        assert path.is_file(), f"Missing screenshot {path}"
        assert path.stat().st_size > 5000, f"Screenshot too small: {path}"


def test_github_pages_subpath_deployment(
    browser: Browser, tmp_path: Path, populated_site_root: Path
) -> None:
    subpath_dist = tmp_path / "dist"
    stats = render_site(
        populated_site_root,
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

        with page.expect_response("**/astrayao-blog/static/images/starloop-cover.jpg") as cover_response:
            resp_home = page.goto(f"{base_url}/astrayao-blog/", wait_until="networkidle")
        assert cover_response.value.ok
        assert resp_home is not None and resp_home.status == 200
        assert (
            page.locator('meta[name="site-base-path"]').get_attribute("content")
            == "/astrayao-blog"
        )
        _open_home_cover(page)
        assert page.locator(".home-entries").is_visible()

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
