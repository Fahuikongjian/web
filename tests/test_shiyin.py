"""Data and browser coverage for Series 03 《十音簿》."""

from __future__ import annotations

import functools
import json
import os
import re
import shutil
import threading
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

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
GALLERY = "/mystery/shiyin/"
ROOM = GALLERY + "reading-room/"
ROOM_HOME = "https://yinqian.shiyin.lh/"
VAULT = "https://zonglu.shiyin.lh/"
VAULT_TITLE = "十音总录 · 律吕密档"
CLOSING_TITLE = "陆闻笙留笺 · 归律之后"
SNAPSHOT = "切至原始母带"
RESTORE = "返回数字转录版"
SHIYIN_SOURCE = "审音人-癸"
TITLES = ("第一幕 哑钟楼", "第二幕 断弦坊", "第三幕 借腔台", "第四幕 漏更鼓", "第五幕 封盘室")
SLIPS = ("GG", "SH", "JU", "ZH", "YU")
FINISH = "【十音总录完】"

ACTS = (
    ("zhongtan", "bobao/newyear-tape", "2008-12-31", "gongshi/tower-repair", "gongshi/master-approval", "共鸣瓮"),
    ("tongyin", "shengxue/spectrum-log", "SY-10", "yueyou/night-hum", "qinfang/material-inspection", "阴沉木"),
    ("xima", "jutuan/tape-1986", "1986-11-18", "ximi/backstage-echo", "jutuan/mix-handoff", "补录"),
    ("gengguxiang", "zaosheng/night-db", "五更三点", "laoju/drum-rumor", "zaosheng/rough-log", "暗梆"),
    ("yinxiang", "jiance/channel-feed", "2008-12-31", "dianji/shellac-ledger", "jiance/cast-script", "并网"),
)


def _url(domain: str, location: str) -> str:
    host, _, path = location.partition("/")
    return f"https://{host}.{domain}.lh/{path}"


@pytest.fixture(scope="module")
def dossiers() -> dict[str, dict]:
    result = {}
    for path in sorted(DATA_DIR.glob("shiyin-*.json")):
        data = json.loads(path.read_bytes().decode("utf-8"))
        result[path.name] = data
    assert len(result) == 7
    return result


def _case(dossiers: dict[str, dict], volume: int) -> dict:
    home = ROOM_HOME if volume == 0 else _url(ACTS[volume - 1][0], "index")
    return next(data for data in dossiers.values() if data["homeUrl"] == home)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        chromium = playwright.chromium
        executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        if not executable and not Path(chromium.executable_path).is_file():
            executable = shutil.which("chromium") or shutil.which("google-chrome")
            chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
            if not executable and chrome.is_file():
                executable = str(chrome)
        launched = chromium.launch(executable_path=executable, headless=True)
        try:
            yield launched
        finally:
            launched.close()


@pytest.fixture(scope="module")
def site_url(tmp_path_factory):
    dist = tmp_path_factory.mktemp("shiyin-dist") / "dist"
    render_site(PROJECT_ROOT, dist_dir=dist)
    yield from _serve_directory(dist)


@pytest.fixture(scope="module")
def subpath_url(tmp_path_factory):
    dist = tmp_path_factory.mktemp("shiyin-subpath") / "dist"
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


@pytest.fixture
def open_page(browser):
    contexts = []

    def create(width: int, height: int):
        context = browser.new_context(
            viewport={"width": width, "height": height},
            is_mobile=width < 768,
            has_touch=width < 768,
        )
        contexts.append(context)
        return context.new_page()

    yield create
    for context in contexts:
        context.close()


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def test_shiyin_data_integrity_and_solvability_gate(dossiers):
    finale = dossiers["shiyin-finale-dossier.json"]
    chapters = [data for name, data in dossiers.items() if name != "shiyin-finale-dossier.json"]
    for key in ("caseId", "storageKey"):
        values = [data[key] for data in chapters]
        assert all(values) and len(set(values)) == 6
    assert set(finale.keys()) == {"sites", "records", "checks", "conclusion"}
    for data in chapters:
        assert data["seriesKey"] == "shiyin"
        assert data["snapshotButtonLabels"]["enter"] == SNAPSHOT
        assert data["snapshotButtonLabels"]["exit"] == RESTORE
        corpus = "\n".join(_strings(data))
        assert "星环手记" not in corpus and "vault-61" not in corpus
    for data in dossiers.values():
        records_corpus = "\n".join(_strings(data["records"]))
        works = [*data.get("checks", [])]
        if data.get("conclusion"):
            works.append(data["conclusion"])
        for work in works:
            assert work["leads"] and work["receipt"] and len(work["fields"]) >= 3
            for field in work["fields"]:
                assert field["accept"] and field["accept"][0] in records_corpus, (work["id"], field["label"])
    for volume in range(1, 6):
        data = _case(dossiers, volume)
        assert data["storageKey"] == f"shiyin_save_v1_ch{volume:02}"
        assert len(data["checks"]) == 6
        assert any(record.get("index") == "site" for record in data["records"])
        assert any(record.get("snapshot") for record in data["records"])
        assert any(SHIYIN_SOURCE in (record.get("source") or "") for record in data["records"])
        assert f"本卷工尺音签：{SLIPS[volume - 1]}。" in data["conclusion"]["receipt"][-1]
    assert len(finale["checks"]) == 4
    assert any(record.get("snapshot") for record in finale["records"])
    assert any(SHIYIN_SOURCE in (record.get("source") or "") for record in finale["records"])
    assert FINISH in "\n".join(_strings(finale["conclusion"]))
    closing = next(record for record in finale["records"] if record["title"] == CLOSING_TITLE)
    assert closing["requiresGate"] == "filed:receipt"


def _theme(page):
    return page.evaluate(
        """() => {
            const body = getComputedStyle(document.body);
            const card = document.querySelector('[data-reel-card].hub-card--featured, [data-reel-card].darun-card--act, [data-reel-card].sj-card--act, [data-reel-card].sy-card--act');
            const cs = getComputedStyle(card);
            return {
                level: document.querySelector('[data-mystery-level]').getAttribute('data-mystery-level'),
                bodyBg: body.backgroundColor,
                cardBgImage: cs.backgroundImage,
                cardBorderColor: cs.borderColor,
                cardRadius: cs.borderRadius,
            };
        }"""
    )


def test_shiyin_two_level_gallery_and_theme(open_page, site_url):
    page = open_page(1440, 900)
    errors = _attach_error_collectors(page)
    page.goto(site_url + "/mystery/", wait_until="networkidle")
    expect(page.locator("[data-reel-card]")).to_have_count(6)
    expect(page.locator(".hub-topbar-status")).to_contain_text("03 已开卷 / 01 筹备")
    cards = page.locator("[data-reel-card]")
    veiled = cards.filter(has_text="百药图")
    expect(veiled).to_be_visible()
    expect(veiled.locator("a[href]")).to_have_count(0)
    hub = _theme(page)

    page.get_by_role("link", name="十音簿", exact=False).click()
    expect(page).to_have_url(site_url + GALLERY)
    expect(page.locator('[data-mystery-level="shiyin"]')).to_have_count(1)
    for title in TITLES:
        expect(page.get_by_role("link", name=title, exact=False)).to_be_visible()
    expect(page.locator("[data-horizontal-reel] a[href*='/act-']")).to_have_count(5)
    _assert_no_horizontal_overflow(page, GALLERY, "1440x900")

    reel = page.locator("[data-horizontal-reel]")
    box = reel.bounding_box()
    before = reel.evaluate("el => el.scrollLeft")
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.wheel(0, 520)
    page.wait_for_function("el => el.scrollLeft > 0", arg=reel.element_handle(), timeout=5000)
    assert reel.evaluate("el => el.scrollLeft") > before

    shiyin = _theme(page)
    assert shiyin["level"] != hub["level"]
    assert shiyin["bodyBg"] != hub["bodyBg"]
    for path in ("/mystery/darun/", "/mystery/suojiang/"):
        page.goto(site_url + path, wait_until="networkidle")
        other = _theme(page)
        assert shiyin["level"] != other["level"]
        assert shiyin["bodyBg"] != other["bodyBg"]
        assert shiyin["cardBorderColor"] != other["cardBorderColor"]

    page.goto(site_url + GALLERY, wait_until="networkidle")
    page.get_by_text("未完待续", exact=True).click()
    page.get_by_role("link", name="核对音签").click()
    expect(page).to_have_url(site_url + ROOM)
    _assert_clean_page(errors, "shiyin two-level gallery")


def _navigate(page, target: str) -> None:
    field = page.get_by_label("网址", exact=True)
    field.fill(target)
    field.press("Enter")
    expect(field).to_have_value(target)


def _search(page, query: str) -> None:
    _navigate(page, "https://search.shiyin.lh/")
    field = page.get_by_role("searchbox", name="检索关键词")
    field.fill(query)
    field.press("Enter")


def _source(page):
    page.get_by_role("button", name="查看源码").click()
    viewer = page.get_by_role("dialog")
    expect(viewer).to_be_visible()
    return viewer


def _submit(page, work: dict, *, wrong: bool = False) -> None:
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


def _review_base(chapter: dict) -> str:
    return "https://" + next(site["domain"] for site in chapter["sites"] if site.get("kind") == "review") + "/"


def _walk_act(page, base: str, volume: int, data: dict, *, reload: bool = False, follow_links: bool = False) -> None:
    domain, tape, clue, source_loc, hidden_loc, keyword = ACTS[volume - 1]
    page.goto(base + f"/mystery/shiyin/act-{volume}/", wait_until="networkidle")
    expect(page.get_by_role("heading", name=data["sites"][0]["heading"])).to_be_visible()
    assert page.evaluate("() => document.body.dataset.series") == "shiyin"
    _assert_no_horizontal_overflow(page, page.url, f"shiyin-act-{volume}")

    # Master tape snapshot toggle
    _navigate(page, _url(domain, tape))
    snap_btn = page.locator("[data-snapshot]")
    expect(snap_btn).to_have_text(SNAPSHOT)
    snap_btn.click()
    expect(snap_btn).to_have_text(RESTORE)
    expect(snap_btn).to_have_attribute("aria-pressed", "true")
    expect(page.locator(".archive-document")).to_contain_text(clue)
    if reload:
        page.reload(wait_until="networkidle")
        expect(snap_btn).to_have_text(RESTORE)
        expect(page.locator(".archive-document")).to_contain_text(clue)
    snap_btn.click()
    expect(snap_btn).to_have_text(SNAPSHOT)

    # HTML source comment
    _navigate(page, _url(domain, source_loc))
    viewer = _source(page)
    expect(viewer.locator("pre")).to_contain_text(SHIYIN_SOURCE)
    viewer.get_by_role("button", name="关闭").click()

    # Search site: operator & isolation (single 全部网页 tab)
    hidden_url = _url(domain, hidden_loc)
    hidden_domain = urlsplit(hidden_url).hostname
    _search(page, keyword)
    expect(page.locator(".site-search-tab")).to_have_count(1)
    expect(page.locator(".site-search-tab")).to_have_text("全部网页")
    expect(page.locator(f'a[data-mystery-link="{hidden_url}"]')).to_have_count(0)
    _search(page, f"site:{hidden_domain} {keyword}")
    link = page.locator(f'a[data-mystery-link="{hidden_url}"]')
    expect(link).to_be_visible()
    link.click()
    expect(page.locator(".archive-document")).to_contain_text(keyword)

    # Complete all 6 checks + conclusion
    review_base = _review_base(data)
    _navigate(page, review_base + data["checks"][0]["id"])
    for index, work in enumerate(data["checks"]):
        if not follow_links:
            _navigate(page, review_base + work["id"])
        if index == 0:
            _submit(page, work, wrong=True)
        _submit(page, work)
        if follow_links:
            doc = page.locator(".archive-document")
            target_id = (
                data["checks"][index + 1]["id"]
                if index + 1 < len(data["checks"])
                else data["conclusion"]["id"]
            )
            nxt = doc.locator(f'a[data-mystery-link="{review_base}{target_id}"]')
            expect(nxt).to_be_visible()
            nxt.click()

    if not follow_links:
        _navigate(page, review_base + data["conclusion"]["id"])
    _submit(page, data["conclusion"], wrong=True)
    _submit(page, data["conclusion"])
    page.reload(wait_until="networkidle")
    expect(page.locator(".archive-receipt")).to_contain_text(f"本卷工尺音签：{SLIPS[volume - 1]}。")
    _assert_no_horizontal_overflow(page, page.url, f"shiyin-act-{volume}-receipt")


def test_shiyin_act_1_desktop_full_walkthrough(open_page, site_url, dossiers):
    page = open_page(1440, 900)
    errors = _attach_error_collectors(page)
    _walk_act(page, site_url, 1, _case(dossiers, 1), reload=True, follow_links=True)
    page.get_by_role("link", name="分卷目录").click()
    expect(page).to_have_url(site_url + GALLERY)
    _assert_clean_page(errors, "shiyin act 1 desktop")


@pytest.mark.parametrize("volume", range(1, 6))
def test_shiyin_acts_mobile_subpath_completion(open_page, subpath_url, volume, dossiers):
    page = open_page(390, 844)
    errors = _attach_error_collectors(page)
    page.goto(subpath_url + "/mystery/darun/", wait_until="networkidle")
    page.evaluate("localStorage.setItem('darun_save_v1_ch01', '{\"sentinel\":1}')")
    before = page.evaluate("Object.fromEntries(Object.entries(localStorage))")
    data = _case(dossiers, volume)
    _walk_act(page, subpath_url, volume, data)
    assert page.url.startswith(subpath_url + "/")
    after = page.evaluate("Object.fromEntries(Object.entries(localStorage))")
    key = data["storageKey"]
    assert after.get(key) and after[key] != before.get(key)
    assert {k: v for k, v in after.items() if k != key} == before
    _assert_clean_page(errors, f"shiyin act {volume} mobile subpath")


def test_shiyin_reading_room_and_finale_subpath(open_page, subpath_url, dossiers):
    page = open_page(1440, 900)
    errors = _attach_error_collectors(page)
    requests = []
    page.on("request", lambda request: requests.append(request.url))

    page.goto(subpath_url + GALLERY, wait_until="networkidle")
    page.get_by_text("未完待续", exact=True).click()
    page.get_by_role("link", name="核对音签").click()
    expect(page).to_have_url(subpath_url + ROOM)
    expect(page.locator("meta[name=robots]")).to_have_attribute("content", "noindex")
    assert not any(url.endswith("/shiyin-finale-dossier.json") for url in requests)

    _navigate(page, VAULT)
    expect(page.get_by_role("heading", name="该网址没有存入本卷")).to_be_visible()

    entry = dossiers["shiyin-reading-room.json"]
    _navigate(page, entry["homeUrl"])
    _submit(page, entry["entry"], wrong=True)
    assert not any(url.endswith("/shiyin-finale-dossier.json") for url in requests)

    _submit(page, entry["entry"])
    assert any(url.endswith("/shiyin-finale-dossier.json") for url in requests)
    page.get_by_role("link", name=VAULT_TITLE, exact=True).click()
    expect(page.get_by_role("heading", name=dossiers["shiyin-finale-dossier.json"]["sites"][0]["heading"])).to_be_visible()

    # Closing note remains gated until receipt is filed
    _navigate(page, VAULT + "closing-note")
    expect(page.get_by_role("heading", name="此页未归档")).to_be_visible()

    # Master drift snapshot + source reveal
    _navigate(page, VAULT + "master-drift")
    page.locator("[data-snapshot]").click()
    expect(page.locator(".archive-document")).to_contain_text("星环手记")
    viewer = _source(page)
    expect(viewer.locator("pre")).to_contain_text(SHIYIN_SOURCE)
    viewer.get_by_role("button", name="关闭").click()

    finale = dossiers["shiyin-finale-dossier.json"]
    base = _review_base(finale)
    for index, work in enumerate(finale["checks"]):
        _navigate(page, base + work["id"])
        if index == 0:
            _submit(page, work, wrong=True)
        _submit(page, work)

    _navigate(page, base + finale["conclusion"]["id"])
    _submit(page, finale["conclusion"], wrong=True)
    _submit(page, finale["conclusion"])
    page.reload(wait_until="networkidle")
    expect(page.locator(".archive-receipt")).to_contain_text(FINISH)

    page.get_by_role("link", name=CLOSING_TITLE, exact=True).click()
    expect(page.get_by_role("heading", name=CLOSING_TITLE)).to_be_visible()
    expect(page.locator(".archive-document")).to_contain_text("YS-10")
    _assert_no_horizontal_overflow(page, page.url, "shiyin finale closing")
    _assert_clean_page(errors, "shiyin reading room & finale subpath")


LAYOUTS = (
    ("zhongtan", "index", ".arch-dir-grid"),
    ("zhongtan", "gongshi/tower-repair", ".arch-layout--sidebar-left .arch-doc--redhead"),
    ("tongyin", "yueyou/night-hum", ".arch-doc--bbs .arch-bbs-floors"),
    ("tongyin", "yueqi", ".arch-layout--library .arch-biblio-card"),
    ("xima", "liyuan", ".arch-layout--library .arch-biblio-card"),
    ("gengguxiang", "zaosheng", ".arch-layout--hydro .arch-hydro-tree"),
    ("yinxiang", "diaodu", ".arch-layout--sidebar-right .arch-maritime-duty"),
    ("yinxiang", "zhonghe", ".arch-doc--hall .arch-hall-steps"),
)


def _assert_archive(page, selector: str, viewport: str) -> None:
    reader = page.locator("[data-viewport]")
    expect(reader.locator(selector).first).to_be_visible()
    assert not any(icon in reader.inner_text() for icon in ("⚠", "⏱")), page.url
    _assert_no_horizontal_overflow(page, page.url, viewport)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_shiyin_real_site_layouts_and_anti_highlight(open_page, subpath_url, dossiers):
    for width, height in ((1440, 900), (390, 844)):
        vp = f"{width}x{height}"
        page = open_page(width, height)
        errors = _attach_error_collectors(page)
        for volume, (domain, *_rest) in enumerate(ACTS, 1):
            page.goto(subpath_url + f"/mystery/shiyin/act-{volume}/", wait_until="networkidle")
            for site, location, selector in LAYOUTS:
                if site == domain:
                    _navigate(page, _url(site, location))
                    _assert_archive(page, selector, vp)
            if volume == 1:
                data = _case(dossiers, volume)
                base = _review_base(data)
                w0, w1 = data["checks"][:2]
                _navigate(page, base + w0["id"])
                _submit(page, w0)
                doc = page.locator(".archive-document")
                expect(doc.locator(".archive-receipt")).to_be_visible()
                nxt = doc.locator(f'a[data-mystery-link="{base}{w1["id"]}"]')
                expect(nxt).to_be_visible()
                nxt.click()
                expect(page.get_by_role("heading", name=w1["title"], exact=True)).to_be_visible()

        page.goto(subpath_url + ROOM, wait_until="networkidle")
        if page.locator("[data-review-form]").is_visible():
            _submit(page, dossiers["shiyin-reading-room.json"]["entry"])
        page.get_by_role("link", name=VAULT_TITLE, exact=True).click()
        _assert_archive(page, ".arch-layout--workbench .arch-vault-rail", vp)
        _assert_clean_page(errors, f"shiyin layouts & anti-highlight {vp}")
