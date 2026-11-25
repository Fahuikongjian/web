"""Browser and data coverage for the Darun archive investigations."""

import functools
import json
import os
import shutil
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.renderer import render_site
from tests.test_e2e_browser import (
    PROJECT_ROOT,
    QuietThreadingHTTPServer,
    SubpathDistHandler,
    _assert_clean_page,
    _assert_no_horizontal_overflow,
    _attach_error_collectors,
    _serve_directory,
)


DATA_DIR = PROJECT_ROOT / "static" / "mystery" / "data"
SEARCH = "https://search.qiandu.lh/"
FEIYI = "https://feiyi.fengning.gov.lh/"
FORUM = "https://bbs.huangli.lh/"
BLOG = "https://blog.shanye.lh/"


def _data(name):
    return json.loads((DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        chromium = playwright.chromium
        executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        if not executable and not Path(chromium.executable_path).is_file():
            executable = shutil.which("chromium") or shutil.which("google-chrome")
            windows_chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
            if not executable and windows_chrome.is_file():
                executable = str(windows_chrome)
        launched = chromium.launch(executable_path=executable, headless=True)
        yield launched
        launched.close()


@pytest.fixture(scope="module")
def site_url(tmp_path_factory):
    dist = tmp_path_factory.mktemp("archive-dist") / "dist"
    render_site(PROJECT_ROOT, dist_dir=dist)
    yield from _serve_directory(dist)


@pytest.fixture(scope="module")
def subpath_url(tmp_path_factory):
    dist = tmp_path_factory.mktemp("archive-subpath") / "dist"
    mount = SubpathDistHandler.mount_prefix
    render_site(PROJECT_ROOT, dist_dir=dist, base_path=mount)
    handler = functools.partial(SubpathDistHandler, directory=str(dist))
    with QuietThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}{mount}"
        finally:
            server.shutdown()
            thread.join(timeout=5)


def _navigate(page, target):
    field = page.get_by_label("网址", exact=True)
    field.fill(target)
    field.press("Enter")
    expect(field).to_have_value(target)


def _search(page, query):
    _navigate(page, SEARCH)
    field = page.get_by_role("searchbox", name="检索关键词")
    field.fill(query)
    field.press("Enter")


def _source(page):
    page.get_by_role("button", name="查看源码").click()
    viewer = page.get_by_role("dialog")
    expect(viewer).to_be_visible()
    return viewer


def _submit(page, work, *, wrong=False):
    form = page.locator("[data-review-form]")
    for index, field in enumerate(work["fields"]):
        value = "错误的填写" if wrong and index == 0 else field["accept"][0]
        form.get_by_label(field["label"], exact=True).fill(value)
    form.get_by_role("button").click()
    if wrong:
        expect(form.locator("[aria-invalid=true]")).to_have_count(1)
        expect(form.get_by_role("status")).to_contain_text("1 项")
    else:
        expect(page.locator(".archive-receipt")).to_contain_text(work["receipt"][0])


def _review_base(chapter):
    return "https://" + next(site["domain"] for site in chapter["sites"] if site.get("kind") == "review") + "/"


def test_archive_route_and_story_data_integrity():
    chapters = [_data(f"act-{number}") for number in range(1, 6)]
    legacy = _data("case_manifest")
    assert len({chapter["caseId"] for chapter in chapters}) == 5
    assert len({chapter["storageKey"] for chapter in chapters}) == 5
    assert chapters[0]["storageKey"] == legacy["storageKey"]
    for number, chapter in enumerate(chapters, start=1):
        old_sites = legacy["sites"] if number == 1 else []
        domains = {site["domain"] for site in chapter["sites"] + old_sites} | {urlsplit(SEARCH).hostname}
        routes = {(item["site"], item["id"]) for item in chapter["records"]}
        assert len(routes) == len(chapter["records"]) >= 42
        assert len({work["id"] for work in chapter["checks"]}) == len(chapter["checks"]) >= 11
        for record in chapter["records"]:
            assert record["site"] in domains
            assert record["paragraphs"]
        for work in [*chapter["checks"], chapter["conclusion"]]:
            assert work["leads"] and work["receipt"] and len(work["fields"]) >= 3
            assert all(field["accept"] for field in work["fields"])
        payload = json.dumps(chapter, ensure_ascii=False)
        assert "vault-61" not in payload
        assert "星环手记" not in payload
        assert "太闰" not in payload
    entry = _data("reading-room")
    assert not entry["records"]
    assert "太闰" not in json.dumps(entry, ensure_ascii=False)
    assert "星环手记" not in json.dumps(entry, ensure_ascii=False)
    for chapter, field in zip(chapters, entry["entry"]["fields"], strict=True):
        assert f"本卷转存撕条：{field['accept'][0]}。" in chapter["conclusion"]["receipt"][-1]
    thread = next(item for item in _data("site_forum")["threads"] if item["id"] == "605")
    entry = next(item for item in _data("site_search")["entries"] if item["id"] == "sr-forum-605")
    assert entry["title"].startswith(thread["title"])
    assert entry["date"] == thread["createdAt"].split()[0]


def test_first_act_archived_pages_and_completion(browser, site_url):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = _attach_error_collectors(page)
    page.goto(site_url + "/mystery/", wait_until="networkidle")
    expect(page.get_by_text("敬请期待", exact=True)).to_be_visible()
    page.get_by_role("link", name="大闰录", exact=False).click()
    expect(page).to_have_url(site_url + "/mystery/darun/")
    expect(page.get_by_role("link", name="第一幕 纸傩代身", exact=False)).to_be_visible()
    expect(page.get_by_role("link", name="第二幕 门牌余号", exact=False)).to_be_visible()
    page.get_by_text("未完待续", exact=True).click()
    expect(page.get_by_text("此页留待下一批", exact=False)).to_be_visible()
    page.get_by_role("link", name="第一幕 纸傩代身", exact=False).click()
    expect(page.get_by_role("heading", name="旧网拾遗", exact=False).first).to_be_visible()
    expect(page.get_by_text("丰ICP备-LXJZ-61", exact=True)).to_be_visible()
    expect(page.locator("[data-evidence-board], [data-mystery-bookmark]")).to_have_count(0)

    _search(page, "605")
    entry = page.get_by_role("link", name="你们家电子族谱", exact=False)
    expect(entry).to_be_visible()
    entry.click()
    expect(page.get_by_text("那一行原本是空的", exact=False)).to_be_visible()
    page.go_back()
    expect(page.get_by_role("searchbox").first).to_have_value("605")

    _search(page, "LXJZ-61")
    page.get_by_role("link", name="查阅缓存").click()
    expect(page.get_by_text("纸本 365 页", exact=False)).to_be_visible()
    _navigate(page, BLOG + "post/temple-smoke")
    page.locator("[data-reveal-ink]").click()
    expect(page.get_by_text("密码前半段是四个大写字母", exact=False)).to_be_visible()
    dialog = _source(page)
    expect(dialog.locator("pre")).to_contain_text("NUOX")
    dialog.get_by_role("button", name="关闭").click()
    _navigate(page, BLOG + "post/locked-404b")
    page.locator("[data-blog-lock-input]").fill("NUOX-1994")
    page.locator("[data-blog-lock-form] button").click()
    expect(page.locator("[data-blog-lock-form]")).to_have_count(0)

    _navigate(page, FORUM + "thread/610")
    page.get_by_role("button", name="历史版本").click()
    expect(page.get_by_text("2024 年 12 月 2 日", exact=False)).to_be_visible()
    page.reload(wait_until="networkidle")
    expect(page.get_by_role("button", name="返回现行版")).to_have_attribute("aria-pressed", "true")
    _navigate(page, FEIYI + "internal")
    page.get_by_label("职工工号", exact=False).fill("FY2018061")
    page.get_by_label("个人馆藏口令", exact=False).fill("cyq081561")
    page.locator("[data-inst-login] button[type=submit]").click()
    expect(page.get_by_role("heading", name="1994 太平社合影", exact=False)).to_be_visible()
    page.locator("a[data-mystery-link$='/doc-paper-nuo']").click()
    expect(page.locator(".site-inst-photo-frame")).to_be_visible()

    _navigate(page, "https://wy.huaianli.lh/notice/building7-demolition")
    page.get_by_role("button", name="历史版本").click()
    expect(page.locator(".mystery-snapshot-diff")).to_contain_text("404B")
    _search(page, "site:ziliaoguan.fengning.lh 青笺")
    page.get_by_role("link", name="青笺副联", exact=False).click()
    expect(page.get_by_text("独盒保管", exact=True)).to_be_visible()

    chapter = _data("act-1")
    base = _review_base(chapter)
    _navigate(page, base + chapter["conclusion"]["id"])
    expect(page.get_by_role("heading", name="待补材料")).to_be_visible()
    for index, work in enumerate(chapter["checks"]):
        _navigate(page, base + work["id"])
        if index == 0:
            _submit(page, work, wrong=True)
        _submit(page, work)
    _navigate(page, base + chapter["conclusion"]["id"])
    _submit(page, chapter["conclusion"])
    page.reload(wait_until="networkidle")
    expect(page.locator(".archive-receipt")).to_contain_text("七号楼破拆暂缓")
    _assert_clean_page(errors, "first archive")
    page.close()


def test_second_act_independent_mobile_subpath_completion(browser, subpath_url):
    page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    errors = _attach_error_collectors(page)
    page.goto(subpath_url + "/games/", wait_until="networkidle")
    page.get_by_role("link", name="查看分卷目录").click()
    expect(page).to_have_url(subpath_url + "/mystery/")
    _assert_no_horizontal_overflow(page, page.url, "390x844")
    page.get_by_role("link", name="大闰录", exact=False).click()
    expect(page).to_have_url(subpath_url + "/mystery/darun/")
    _assert_no_horizontal_overflow(page, page.url, "390x844")
    page.get_by_role("link", name="第二幕 门牌余号", exact=False).click()
    expect(page.get_by_role("heading", name="澄溪清河巷旧站存档")).to_be_visible()
    page.get_by_role("link", name="清河街道公示栏", exact=True).click()
    page.get_by_role("link", name="清河巷换领门牌公告", exact=False).click()
    expect(page.get_by_text("已转正", exact=True)).to_be_visible()
    page.get_by_role("button", name="历史版本").click()
    expect(page.get_by_text("测绘占位", exact=True)).to_be_visible()
    _assert_no_horizontal_overflow(page, page.url, "390x844")

    _navigate(page, "https://qinghe-tongxun.lh/post-return")
    viewer = _source(page)
    expect(viewer.locator("pre")).to_contain_text("TD-62")
    viewer.get_by_role("button", name="关闭").click()
    _search(page, "退回信件登记")
    expect(page.get_by_role("link", name="退回信件登记")).to_have_count(0)
    _search(page, "site:qinghe-tongxun.lh 退回信件登记")
    page.get_by_role("link", name="退回信件登记").click()
    expect(page.get_by_text("段素兰", exact=True)).to_be_visible()
    _assert_no_horizontal_overflow(page, page.url, "390x844")

    chapter = _data("act-2")
    base = _review_base(chapter)
    for work in chapter["checks"]:
        _navigate(page, base + work["id"])
        _submit(page, work)
    _navigate(page, base + chapter["conclusion"]["id"])
    _submit(page, chapter["conclusion"])
    page.reload(wait_until="networkidle")
    expect(page.locator(".archive-receipt")).to_contain_text("本卷转存撕条：QS")
    assert page.evaluate("localStorage.getItem('darun_save_v1_ch01')") is None
    page.get_by_role("link", name="分卷目录").click()
    expect(page).to_have_url(subpath_url + "/mystery/darun/")
    _assert_clean_page(errors, "second archive")
    page.close()


@pytest.mark.parametrize(
    "volume,landing,version_url,original_text,source_url,old_title,source_domain,receipt_text",
    [
        (3, "栖梧迁居资料目录", "https://minzheng.qiwu.lh/maternity-index", "沈霁",
         "https://fangtan.qiwu.lh/ghost-letter", "回姓暂寄", "fangtan.qiwu.lh", "南埠原册恢复沈霁"),
        (4, "鸣川春汛资料目录", "https://qixiang.mingchuan.lh/shift-index", "TY-31",
         "https://radio.mingchuan.lh/lost-carousel", "零点不发", "radio.mingchuan.lh", "春汛数据回到鸣川原来的历页"),
        (5, "蒲岭会屋修复资料目录", "https://wenhua.puling.lh/restoration", "白麻衬",
         "https://yingyin.puling.lh/listen-index", "炉后三问", "yingyin.puling.lh", "白鹭会停用代收栏"),
    ],
)
def test_later_acts_independent_completion(
    browser, subpath_url, volume, landing, version_url, original_text, source_url, old_title, source_domain, receipt_text
):
    page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    errors = _attach_error_collectors(page)
    page.goto(subpath_url + f"/mystery/act-{volume}/", wait_until="networkidle")
    expect(page.get_by_role("heading", name=landing)).to_be_visible()
    _assert_no_horizontal_overflow(page, page.url, "390x844")
    _navigate(page, version_url)
    page.get_by_role("button", name="历史版本").click()
    expect(page.get_by_text(original_text, exact=True)).to_be_visible()
    _navigate(page, source_url)
    dialog = _source(page)
    expect(dialog.locator("pre")).to_contain_text(old_title)
    dialog.get_by_role("button", name="关闭").click()
    _search(page, f"site:{source_domain} {old_title}")
    page.get_by_role("link", name=old_title, exact=False).click()
    expect(page.get_by_role("heading", name=old_title, exact=False)).to_be_visible()

    chapter = _data(f"act-{volume}")
    base = _review_base(chapter)
    for work in chapter["checks"]:
        _navigate(page, base + work["id"])
        _submit(page, work)
    _navigate(page, base + chapter["conclusion"]["id"])
    _submit(page, chapter["conclusion"])
    page.reload(wait_until="networkidle")
    expect(page.locator(".archive-receipt")).to_contain_text(receipt_text)
    assert page.evaluate("localStorage.getItem('darun_save_v1_ch01')") is None
    _assert_clean_page(errors, f"act {volume}")
    page.close()


def test_hidden_reading_room_and_finale(browser, subpath_url):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = _attach_error_collectors(page)
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    page.goto(subpath_url + "/mystery/", wait_until="networkidle")
    page.get_by_role("link", name="大闰录", exact=False).click()
    expect(page).to_have_url(subpath_url + "/mystery/darun/")
    expect(page.locator("[data-horizontal-reel] a[href*='/act-']")).to_have_count(5)
    page.get_by_text("未完待续", exact=True).click()
    page.get_by_role("link", name="核对撕条").click()
    expect(page.get_by_role("heading", name="目录缺页登记")).to_be_visible()
    assert not any(url.endswith("/finale-dossier.json") for url in requests)
    expect(page.locator("meta[name=robots]")).to_have_attribute("content", "noindex")
    _navigate(page, "https://archive61.darun.lh/")
    expect(page.get_by_role("heading", name="该网址没有存入本卷")).to_be_visible()

    entry = _data("reading-room")
    _navigate(page, entry["homeUrl"])
    _submit(page, entry["entry"], wrong=True)
    assert not any(url.endswith("/finale-dossier.json") for url in requests)
    _submit(page, entry["entry"])
    assert any(url.endswith("/finale-dossier.json") for url in requests)
    page.get_by_role("link", name="第 61 号馆藏目录").click()
    expect(page.get_by_role("heading", name="五地留件会勘")).to_be_visible()

    dossier = _data("finale-dossier")
    base = _review_base(dossier)
    host_imprint = "https://mirror61.darun.lh/host-imprint"
    _navigate(page, host_imprint)
    expect(page.get_by_role("heading", name="此页未归档")).to_be_visible()
    _navigate(page, base + "receipt")
    expect(page.get_by_role("heading", name="待补材料")).to_be_visible()
    for work in dossier["checks"]:
        _navigate(page, base + work["id"])
        _submit(page, work)

    _navigate(page, host_imprint)
    expect(page.get_by_text("【宿主印记】ASTRA YAO · 星环手记", exact=False)).to_be_visible()
    _navigate(page, base + "receipt")
    _submit(page, dossier["conclusion"])
    page.reload(wait_until="networkidle")
    expect(page.locator(".archive-receipt")).to_contain_text("【全录完】")
    page.get_by_role("link", name="阅封柜后的纸封回执").click()
    expect(page.get_by_role("heading", name="封柜回执副联 · 留缺")).to_be_visible()
    page.get_by_role("link", name="分卷目录").click()
    expect(page).to_have_url(subpath_url + "/mystery/darun/")
    _assert_clean_page(errors, "series finale")
    page.close()


def _assert_wheel_scrolls_reel_horizontally(page, route_label: str) -> None:
    stage = page.locator("[data-reel-stage]")
    reel = page.locator("[data-horizontal-reel]")
    expect(stage).to_be_visible()
    expect(reel).to_be_visible()

    initial = page.evaluate(
        """() => ({
            scrollLeft: document.querySelector('[data-horizontal-reel]').scrollLeft,
            scrollY: window.scrollY,
            scrollWidth: document.querySelector('[data-horizontal-reel]').scrollWidth,
            clientWidth: document.querySelector('[data-horizontal-reel]').clientWidth,
        })"""
    )
    assert initial["scrollWidth"] > initial["clientWidth"] + 2, (
        f"Expected horizontal overflow in reel on {route_label}, got {initial}"
    )
    assert initial["scrollLeft"] == 0
    assert initial["scrollY"] == 0

    box = stage.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5)
    page.mouse.wheel(0, 480)
    page.wait_for_function(
        "() => document.querySelector('[data-horizontal-reel]').scrollLeft > 0"
    )
    page.wait_for_timeout(320)

    after = page.evaluate(
        """() => ({
            scrollLeft: document.querySelector('[data-horizontal-reel]').scrollLeft,
            scrollY: window.scrollY,
        })"""
    )
    assert after["scrollLeft"] > 0, f"Expected wheel to scroll reel horizontally on {route_label}"
    assert after["scrollY"] == 0, f"Expected window.scrollY === 0 on {route_label}, got {after['scrollY']}"


def test_two_level_gallery_wheel_themes_and_responsive_layout(browser, site_url):
    desktop = browser.new_page(viewport={"width": 1440, "height": 900})
    desktop_errors = _attach_error_collectors(desktop)
    try:
        desktop.goto(site_url + "/mystery/", wait_until="networkidle")
        expect(desktop.locator('[data-mystery-level="hub"]')).to_have_count(1)
        expect(desktop.get_by_text("敬请期待", exact=True)).to_be_visible()
        _assert_no_horizontal_overflow(desktop, "/mystery/", "1440x900")
        _assert_wheel_scrolls_reel_horizontally(desktop, "/mystery/")

        hub_theme = desktop.evaluate(
            """() => {
                const body = getComputedStyle(document.body);
                const card = getComputedStyle(document.querySelector('.hub-card--featured'));
                return {
                    level: document.querySelector('[data-mystery-level]').getAttribute('data-mystery-level'),
                    bodyBg: body.backgroundColor,
                    cardBgImage: card.backgroundImage,
                    cardBorderColor: card.borderColor,
                    cardRadius: card.borderRadius,
                };
            }"""
        )

        desktop.get_by_role("link", name="大闰录", exact=False).click()
        expect(desktop).to_have_url(site_url + "/mystery/darun/")
        expect(desktop.locator('[data-mystery-level="darun"]')).to_have_count(1)
        for act_title in (
            "第一幕 纸傩代身",
            "第二幕 门牌余号",
            "第三幕 借姓簿",
            "第四幕 失日台",
            "第五幕 空炉回香",
        ):
            expect(desktop.get_by_role("link", name=act_title, exact=False)).to_be_visible()
        expect(desktop.get_by_text("未完待续", exact=True)).to_be_visible()
        _assert_no_horizontal_overflow(desktop, "/mystery/darun/", "1440x900")
        _assert_wheel_scrolls_reel_horizontally(desktop, "/mystery/darun/")

        darun_theme = desktop.evaluate(
            """() => {
                const body = getComputedStyle(document.body);
                const card = getComputedStyle(document.querySelector('.darun-card--act'));
                return {
                    level: document.querySelector('[data-mystery-level]').getAttribute('data-mystery-level'),
                    bodyBg: body.backgroundColor,
                    cardBgImage: card.backgroundImage,
                    cardBorderColor: card.borderColor,
                    cardRadius: card.borderRadius,
                };
            }"""
        )

        assert hub_theme["level"] != darun_theme["level"]
        assert hub_theme["bodyBg"] != darun_theme["bodyBg"]
        assert hub_theme["cardBgImage"] != darun_theme["cardBgImage"]
        assert hub_theme["cardBorderColor"] != darun_theme["cardBorderColor"]
        assert hub_theme["cardRadius"] != darun_theme["cardRadius"]

        desktop.get_by_text("未完待续", exact=True).click()
        desktop.get_by_role("link", name="核对撕条").click()
        expect(desktop).to_have_url(site_url + "/mystery/reading-room/")
        desktop.get_by_role("link", name="分卷目录").click()
        expect(desktop).to_have_url(site_url + "/mystery/darun/")
        _assert_clean_page(desktop_errors, "mystery two-level desktop")
    finally:
        desktop.close()

    mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    mobile_errors = _attach_error_collectors(mobile)
    try:
        mobile.goto(site_url + "/mystery/", wait_until="networkidle")
        expect(mobile.get_by_text("敬请期待", exact=True)).to_be_visible()
        _assert_no_horizontal_overflow(mobile, "/mystery/", "390x844")

        mobile.get_by_role("link", name="大闰录", exact=False).click()
        expect(mobile).to_have_url(site_url + "/mystery/darun/")
        expect(mobile.locator("[data-horizontal-reel] a[href*='/act-']")).to_have_count(5)
        expect(mobile.get_by_text("未完待续", exact=True)).to_be_visible()
        _assert_no_horizontal_overflow(mobile, "/mystery/darun/", "390x844")
        _assert_clean_page(mobile_errors, "mystery two-level mobile")
    finally:
        mobile.close()
