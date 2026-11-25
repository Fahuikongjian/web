"""Data integrity, solvability gate, and browser E2E coverage for Series 02 《锁江志》."""

from __future__ import annotations

import functools
import json
import os
import shutil
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Browser, Page, expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.renderer import render_site  # noqa: E402
from tests.test_e2e_browser import (  # noqa: E402
    PROJECT_ROOT,
    QuietThreadingHTTPServer,
    SubpathDistHandler,
    _assert_clean_page,
    _assert_no_horizontal_overflow,
    _attach_error_collectors,
    _serve_directory,
)


DATA_DIR = PROJECT_ROOT / "static" / "mystery" / "data"
SEARCH = "https://search.suojiang.lh/"
ALLOWED_STYLES = {
    "directory",
    "hydro",
    "public",
    "library",
    "maritime",
    "community",
    "office",
    "registry",
}
EXPECTED_SLIPS = ("SY", "DJ", "GZ", "HD", "TN")
DARUN_ONLY_SEARCH_TABS = ("槐安里物业", "非遗政务", "老黄历BBS")


def _load_json_strict(name: str) -> dict:
    path = DATA_DIR / f"{name}.json"
    raw = path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), f"{path.name} must not have a UTF-8 BOM"
    return json.loads(raw.decode("utf-8"))


@pytest.fixture(scope="module")
def browser() -> Browser:
    with sync_playwright() as playwright:
        chromium = playwright.chromium
        executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        if not executable and not Path(chromium.executable_path).is_file():
            executable = shutil.which("chromium") or shutil.which("google-chrome")
            windows_chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
            if not executable and windows_chrome.is_file():
                executable = str(windows_chrome)
        launched = chromium.launch(executable_path=executable, headless=True)
        try:
            yield launched
        finally:
            launched.close()


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory):
    dist = tmp_path_factory.mktemp("suojiang-dist") / "dist"
    render_site(PROJECT_ROOT, dist_dir=dist)
    yield from _serve_directory(dist)


@pytest.fixture(scope="module")
def subpath_url(tmp_path_factory: pytest.TempPathFactory):
    dist = tmp_path_factory.mktemp("suojiang-subpath") / "dist"
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


def _extract_view_strings(view: dict) -> list[str]:
    parts: list[str] = []
    for key in ("title", "date", "source"):
        val = view.get(key)
        if isinstance(val, str):
            parts.append(val)
    for list_key in ("paragraphs", "notes"):
        items = view.get(list_key)
        if isinstance(items, list):
            parts.extend(str(item) for item in items)
    table = view.get("table")
    if isinstance(table, dict):
        parts.extend(str(col) for col in table.get("columns", []))
        for row in table.get("rows", []):
            for cell in row:
                if isinstance(cell, dict):
                    parts.append(str(cell.get("label", "")))
                else:
                    parts.append(str(cell))
    return parts


def _unlocked_records_corpus(data: dict) -> str:
    chunks: list[str] = []
    for record in data.get("records", []):
        if record.get("requiresGate"):
            continue
        chunks.extend(_extract_view_strings(record))
        snapshot = record.get("snapshot")
        if isinstance(snapshot, dict):
            chunks.extend(_extract_view_strings(snapshot))
    return "\n".join(chunks)


def _iter_urls(data: dict) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for site in data.get("sites", []):
        for item in site.get("nav", []):
            found.append((f"site:{site['domain']}.nav", item["url"]))
        for item in site.get("links", []):
            found.append((f"site:{site['domain']}.links", item["url"]))
    for record in data.get("records", []):
        label = f"record:{record['site']}/{record['id']}"
        for item in record.get("links", []):
            found.append((f"{label}.links", item["url"]))
        snapshot = record.get("snapshot")
        if isinstance(snapshot, dict):
            for item in snapshot.get("links", []):
                found.append((f"{label}.snapshot.links", item["url"]))
    for check in data.get("checks", []):
        for item in check.get("leads", []):
            found.append((f"check:{check['id']}.leads", item["url"]))
        for item in check.get("links", []):
            found.append((f"check:{check['id']}.links", item["url"]))
    conclusion = data.get("conclusion")
    if isinstance(conclusion, dict):
        for item in conclusion.get("leads", []):
            found.append(("conclusion.leads", item["url"]))
        for item in conclusion.get("links", []):
            found.append(("conclusion.links", item["url"]))
    entry = data.get("entry")
    if isinstance(entry, dict):
        for item in entry.get("leads", []):
            found.append(("entry.leads", item["url"]))
        for item in entry.get("links", []):
            found.append(("entry.links", item["url"]))
    return found


def _valid_urls_for_dossier(data: dict, *, extra_roots: set[str] | None = None) -> set[str]:
    valid: set[str] = set(extra_roots or set())
    for site in data.get("sites", []):
        valid.add(f"https://{site['domain']}/")
    search = data.get("search")
    if isinstance(search, dict) and search.get("domain"):
        valid.add(f"https://{search['domain']}/")
    for record in data.get("records", []):
        valid.add(f"https://{record['site']}/{record['id']}")
    review_sites = [site for site in data.get("sites", []) if site.get("kind") == "review"]
    if review_sites:
        review_domain = review_sites[0]["domain"]
        for check in data.get("checks", []):
            valid.add(f"https://{review_domain}/{check['id']}")
        conclusion = data.get("conclusion")
        if isinstance(conclusion, dict):
            valid.add(f"https://{review_domain}/{conclusion['id']}")
    return valid


def _review_base(chapter: dict) -> str:
    return "https://" + next(site["domain"] for site in chapter["sites"] if site.get("kind") == "review") + "/"


def _navigate(page: Page, target: str) -> None:
    field = page.get_by_label("网址", exact=True)
    field.fill(target)
    field.press("Enter")
    expect(field).to_have_value(target)


def _search(page: Page, query: str) -> None:
    _navigate(page, SEARCH)
    field = page.get_by_role("searchbox", name="检索关键词")
    field.fill(query)
    field.press("Enter")


def _source(page: Page):
    page.get_by_role("button", name="查看源码").click()
    viewer = page.get_by_role("dialog")
    expect(viewer).to_be_visible()
    return viewer


def _submit(page: Page, work: dict, *, wrong: bool = False) -> None:
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


def _assert_wheel_scrolls_reel_horizontally(page: Page, route_label: str) -> None:
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
    page.wait_for_function("() => document.querySelector('[data-horizontal-reel]').scrollLeft > 0")
    page.wait_for_timeout(320)

    after = page.evaluate(
        """() => ({
            scrollLeft: document.querySelector('[data-horizontal-reel]').scrollLeft,
            scrollY: window.scrollY,
        })"""
    )
    assert after["scrollLeft"] > 0, f"Expected wheel to scroll horizontally on {route_label}"
    assert after["scrollY"] == 0, f"Expected window.scrollY === 0 on {route_label}, got {after['scrollY']}"


# ---------------------------------------------------------------------------
# 1. Data Integrity & Solvability Gate
# ---------------------------------------------------------------------------


def test_suojiang_data_integrity_and_solvability_gate() -> None:
    darun_files = [*(f"act-{n}" for n in range(1, 6)), "reading-room", "case_manifest"]
    darun_data = [_load_json_strict(name) for name in darun_files]
    darun_case_ids = {d["caseId"] for d in darun_data if "caseId" in d}
    darun_storage_keys = {d["storageKey"] for d in darun_data if "storageKey" in d}

    acts = [_load_json_strict(f"suojiang-act-{n}") for n in range(1, 6)]
    reading_room = _load_json_strict("suojiang-reading-room")
    finale = _load_json_strict("suojiang-finale-dossier")

    sj_case_ids = [*(act["caseId"] for act in acts), reading_room["caseId"]]
    sj_storage_keys = [*(act["storageKey"] for act in acts), reading_room["storageKey"]]
    assert len(set(sj_case_ids)) == 6
    assert len(set(sj_storage_keys)) == 6
    assert set(sj_case_ids).isdisjoint(darun_case_ids)
    assert set(sj_storage_keys).isdisjoint(darun_storage_keys)

    # Reading room validation
    assert reading_room["seriesKey"] == "suojiang"
    assert reading_room["archiveBrand"] == "锁江水文档案"
    assert reading_room["snapshotButtonLabels"] == {"enter": "切至极枯水位", "exit": "返回现行水位"}
    assert reading_room["records"] == []
    assert reading_room["dossierUrl"] == "/static/mystery/data/suojiang-finale-dossier.json"
    assert len(reading_room["sites"]) == 1
    assert reading_room["sites"][0]["kind"] == "entry"
    assert reading_room["sites"][0]["style"] == "directory"
    assert reading_room["entry"]["id"] == "collate-water"
    assert [field["accept"][0] for field in reading_room["entry"]["fields"]] == list(EXPECTED_SLIPS)
    finale_roots = {f"https://{site['domain']}/" for site in finale["sites"]}
    rr_valid_urls = _valid_urls_for_dossier(reading_room, extra_roots=finale_roots)
    for loc, url in _iter_urls(reading_room):
        assert url in rr_valid_urls, f"Dead URL in suojiang-reading-room.json ({loc}): {url}"

    # Acts 1-5 validation
    for index, (act, expected_slip) in enumerate(zip(acts, EXPECTED_SLIPS, strict=True), start=1):
        label = f"suojiang-act-{index}.json"
        assert act["caseId"] == f"CASE-SJ-0{index}"
        assert act["storageKey"] == f"suojiang_save_v1_ch0{index}"
        assert act["seriesKey"] == "suojiang"
        assert act["archiveBrand"] == "锁江水文档案"
        assert act["snapshotButtonLabels"] == {"enter": "切至极枯水位", "exit": "返回现行水位"}
        assert act["search"]["domain"] == "search.suojiang.lh"

        sites = act["sites"]
        assert len(sites) == 6, f"{label} expected 6 sites"
        assert sites[0]["style"] == "directory"
        assert sites[5]["style"] == "office" and sites[5].get("kind") == "review"
        assert {link["url"] for link in sites[0]["links"]} == {
            f"https://{site['domain']}/" for site in sites[1:]
        }
        for site in sites:
            assert site["style"] in ALLOWED_STYLES

        site_domains = {site["domain"] for site in sites}
        records = act["records"]
        route_pairs = {(record["site"], record["id"]) for record in records}
        assert len(records) >= 20, f"{label} expected >=20 records, got {len(records)}"
        assert len(route_pairs) == len(records), f"{label} has duplicate (site, id)"
        for record in records:
            assert record["site"] in site_domains, f"{label} invalid record site {record['site']}"
            assert record.get("paragraphs"), f"{label} empty paragraphs on {record['id']}"

        snapshots = [r for r in records if isinstance(r.get("snapshot"), dict)]
        assert len(snapshots) >= 2, f"{label} expected >=2 snapshot records"
        assert all(
            str(r["snapshot"].get("bannerText", "")).startswith("极枯水位 -2.4m 快照｜")
            for r in snapshots
        ), f"{label} missing custom snapshot bannerText"

        sources = [r for r in records if isinstance(r.get("source"), str) and "<!--" in r["source"]]
        assert len(sources) >= 2, f"{label} expected >=2 source comment records"
        assert any("守水人-壬" in r["source"] for r in sources)

        hidden = [r for r in records if r.get("listed") is False and r.get("index") == "site"]
        assert len(hidden) >= 2, f"{label} expected >=2 unlisted index:'site' records"

        checks = act["checks"]
        assert len(checks) == 6, f"{label} expected 6 checks"
        assert len({c["id"] for c in checks}) == 6
        conclusion = act["conclusion"]
        assert conclusion["id"] == "receipt"
        assert len(conclusion["fields"]) >= 4

        valid_urls = _valid_urls_for_dossier(act)
        for loc, url in _iter_urls(act):
            assert url in valid_urls, f"Dead URL in {label} ({loc}): {url}"

        corpus = _unlocked_records_corpus(act)
        for work in [*checks, conclusion]:
            assert len(work["fields"]) >= 3
            assert work["leads"] and work["receipt"]
            for field in work["fields"]:
                assert field["accept"], f"{label} empty accept on {work['id']}:{field['label']}"
                ans = field["accept"][0]
                assert ans in corpus, (
                    f"Solvability failure in {label} ({work['id']}:{field['label']}): "
                    f"accept[0]={ans!r} not verbatim in unlocked records"
                )

        assert conclusion["receipt"][-1].endswith(f"本卷水文回执签号：{expected_slip}。"), (
            f"{label} receipt[-1] mismatch: {conclusion['receipt'][-1]!r}"
        )
        raw_payload = json.dumps(act, ensure_ascii=False)
        assert "search.qiandu.lh" not in raw_payload
        assert "太闰" not in raw_payload

    # Finale dossier validation
    assert len(finale["sites"]) == 4
    for site in finale["sites"]:
        assert site["style"] in ALLOWED_STYLES
    assert finale["sites"][-1].get("kind") == "review"
    finale_domains = {site["domain"] for site in finale["sites"]}
    finale_records = finale["records"]
    finale_pairs = {(r["site"], r["id"]) for r in finale_records}
    assert len(finale_records) >= 14
    assert len(finale_pairs) == len(finale_records)
    for record in finale_records:
        assert record["site"] in finale_domains
        assert record.get("paragraphs")

    finale_snaps = [r for r in finale_records if isinstance(r.get("snapshot"), dict)]
    assert len(finale_snaps) >= 2
    assert all(
        str(r["snapshot"].get("bannerText", "")).startswith("极枯水位 -2.4m 快照｜")
        for r in finale_snaps
    )
    finale_sources = [r for r in finale_records if isinstance(r.get("source"), str) and "<!--" in r["source"]]
    assert len(finale_sources) >= 2

    closing_rec = next(
        r for r in finale_records if r["site"] == "yaoce.suojiang.lh" and r["id"] == "closing-slip"
    )
    assert closing_rec.get("requiresGate") == "filed:receipt"
    assert any(
        link["url"] == "https://yaoce.suojiang.lh/closing-slip"
        and link.get("requiresGate") == "filed:receipt"
        for link in finale["conclusion"]["links"]
    )

    assert len(finale["checks"]) == 4
    assert finale["conclusion"]["id"] == "receipt"
    finale_valid_urls = _valid_urls_for_dossier(finale)
    for loc, url in _iter_urls(finale):
        assert url in finale_valid_urls, f"Dead URL in suojiang-finale-dossier.json ({loc}): {url}"

    finale_corpus = _unlocked_records_corpus(finale)
    for work in [*finale["checks"], finale["conclusion"]]:
        assert len(work["fields"]) >= 3
        assert work["leads"] and work["receipt"]
        for field in work["fields"]:
            assert field["accept"]
            ans = field["accept"][0]
            assert ans in finale_corpus, (
                f"Solvability failure in suojiang-finale-dossier.json "
                f"({work['id']}:{field['label']}): accept[0]={ans!r} not verbatim in unlocked records"
            )


# ---------------------------------------------------------------------------
# 2. Two-Level Gallery, Theme Differentiation & Wheel-Scroll E2E
# ---------------------------------------------------------------------------


def test_suojiang_two_level_gallery_wheel_themes_and_overflow(browser: Browser, site_url: str) -> None:
    desktop = browser.new_page(viewport={"width": 1440, "height": 900})
    desktop_errors = _attach_error_collectors(desktop)
    try:
        desktop.goto(site_url + "/mystery/", wait_until="networkidle")
        expect(desktop.locator('[data-mystery-level="hub"]')).to_have_count(1)
        expect(desktop.locator(".hub-topbar-status")).to_contain_text("02 已开卷 / 02 筹备")
        expect(desktop.locator("[data-reel-card]")).to_have_count(5)
        expect(desktop.get_by_role("link", name="大闰录", exact=False)).to_be_visible()
        expect(desktop.get_by_role("link", name="锁江志", exact=False)).to_be_visible()
        expect(desktop.get_by_text("十音簿", exact=False)).to_be_visible()
        expect(desktop.get_by_text("敬请期待", exact=True)).to_be_visible()
        _assert_no_horizontal_overflow(desktop, "/mystery/", "1440x900")
        _assert_wheel_scrolls_reel_horizontally(desktop, "/mystery/")

        hub_theme = desktop.evaluate(
            """() => {
                const body = getComputedStyle(document.body);
                const card = getComputedStyle(document.querySelector('.hub-card--featured'));
                const topbar = getComputedStyle(document.querySelector('.hub-topbar'));
                return {
                    level: document.querySelector('[data-mystery-level]').getAttribute('data-mystery-level'),
                    bodyBg: body.backgroundColor,
                    cardBgImage: card.backgroundImage,
                    cardBorderColor: card.borderColor,
                    cardRadius: card.borderRadius,
                    clipPath: card.clipPath,
                    topbarBg: topbar.backgroundImage,
                };
            }"""
        )

        desktop.get_by_role("link", name="锁江志", exact=False).click()
        expect(desktop).to_have_url(site_url + "/mystery/suojiang/")
        expect(desktop.locator('[data-mystery-level="suojiang"]')).to_have_count(1)
        expect(desktop.locator("[data-reel-card]")).to_have_count(6)
        for act_title in (
            "第一幕 石鱼露背",
            "第二幕 断剑桥墩",
            "第三幕 借船过闸",
            "第四幕 暗渠行灯",
            "第五幕 锁江铁牛",
        ):
            expect(desktop.get_by_role("link", name=act_title, exact=False)).to_be_visible()
        expect(desktop.get_by_text("未完待续", exact=True)).to_be_visible()
        _assert_no_horizontal_overflow(desktop, "/mystery/suojiang/", "1440x900")
        _assert_wheel_scrolls_reel_horizontally(desktop, "/mystery/suojiang/")

        suojiang_theme = desktop.evaluate(
            """() => {
                const body = getComputedStyle(document.body);
                const card = getComputedStyle(document.querySelector('.sj-card--act'));
                const stele = getComputedStyle(document.querySelector('.sj-stele-surface'));
                const topbar = getComputedStyle(document.querySelector('.suojiang-topbar'));
                return {
                    level: document.querySelector('[data-mystery-level]').getAttribute('data-mystery-level'),
                    bodyBg: body.backgroundColor,
                    cardBgImage: stele.backgroundImage,
                    cardBorderColor: card.borderColor,
                    cardRadius: card.borderRadius,
                    clipPath: stele.clipPath,
                    topbarBg: topbar.backgroundImage,
                };
            }"""
        )

        desktop.goto(site_url + "/mystery/darun/", wait_until="networkidle")
        darun_theme = desktop.evaluate(
            """() => {
                const body = getComputedStyle(document.body);
                const card = getComputedStyle(document.querySelector('.darun-card--act'));
                const topbar = getComputedStyle(document.querySelector('.darun-topbar'));
                return {
                    level: document.querySelector('[data-mystery-level]').getAttribute('data-mystery-level'),
                    bodyBg: body.backgroundColor,
                    cardBgImage: card.backgroundImage,
                    cardBorderColor: card.borderColor,
                    cardRadius: card.borderRadius,
                    clipPath: card.clipPath,
                    topbarBg: topbar.backgroundImage,
                };
            }"""
        )

        assert suojiang_theme["level"] not in (hub_theme["level"], darun_theme["level"])
        assert suojiang_theme["bodyBg"] != hub_theme["bodyBg"]
        assert suojiang_theme["bodyBg"] != darun_theme["bodyBg"]
        assert suojiang_theme["cardBgImage"] != hub_theme["cardBgImage"]
        assert suojiang_theme["cardBgImage"] != darun_theme["cardBgImage"]
        assert suojiang_theme["cardBorderColor"] != hub_theme["cardBorderColor"]
        assert suojiang_theme["cardBorderColor"] != darun_theme["cardBorderColor"]
        assert suojiang_theme["cardRadius"] != hub_theme["cardRadius"]
        assert suojiang_theme["cardRadius"] != darun_theme["cardRadius"]
        assert suojiang_theme["clipPath"] != hub_theme["clipPath"]
        assert suojiang_theme["clipPath"] != darun_theme["clipPath"]
        assert suojiang_theme["topbarBg"] != darun_theme["topbarBg"]

        desktop.goto(site_url + "/mystery/suojiang/", wait_until="networkidle")
        desktop.get_by_text("未完待续", exact=True).click()
        desktop.get_by_role("link", name="核对水签").click()
        expect(desktop).to_have_url(site_url + "/mystery/suojiang/reading-room/")
        desktop.get_by_role("link", name="分卷目录").click()
        expect(desktop).to_have_url(site_url + "/mystery/suojiang/")
        desktop.get_by_role("link", name="系列总录").click()
        expect(desktop).to_have_url(site_url + "/mystery/")
        _assert_clean_page(desktop_errors, "suojiang two-level desktop")
    finally:
        desktop.close()

    mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    mobile_errors = _attach_error_collectors(mobile)
    try:
        mobile.goto(site_url + "/mystery/", wait_until="networkidle")
        expect(mobile.get_by_role("link", name="锁江志", exact=False)).to_be_visible()
        expect(mobile.get_by_text("敬请期待", exact=True)).to_be_visible()
        _assert_no_horizontal_overflow(mobile, "/mystery/", "390x844")

        mobile.get_by_role("link", name="锁江志", exact=False).click()
        expect(mobile).to_have_url(site_url + "/mystery/suojiang/")
        expect(mobile.locator("[data-horizontal-reel] a[href*='/act-']")).to_have_count(5)
        expect(mobile.get_by_text("未完待续", exact=True)).to_be_visible()
        _assert_no_horizontal_overflow(mobile, "/mystery/suojiang/", "390x844")

        mobile.get_by_text("未完待续", exact=True).click()
        expect(mobile.get_by_role("link", name="核对水签")).to_be_visible()
        _assert_no_horizontal_overflow(mobile, "/mystery/suojiang/#continuation", "390x844")
        _assert_clean_page(mobile_errors, "suojiang two-level mobile")
    finally:
        mobile.close()


# ---------------------------------------------------------------------------
# 3. Full Playable E2E Walkthroughs (Acts 1–5 + Reading Room + Finale)
# ---------------------------------------------------------------------------


def _assert_search_is_suojiang_only(page: Page) -> None:
    for forbidden_tab in DARUN_ONLY_SEARCH_TABS:
        expect(page.locator(f".site-search-tab:has-text('{forbidden_tab}')")).to_have_count(0)
    expect(page.locator(".site-search-tab")).to_have_count(1)
    expect(page.locator(".site-search-tab")).to_have_text("全部网页")


def test_suojiang_act_1_desktop_full_walkthrough(browser: Browser, site_url: str) -> None:
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = _attach_error_collectors(page)
    try:
        page.goto(site_url + "/mystery/", wait_until="networkidle")
        page.get_by_role("link", name="锁江志", exact=False).click()
        expect(page).to_have_url(site_url + "/mystery/suojiang/")
        page.get_by_role("link", name="第一幕 石鱼露背", exact=False).click()
        expect(page).to_have_url(site_url + "/mystery/suojiang/act-1/")
        expect(page.get_by_role("heading", name="沧江上游 · 夔滩站群存档目录")).to_be_visible()
        assert page.evaluate("() => document.body.dataset.series") == "suojiang"
        _assert_no_horizontal_overflow(page, "/mystery/suojiang/act-1/", "1440x900")

        # Snapshot toggle: 切至极枯水位 <-> 返回现行水位 + reload persistence
        _navigate(page, "https://shuiwen.kuitan.lh/gauge-log")
        expect(page.locator(".archive-site")).to_have_attribute("data-style", "hydro")
        snap_btn = page.locator("[data-snapshot]")
        expect(snap_btn).to_have_text("切至极枯水位")
        expect(snap_btn).to_have_attribute("aria-pressed", "false")
        snap_btn.click()
        expect(snap_btn).to_have_text("返回现行水位")
        expect(snap_btn).to_have_attribute("aria-pressed", "true")
        status_bar = page.locator("[data-reader-status]")
        expect(status_bar).to_be_visible()
        expect(status_bar).to_contain_text("极枯水位 -2.4m 快照")
        expect(page.locator(".archive-document")).to_contain_text("-2.4m")
        page.reload(wait_until="networkidle")
        expect(snap_btn).to_have_text("返回现行水位")
        expect(snap_btn).to_have_attribute("aria-pressed", "true")
        snap_btn.click()
        expect(snap_btn).to_have_text("切至极枯水位")
        expect(snap_btn).to_have_attribute("aria-pressed", "false")
        expect(status_bar).to_be_hidden()

        # Viewing source comment clue
        _navigate(page, "https://daba.kuitan.lh/discharge-notice")
        viewer = _source(page)
        expect(viewer.locator("pre")).to_contain_text("守水人-壬")
        expect(viewer.locator("pre")).to_contain_text("site:daba.kuitan.lh")
        viewer.get_by_role("button", name="关闭").click()

        # Search site: operator & isolation from Darun-only tabs
        _search(page, "原签底稿")
        _assert_search_is_suojiang_only(page)
        expect(page.locator('a[data-mystery-link="https://daba.kuitan.lh/dh114-draft"]')).to_have_count(0)
        _search(page, "site:daba.kuitan.lh DH-114")
        _assert_search_is_suojiang_only(page)
        hidden_link = page.locator('a[data-mystery-link="https://daba.kuitan.lh/dh114-draft"]')
        expect(hidden_link).to_be_visible()
        hidden_link.click()
        expect(page.locator(".archive-document")).to_contain_text("周广成")

        # Review checks & conclusion with wrong-answer rejection + reload persistence
        chapter = _load_json_strict("suojiang-act-1")
        base = _review_base(chapter)
        _navigate(page, base + chapter["conclusion"]["id"])
        expect(page.get_by_role("heading", name="待补材料")).to_be_visible()
        for index, work in enumerate(chapter["checks"]):
            _navigate(page, base + work["id"])
            if index == 0:
                _submit(page, work, wrong=True)
            _submit(page, work)
        _navigate(page, base + chapter["conclusion"]["id"])
        _submit(page, chapter["conclusion"], wrong=True)
        _submit(page, chapter["conclusion"])
        page.reload(wait_until="networkidle")
        expect(page.locator(".archive-receipt")).to_contain_text("本卷水文回执签号：SY。")
        assert page.evaluate("localStorage.getItem('suojiang_save_v1_ch01')") is not None
        assert page.evaluate("localStorage.getItem('darun_save_v1_ch01')") is None

        # Strip navigation: 分卷目录 -> /mystery/suojiang/, 系列总录 -> /mystery/
        page.get_by_role("link", name="分卷目录").click()
        expect(page).to_have_url(site_url + "/mystery/suojiang/")
        page.goto(site_url + "/mystery/suojiang/act-1/", wait_until="networkidle")
        page.get_by_role("link", name="系列总录").click()
        expect(page).to_have_url(site_url + "/mystery/")
        _assert_clean_page(errors, "suojiang act 1 desktop")
    finally:
        page.close()


@pytest.mark.parametrize(
    "volume,landing,snapshot_url,snapshot_text,source_url,source_snippet,"
    "hidden_domain,hidden_query,hidden_url,hidden_text,slip",
    [
        (
            1,
            "沧江上游 · 夔滩站群存档目录",
            "https://shiyu.kuitan.lh/fish-rubbing",
            "让槽三丈",
            "https://shuiwen.kuitan.lh/duty-roster",
            "site:shuiwen.kuitan.lh",
            "shuiwen.kuitan.lh",
            "标尺袋",
            "https://shuiwen.kuitan.lh/kt09-handover",
            "SJ-61",
            "SY",
        ),
        (
            2,
            "沧江中上游 · 龙门渡站群存档目录",
            "https://qiaodun.longmen.lh/pier-scan",
            "水泥封槽",
            "https://dukou.longmen.lh/scrap-rumor",
            "兴隆铁厂",
            "hangdao.longmen.lh",
            "兴隆铁厂",
            "https://hangdao.longmen.lh/scrap-receipt",
            "定界三分",
            "DJ",
        ),
        (
            3,
            "淮阴船闸与水文旧站总目",
            "https://shuiqing.huaiyin.lh/sensor-feed",
            "610吨",
            "https://chuanzha.huaiyin.lh/dispatch-board",
            "HY-019",
            "chuanzha.huaiyin.lh",
            "HY-019",
            "https://chuanzha.huaiyin.lh/hy019-memo",
            "赵明远",
            "GZ",
        ),
        (
            4,
            "临安坊排水、城建与古城舆图存档目录",
            "https://paishui.linan.lh/pump4-log",
            "7盏",
            "https://shizheng.linan.lh/plaza-foundation",
            "LA-304",
            "paishui.linan.lh",
            "D-4检修口",
            "https://paishui.linan.lh/d4-redpen",
            "GZ",
            "HD",
        ),
        (
            5,
            "崇沙洲江口水文档案旧站目录",
            "https://tieniu.chongsha.lh/ox-base",
            "松链纳潮",
            "https://haishi.chongsha.lh/dredge-bulletin",
            "CS-508",
            "tieniu.chongsha.lh",
            "水签匣",
            "https://tieniu.chongsha.lh/kt09-estuary",
            "SJ-61-RESET",
            "TN",
        ),
    ],
)
def test_suojiang_acts_mobile_subpath_completion(
    browser: Browser,
    subpath_url: str,
    volume: int,
    landing: str,
    snapshot_url: str,
    snapshot_text: str,
    source_url: str,
    source_snippet: str,
    hidden_domain: str,
    hidden_query: str,
    hidden_url: str,
    hidden_text: str,
    slip: str,
) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    errors = _attach_error_collectors(page)
    try:
        page.goto(subpath_url + f"/mystery/suojiang/act-{volume}/", wait_until="networkidle")
        expect(page.get_by_role("heading", name=landing)).to_be_visible()
        _assert_no_horizontal_overflow(page, page.url, f"act-{volume}-mobile")

        # Low-water snapshot toggle & custom hydro banner
        _navigate(page, snapshot_url)
        snap_btn = page.locator("[data-snapshot]")
        expect(snap_btn).to_have_text("切至极枯水位")
        snap_btn.click()
        expect(snap_btn).to_have_text("返回现行水位")
        expect(snap_btn).to_have_attribute("aria-pressed", "true")
        expect(page.locator("[data-reader-status]")).to_contain_text("极枯水位 -2.4m 快照")
        expect(page.locator(".archive-document")).to_contain_text(snapshot_text)
        _assert_no_horizontal_overflow(page, page.url, f"act-{volume}-snapshot-mobile")
        snap_btn.click()
        expect(snap_btn).to_have_text("切至极枯水位")
        expect(page.locator("[data-reader-status]")).to_be_hidden()

        # HTML source viewer
        _navigate(page, source_url)
        dialog = _source(page)
        expect(dialog.locator("pre")).to_contain_text("守水人-壬")
        expect(dialog.locator("pre")).to_contain_text(source_snippet)
        dialog.get_by_role("button", name="关闭").click()

        # Search operator & absence of Darun-only tabs
        _search(page, hidden_query)
        _assert_search_is_suojiang_only(page)
        expect(page.locator(f'a[data-mystery-link="{hidden_url}"]')).to_have_count(0)
        _search(page, f"site:{hidden_domain} {hidden_query}")
        _assert_search_is_suojiang_only(page)
        hidden_link = page.locator(f'a[data-mystery-link="{hidden_url}"]')
        expect(hidden_link).to_be_visible()
        hidden_link.click()
        expect(page.locator(".archive-document")).to_contain_text(hidden_text)
        _assert_no_horizontal_overflow(page, page.url, f"act-{volume}-hidden-mobile")

        # Complete all 6 checks + conclusion
        chapter = _load_json_strict(f"suojiang-act-{volume}")
        base = _review_base(chapter)
        for index, work in enumerate(chapter["checks"]):
            _navigate(page, base + work["id"])
            if index == 0:
                _submit(page, work, wrong=True)
            _submit(page, work)
        _navigate(page, base + chapter["conclusion"]["id"])
        _submit(page, chapter["conclusion"], wrong=True)
        _submit(page, chapter["conclusion"])
        page.reload(wait_until="networkidle")
        expect(page.locator(".archive-receipt")).to_contain_text(f"本卷水文回执签号：{slip}。")
        assert page.evaluate("localStorage.getItem('darun_save_v1_ch01')") is None
        for other_vol in range(1, 6):
            if other_vol != volume:
                assert page.evaluate(f"localStorage.getItem('suojiang_save_v1_ch0{other_vol}')") is None

        # Strip back navigation under subpath
        page.get_by_role("link", name="分卷目录").click()
        expect(page).to_have_url(subpath_url + "/mystery/suojiang/")
        page.get_by_role("link", name="系列总录").click()
        expect(page).to_have_url(subpath_url + "/mystery/")
        _assert_clean_page(errors, f"suojiang act {volume} mobile subpath")
    finally:
        page.close()


def test_suojiang_reading_room_and_finale_subpath(browser: Browser, subpath_url: str) -> None:
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = _attach_error_collectors(page)
    requests: list[str] = []
    page.on("request", lambda request: requests.append(request.url))
    try:
        page.goto(subpath_url + "/mystery/suojiang/", wait_until="networkidle")
        page.get_by_text("未完待续", exact=True).click()
        page.get_by_role("link", name="核对水签").click()
        expect(page).to_have_url(subpath_url + "/mystery/suojiang/reading-room/")
        expect(page.locator("meta[name=robots]")).to_have_attribute("content", "noindex")
        expect(page.get_by_role("heading", name="五卷水文回执签号合验")).to_be_visible()
        assert not any(url.endswith("/suojiang-finale-dossier.json") for url in requests)

        # Finale dossier must not be reachable before submitting valid SY/DJ/GZ/HD/TN
        _navigate(page, "https://shuifu.suojiang.lh/")
        expect(page.get_by_role("heading", name="该网址没有存入本卷")).to_be_visible()

        entry = _load_json_strict("suojiang-reading-room")
        _navigate(page, entry["homeUrl"])
        _submit(page, entry["entry"], wrong=True)
        assert not any(url.endswith("/suojiang-finale-dossier.json") for url in requests)

        _submit(page, entry["entry"])
        assert any(url.endswith("/suojiang-finale-dossier.json") for url in requests)
        page.get_by_role("link", name="锁江总录 · 龙门水府密档").click()
        expect(page.get_by_role("heading", name="沧江流域五契总勘")).to_be_visible()
        _assert_no_horizontal_overflow(page, page.url, "finale-shuifu-1440x900")

        # Closing slip must remain gated until finale conclusion is filed
        closing_url = "https://yaoce.suojiang.lh/closing-slip"
        _navigate(page, closing_url)
        expect(page.get_by_role("heading", name="此页未归档")).to_be_visible()

        # Verify low-water snapshot reveals meta-host & grand principle, and source reveals 观澜_61 / 守水人-壬
        _navigate(page, "https://yaoce.suojiang.lh/host-drift")
        page.locator("[data-snapshot]").click()
        expect(page.locator(".archive-document")).to_contain_text("星环手记")
        expect(page.locator("[data-reader-status]")).to_contain_text("极枯水位 -2.4m 快照")
        viewer = _source(page)
        expect(viewer.locator("pre")).to_contain_text("观澜_61")
        viewer.get_by_role("button", name="关闭").click()

        _navigate(page, "https://guqi.suojiang.lh/warden-lineage")
        warden_viewer = _source(page)
        expect(warden_viewer.locator("pre")).to_contain_text("守水人-壬")
        warden_viewer.get_by_role("button", name="关闭").click()

        _navigate(page, "https://guqi.suojiang.lh/scroll-origin")
        page.locator("[data-snapshot]").click()
        expect(page.locator(".archive-document")).to_contain_text("水有旧道，蛟行不改")
        expect(page.locator(".archive-document")).to_contain_text("留旧槽立复契")

        dossier = _load_json_strict("suojiang-finale-dossier")
        base = _review_base(dossier)
        _navigate(page, base + "receipt")
        expect(page.get_by_role("heading", name="待补材料")).to_be_visible()
        for index, work in enumerate(dossier["checks"]):
            _navigate(page, base + work["id"])
            if index == 0:
                _submit(page, work, wrong=True)
            _submit(page, work)

        _navigate(page, base + "receipt")
        _submit(page, dossier["conclusion"], wrong=True)
        _submit(page, dossier["conclusion"])
        page.reload(wait_until="networkidle")
        expect(page.locator(".archive-receipt")).to_contain_text("【锁江总录完】")
        expect(page.locator(".archive-receipt")).to_contain_text("星环手记")

        # Closing slip unlocks after filing conclusion receipt
        page.get_by_role("link", name="沈砚青留笺 · 归道之后").click()
        expect(page.get_by_role("heading", name="沈砚青留笺 · 归道之后")).to_be_visible()
        expect(page.locator(".archive-document")).to_contain_text("KT-09 沈砚青")
        _assert_no_horizontal_overflow(page, page.url, "finale-closing-slip-1440x900")

        page.get_by_role("link", name="分卷目录").click()
        expect(page).to_have_url(subpath_url + "/mystery/suojiang/")
        page.get_by_role("link", name="系列总录").click()
        expect(page).to_have_url(subpath_url + "/mystery/")
        _assert_clean_page(errors, "suojiang reading room & finale subpath")
    finally:
        page.close()


def _assert_suojiang_reader_layout(page: Page, selector: str, viewport: str) -> None:
    reader = page.locator("[data-viewport]")
    expect(reader.locator(selector).first).to_be_visible()
    visible_text = reader.inner_text()
    assert not any(icon in visible_text for icon in ("⚠", "⏱")), page.url
    _assert_no_horizontal_overflow(page, page.url, viewport)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        f"Horizontal overflow on {page.url} ({viewport})"
    )


def test_suojiang_real_site_layouts_and_anti_highlight(browser: Browser, site_url: str) -> None:
    act_one = "/mystery/suojiang/act-1/"
    act_two = "/mystery/suojiang/act-2/"
    reading_room = "/mystery/suojiang/reading-room/"
    routes = (
        (act_one, "https://index.kuitan.lh/", ".arch-dir-grid"),
        (act_one, "https://daba.kuitan.lh/", ".arch-layout--sidebar-left .arch-doc--redhead"),
        (act_one, "https://jiangyu.kuitan.lh/", ".arch-doc--bbs .archive-table"),
        (act_one, "https://shiyu.kuitan.lh/", ".arch-layout--library .arch-biblio-card"),
        (act_one, "https://shuiwen.kuitan.lh/gauge-log", ".arch-layout--hydro .arch-hydro-tree"),
        (act_one, "https://hecha.kuitan.lh/", ".arch-doc--hall .arch-hall-steps"),
        (act_two, "https://hangdao.longmen.lh/sonar-night", ".arch-layout--sidebar-right .arch-maritime-duty"),
    )
    chapter = _load_json_strict("suojiang-act-1")
    entry = _load_json_strict("suojiang-reading-room")
    review_url = _review_base(chapter)
    work, next_work = chapter["checks"][:2]

    for width, height in ((1440, 900), (390, 844)):
        viewport = f"{width}x{height}"
        page = browser.new_page(
            viewport={"width": width, "height": height},
            is_mobile=width < 768,
            has_touch=width < 768,
        )
        errors = _attach_error_collectors(page)
        try:
            for path, target, selector in routes:
                if path != act_one or not page.url.startswith(site_url + act_one):
                    page.goto(site_url + path, wait_until="networkidle")
                _navigate(page, target)
                _assert_suojiang_reader_layout(page, selector, viewport)

            page.goto(site_url + reading_room, wait_until="networkidle")
            if page.locator("[data-review-form]").is_visible():
                _submit(page, entry["entry"])
            page.get_by_role("link", name="锁江总录 · 龙门水府密档", exact=True).click()
            _assert_suojiang_reader_layout(page, ".arch-layout--workbench .arch-vault-rail", viewport)

            page.goto(site_url + act_one, wait_until="networkidle")
            page.evaluate("(key) => localStorage.removeItem(key)", chapter["storageKey"])
            page.reload(wait_until="networkidle")
            _navigate(page, review_url + work["id"])
            _submit(page, work)
            doc = page.locator(".archive-document")
            expect(doc.locator(".archive-receipt")).to_be_visible()
            progression = doc.locator(f'a[data-mystery-link="{review_url}{next_work["id"]}"]')
            expect(progression).to_be_visible()
            expect(doc.get_by_role("link", name="返回收件目录", exact=True)).to_have_attribute(
                "data-mystery-link", review_url
            )
            _assert_suojiang_reader_layout(page, ".archive-receipt", viewport)
            progression.click()
            expect(page.get_by_role("heading", name=next_work["title"], exact=True)).to_be_visible()
            _assert_clean_page(errors, f"suojiang layout & anti-highlight {viewport}")
        finally:
            page.close()
