"""Full-pipeline static site build and quality gate checker.

Runs ``scripts/build.py`` to regenerate ``dist/``, verifies all required build
artifacts (including ``.nojekyll`` and optional ``CNAME``) exist, checks static
image/CSS assets, validates JSON feeds and XML sitemaps/RSS, ensures zero
unreplaced ``{{...}}`` template placeholders remain, and verifies every internal
``href`` and ``src`` across all generated HTML pages (supporting root and
GitHub Pages ``--base-path`` subpath deployments).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.content_loader import load_posts  # noqa: E402

BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build.py"
CONTENT_DIR = PROJECT_ROOT / "content"
SITE_JSON_PATH = PROJECT_ROOT / "content" / "site.json"
STATIC_SRC_DIR = PROJECT_ROOT / "static"
DIST_DIR = PROJECT_ROOT / "dist"

REQUIRED_FILES = (
    "index.html",
    "articles/index.html",
    "projects/index.html",
    "gallery/index.html",
    "about/index.html",
    "404.html",
    "api/posts.json",
    "api/projects.json",
    "api/gallery.json",
    "api/search-index.json",
    "rss.xml",
    "sitemap.xml",
    "robots.txt",
)

REQUIRED_ALLOW_EMPTY_FILES = (".nojekyll",)

REQUIRED_IMAGE_ASSETS = (
    "static/images/starloop-cover.jpg",
    "static/images/astra-portrait.jpg",
    "static/images/favicon.svg",
    "static/images/author-mark.svg",
    "static/images/cover-01.svg",
    "static/images/cover-02.svg",
    "static/images/cover-03.svg",
    "static/images/cover-04.svg",
    "static/images/cover-05.svg",
)

PLACEHOLDER_RE = re.compile(r"\{\{[a-zA-Z0-9_]+\}\}")
CSS_URL_RE = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""")


@dataclass(frozen=True)
class LinkReference:
    """Represents an internal ``href`` or ``src`` found in a generated HTML file."""

    tag: str
    attr: str
    raw_url: str
    line: int
    column: int


class InternalLinkExtractor(HTMLParser):
    """HTML parser that extracts root-relative links and ``site-base-path`` meta."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[LinkReference] = []
        self.meta_base_path: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line, col = self.getpos()
        attr_map = dict(attrs)
        if tag == "meta" and attr_map.get("name") == "site-base-path":
            self.meta_base_path = attr_map.get("content")

        for attr_name, attr_val in attrs:
            if attr_name not in ("href", "src", "data-image") or attr_val is None:
                continue
            value = attr_val.strip()
            if value.startswith("/") and not value.startswith("//"):
                self.links.append(
                    LinkReference(
                        tag=tag,
                        attr=attr_name,
                        raw_url=value,
                        line=line,
                        column=col,
                    )
                )


def _configure_stdio() -> None:
    """Avoid UnicodeEncodeError on Windows terminals with legacy codepages."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def normalize_base_path(raw: str | None) -> str:
    """Normalize a deployment subpath into ``''`` or ``'/subpath'``."""
    if not raw:
        return ""
    cleaned = raw.strip()
    if not cleaned or cleaned == "/":
        return ""
    return "/" + cleaned.strip("/")


def _normalize_cname(raw: str | None) -> str:
    """Normalize an optional custom domain to bare hostname (or empty string)."""
    if not raw:
        return ""
    cleaned = raw.strip()
    cleaned = re.sub(r"^https?://", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.split("/", 1)[0].strip()
    return cleaned


def _expected_cname(cli_cname: str) -> str:
    """Determine expected CNAME domain from CLI override or ``content/site.json``."""
    explicit = _normalize_cname(cli_cname)
    if explicit:
        return explicit
    if SITE_JSON_PATH.is_file():
        try:
            site_data = json.loads(SITE_JSON_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return ""
        if isinstance(site_data, dict):
            return _normalize_cname(str(site_data.get("custom_domain") or ""))
    return ""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse optional deployment flags forwarded to ``scripts/build.py``."""
    parser = argparse.ArgumentParser(
        description="Build the static site and run all quality gate checks."
    )
    parser.add_argument(
        "--base-path",
        default=os.environ.get("SITE_BASE_PATH", ""),
        help="Deployment subpath prefix, e.g. /astrayao-blog (default: '')",
    )
    parser.add_argument(
        "--site-url",
        default=os.environ.get("SITE_URL") or None,
        help="Override canonical/RSS/Sitemap site_url",
    )
    parser.add_argument(
        "--cname",
        default=os.environ.get("SITE_CNAME", ""),
        help="Optional custom domain for dist/CNAME",
    )
    return parser.parse_args(argv)


def run_build(base_path: str = "", site_url: str | None = None, cname: str = "") -> list[str]:
    """Execute ``scripts/build.py`` and return any fatal errors."""
    if not BUILD_SCRIPT.is_file():
        return [f"Missing build script: {BUILD_SCRIPT}"]

    cmd = [sys.executable, str(BUILD_SCRIPT), "--base-path", base_path]
    if site_url:
        cmd.extend(["--site-url", site_url])
    if cname:
        cmd.extend(["--cname", cname])

    print(f"[check] Running build script: {' '.join(cmd[1:])}")
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return [f"scripts/build.py exited with non-zero status: {result.returncode}"]
    return []


def check_required_files(dist_dir: Path, expected_cname: str = "") -> list[str]:
    """Verify mandatory static pages, feeds, ``.nojekyll``, and ``CNAME`` state."""
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        target = dist_dir / rel
        if not target.is_file():
            errors.append(f"Missing required artifact: dist/{rel}")
        elif target.stat().st_size == 0:
            errors.append(f"Artifact is empty: dist/{rel}")

    for rel in REQUIRED_ALLOW_EMPTY_FILES:
        target = dist_dir / rel
        if not target.is_file():
            errors.append(f"Missing required artifact: dist/{rel}")

    cname_path = dist_dir / "CNAME"
    if expected_cname:
        if not cname_path.is_file():
            errors.append(f"Expected dist/CNAME for domain '{expected_cname}', but file is missing.")
        else:
            actual = cname_path.read_text(encoding="utf-8").strip()
            if actual != expected_cname:
                errors.append(
                    f"dist/CNAME mismatch: expected '{expected_cname}', got '{actual}'."
                )
    elif cname_path.exists():
        errors.append("Unexpected dist/CNAME present when no custom domain is configured.")

    return errors


def _extract_list_payload(data: object, candidate_keys: tuple[str, ...]) -> list[object] | None:
    """Return a list payload directly or from one of ``candidate_keys``."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in candidate_keys:
            val = data.get(key)
            if isinstance(val, list):
                return val
    return None


def check_json_and_posts(
    dist_dir: Path, base_path: str = "", *, content_dir: Path = CONTENT_DIR
) -> tuple[list[str], int, int]:
    """Validate JSON outputs and verify every published post detail page exists."""
    errors: list[str] = []
    posts_count = 0
    search_count = 0

    posts_json_path = dist_dir / "api" / "posts.json"
    search_json_path = dist_dir / "api" / "search-index.json"

    post_slugs_from_api: set[str] = set()
    search_slugs: set[str] = set()
    if posts_json_path.is_file():
        try:
            posts_data = json.loads(posts_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in dist/api/posts.json: {exc}")
        else:
            posts_list = _extract_list_payload(posts_data, ("posts", "items", "articles"))
            if posts_list is None:
                errors.append("dist/api/posts.json must contain a list of posts.")
            else:
                posts_count = len(posts_list)
                if isinstance(posts_data, dict) and "total" in posts_data:
                    if posts_data["total"] != posts_count:
                        errors.append(
                            f"dist/api/posts.json 'total' ({posts_data['total']}) "
                            f"does not match len(posts) ({posts_count})."
                        )
                if isinstance(posts_data, dict) and "categories" in posts_data:
                    cats_val = posts_data["categories"]
                    if not isinstance(cats_val, list):
                        errors.append("dist/api/posts.json field 'categories' must be a list.")
                    else:
                        for cidx, cat in enumerate(cats_val):
                            if not isinstance(cat, dict) or not cat.get("name"):
                                errors.append(
                                    f"dist/api/posts.json categories[{cidx}] missing 'name'."
                                )
                for idx, entry in enumerate(posts_list):
                    if not isinstance(entry, dict) or not entry.get("slug"):
                        errors.append(f"dist/api/posts.json entry #{idx} missing 'slug'.")
                        continue
                    slug = str(entry["slug"])
                    post_slugs_from_api.add(slug)
                    detail_html = dist_dir / "articles" / slug / "index.html"
                    if not detail_html.is_file():
                        errors.append(
                            f"Missing article detail page for slug '{slug}': "
                            f"dist/articles/{slug}/index.html"
                        )
                    if base_path:
                        expected_url = f"{base_path}/articles/{slug}/"
                        if entry.get("url") != expected_url:
                            errors.append(
                                f"dist/api/posts.json entry #{idx} url '{entry.get('url')}' "
                                f"expected '{expected_url}'."
                            )
                        cover = str(entry.get("cover") or "")
                        if cover.startswith("/") and not cover.startswith(f"{base_path}/"):
                            errors.append(
                                f"dist/api/posts.json entry #{idx} cover '{cover}' "
                                f"missing base_path '{base_path}'."
                            )

    if search_json_path.is_file():
        try:
            search_data = json.loads(search_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in dist/api/search-index.json: {exc}")
        else:
            search_list = _extract_list_payload(
                search_data, ("items", "posts", "documents", "index")
            )
            if search_list is None:
                errors.append(
                    "dist/api/search-index.json must contain a list of entries."
                )
            else:
                search_count = len(search_list)
                required_search_keys = (
                    "title",
                    "slug",
                    "url",
                    "date",
                    "category",
                    "tags",
                    "summary",
                    "excerpt",
                    "reading_time",
                )
                for idx, entry in enumerate(search_list):
                    if not isinstance(entry, dict):
                        errors.append(f"dist/api/search-index.json entry #{idx} is not an object.")
                        continue
                    for req_key in required_search_keys:
                        if req_key not in entry:
                            errors.append(
                                f"dist/api/search-index.json entry #{idx} missing '{req_key}'."
                            )
                        elif req_key in ("title", "slug", "url") and not entry.get(req_key):
                            errors.append(
                                f"dist/api/search-index.json entry #{idx} has empty '{req_key}'."
                            )
                    if "tags" in entry and not isinstance(entry["tags"], list):
                        errors.append(
                            f"dist/api/search-index.json entry #{idx} field 'tags' must be a list."
                        )
                    if entry.get("slug"):
                        search_slugs.add(str(entry["slug"]))
                    if base_path and entry.get("slug"):
                        expected_url = f"{base_path}/articles/{entry['slug']}/"
                        if entry.get("url") != expected_url:
                            errors.append(
                                f"dist/api/search-index.json entry #{idx} url "
                                f"'{entry.get('url')}' expected '{expected_url}'."
                            )

    source_slugs = {post.slug for post in load_posts(content_dir)}
    for label, slugs, count in (
        ("posts.json", post_slugs_from_api, posts_count),
        ("search-index.json", search_slugs, search_count),
    ):
        if slugs != source_slugs or count != len(source_slugs):
            errors.append(f"dist/api/{label} does not match the published article sources.")

    articles_dir = dist_dir / "articles"
    for detail_html in sorted(articles_dir.rglob("index.html")):
        slug = detail_html.parent.relative_to(articles_dir).as_posix()
        if slug != "." and slug not in source_slugs:
            errors.append(f"Stale article detail page: {detail_html.relative_to(dist_dir)}")

    category_registries = (
        ("categories.json", dist_dir / "articles" / "index.html", "articles/index.html", False),
        ("project_categories.json", dist_dir / "projects" / "index.html", "projects/index.html", True),
        ("gallery_categories.json", dist_dir / "gallery" / "index.html", "gallery/index.html", True),
    )
    for json_name, page_path, page_label, required in category_registries:
        reg_path = content_dir / json_name
        if not reg_path.is_file():
            if required:
                errors.append(f"Missing required category registry: content/{json_name}")
            continue
        try:
            reg_data = json.loads(reg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in content/{json_name}: {exc}")
            continue
        if not isinstance(reg_data, list):
            errors.append(f"content/{json_name} must be a JSON array.")
            continue

        page_html = page_path.read_text(encoding="utf-8") if page_path.is_file() else ""
        if page_html:
            if "data-category-bar" not in page_html or "data-category-indicator" not in page_html:
                errors.append(
                    f"Missing category bar/indicator hooks in dist/{page_label}"
                )
            if 'data-filter-category="all"' not in page_html:
                errors.append(
                    f"Missing 'all' category tab in dist/{page_label}"
                )
        for idx, cat in enumerate(reg_data):
            if not isinstance(cat, dict) or not str(cat.get("name", "")).strip():
                errors.append(f"content/{json_name} entry #{idx} missing 'name'.")
                continue
            cat_name = str(cat["name"]).strip()
            esc_cat_name = html.escape(cat_name, quote=True)
            if page_html and f'data-filter-category="{esc_cat_name}"' not in page_html:
                errors.append(
                    f"Category '{cat_name}' from content/{json_name} missing from dist/{page_label}"
                )

    for api_name, list_key, source_name, url_field in (
        ("projects.json", "projects", "projects.json", "url"),
        ("gallery.json", "items", "gallery.json", "image"),
    ):
        api_path = dist_dir / "api" / api_name
        if not api_path.is_file():
            continue
        try:
            api_data = json.loads(api_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in dist/api/{api_name}: {exc}")
            continue
        if not isinstance(api_data, dict):
            errors.append(f"dist/api/{api_name} must be a JSON object.")
            continue
        items_list = api_data.get(list_key)
        if not isinstance(items_list, list):
            errors.append(f"dist/api/{api_name} missing list field '{list_key}'.")
            continue
        if "total" in api_data and api_data["total"] != len(items_list):
            errors.append(
                f"dist/api/{api_name} 'total' ({api_data['total']}) "
                f"does not match len({list_key}) ({len(items_list)})."
            )
        src_path = content_dir / source_name
        if src_path.is_file():
            try:
                src_items = json.loads(src_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid JSON in content/{source_name}: {exc}")
            else:
                if not isinstance(src_items, list):
                    errors.append(f"content/{source_name} must be a JSON array.")
                elif len(items_list) != len(src_items):
                    errors.append(
                        f"dist/api/{api_name} count ({len(items_list)}) "
                        f"does not match content/{source_name} ({len(src_items)})."
                    )
        if "categories" in api_data:
            if not isinstance(api_data["categories"], list):
                errors.append(f"dist/api/{api_name} field 'categories' must be a list.")
            else:
                for cidx, cat in enumerate(api_data["categories"]):
                    if not isinstance(cat, dict) or not cat.get("name"):
                        errors.append(f"dist/api/{api_name} categories[{cidx}] missing 'name'.")
        if base_path:
            for idx, item in enumerate(items_list):
                if not isinstance(item, dict):
                    continue
                val = str(item.get(url_field) or "")
                if val.startswith("/") and not val.startswith("//") and not val.startswith(f"{base_path}/"):
                    errors.append(
                        f"dist/api/{api_name} {list_key}[{idx}].{url_field} '{val}' "
                        f"missing base_path '{base_path}'."
                    )

    return errors, posts_count, search_count


def check_xml_files(dist_dir: Path, base_path: str = "", *, posts_count: int) -> list[str]:
    """Parse ``rss.xml`` and ``sitemap.xml`` via ElementTree to verify validity."""
    errors: list[str] = []
    double_prefix = f"{base_path}{base_path}/" if base_path else ""

    rss_path = dist_dir / "rss.xml"
    if rss_path.is_file():
        try:
            rss_root = ET.fromstring(rss_path.read_text(encoding="utf-8"))
        except ET.ParseError as exc:
            errors.append(f"Invalid XML in dist/rss.xml: {exc}")
        else:
            if rss_root.tag != "rss":
                errors.append(f"dist/rss.xml root element must be <rss>, got <{rss_root.tag}>")
            channel = rss_root.find("channel")
            if channel is None:
                errors.append("dist/rss.xml missing <channel> element.")
            else:
                items = channel.findall("item")
                if len(items) != posts_count:
                    errors.append(f"dist/rss.xml has {len(items)} items, expected {posts_count}.")
                if double_prefix:
                    for el in channel.iter():
                        if el.text and double_prefix in el.text:
                            errors.append(
                                f"Duplicate base_path '{double_prefix}' in dist/rss.xml: {el.text}"
                            )

    sitemap_path = dist_dir / "sitemap.xml"
    if sitemap_path.is_file():
        try:
            sm_root = ET.fromstring(sitemap_path.read_text(encoding="utf-8"))
        except ET.ParseError as exc:
            errors.append(f"Invalid XML in dist/sitemap.xml: {exc}")
        else:
            local_tag = sm_root.tag.rsplit("}", 1)[-1]
            if local_tag != "urlset":
                errors.append(
                    f"dist/sitemap.xml root element must be <urlset>, got <{sm_root.tag}>"
                )
            urls = [el for el in sm_root if el.tag.rsplit("}", 1)[-1] == "url"]
            expected_min_urls = 5 + posts_count
            if len(urls) < expected_min_urls:
                errors.append(
                    f"dist/sitemap.xml has {len(urls)} <url> entries, expected at least "
                    f"{expected_min_urls} (5 core pages + {posts_count} posts)."
                )
            else:
                locs: list[str] = []
                for url_el in urls:
                    for child in url_el:
                        if child.tag.rsplit("}", 1)[-1] == "loc" and child.text:
                            locs.append(child.text.strip())
                        if double_prefix and child.text and double_prefix in child.text:
                            errors.append(
                                f"Duplicate base_path '{double_prefix}' in dist/sitemap.xml: "
                                f"{child.text}"
                            )
                if not any(loc.endswith("/gallery/") for loc in locs):
                    errors.append("dist/sitemap.xml missing '/gallery/' entry.")

    return errors


def _strip_base_path(decoded_path: str, base_path: str, require_prefix: bool) -> str | None:
    """Validate and strip ``base_path`` from a decoded root-relative URL path."""
    if not base_path:
        return decoded_path
    if decoded_path == base_path:
        return "/"
    if decoded_path.startswith(base_path + "/"):
        return decoded_path[len(base_path):]
    if require_prefix:
        return None
    return decoded_path


def _resolve_internal_target(
    dist_dir: Path,
    raw_url: str,
    base_path: str = "",
    require_base_prefix: bool = False,
) -> tuple[bool, str]:
    """Resolve ``raw_url`` inside ``dist_dir`` and return ``(ok, reason)``."""
    parsed = urllib.parse.urlsplit(raw_url)
    decoded_path = urllib.parse.unquote(parsed.path)

    stripped_path = _strip_base_path(decoded_path, base_path, require_prefix=require_base_prefix)
    if stripped_path is None:
        return False, f"missing base_path prefix '{base_path}'"

    rel = stripped_path.lstrip("/")
    dist_root = dist_dir.resolve()
    if rel == "":
        candidate = (dist_root / "index.html").resolve()
        if candidate.is_file() and candidate.stat().st_size > 0:
            return True, ""
        return False, "dist/index.html missing or empty"

    target = (dist_root / rel).resolve()
    try:
        target.relative_to(dist_root)
    except ValueError:
        return False, "path escapes dist/"

    if target.is_file():
        return (target.stat().st_size > 0, "target file is empty")
    dir_index = (target / "index.html").resolve()
    if dir_index.is_file() and dir_index.stat().st_size > 0:
        return True, ""
    return False, f"target not found under dist/{rel}"


def check_static_assets(dist_dir: Path, base_path: str = "") -> tuple[list[str], int, int]:
    """Verify static assets (including .jpg/.svg) copied cleanly and CSS url() links exist."""
    errors: list[str] = []
    verified_images = 0
    css_links = 0

    for rel in REQUIRED_IMAGE_ASSETS:
        target = dist_dir / rel
        if not target.is_file():
            errors.append(f"Missing required image asset: dist/{rel}")
        elif target.stat().st_size == 0:
            errors.append(f"Empty image asset: dist/{rel}")
        else:
            verified_images += 1

    if STATIC_SRC_DIR.is_dir():
        for src_file in sorted(STATIC_SRC_DIR.rglob("*")):
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(STATIC_SRC_DIR)
            dist_file = dist_dir / "static" / rel
            if not dist_file.is_file():
                errors.append(f"Static file not copied to dist: dist/static/{rel.as_posix()}")
            elif dist_file.stat().st_size == 0:
                errors.append(f"Static file is empty in dist: dist/static/{rel.as_posix()}")
            elif dist_file.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".svg"):
                if f"static/{rel.as_posix()}" not in REQUIRED_IMAGE_ASSETS:
                    verified_images += 1

    css_dir = dist_dir / "static" / "css"
    dist_root = dist_dir.resolve()
    if css_dir.is_dir():
        for css_file in sorted(css_dir.rglob("*.css")):
            rel_name = css_file.relative_to(dist_dir).as_posix()
            css_text = css_file.read_text(encoding="utf-8")
            for match in CSS_URL_RE.finditer(css_text):
                raw_url = match.group(1).strip()
                if (
                    not raw_url
                    or raw_url.startswith("#")
                    or raw_url.startswith("//")
                    or raw_url.startswith(("http://", "https://", "data:"))
                ):
                    continue
                css_links += 1
                line_no = css_text.count("\n", 0, match.start()) + 1
                if raw_url.startswith("/"):
                    ok, reason = _resolve_internal_target(
                        dist_dir,
                        raw_url,
                        base_path=base_path,
                        require_base_prefix=False,
                    )
                    if not ok:
                        errors.append(
                            f"Broken CSS url('{raw_url}') ({reason}) in dist/{rel_name}:{line_no}"
                        )
                else:
                    clean_rel = urllib.parse.unquote(urllib.parse.urlsplit(raw_url).path)
                    rel_target = (css_file.parent / clean_rel).resolve()
                    try:
                        rel_target.relative_to(dist_root)
                    except ValueError:
                        errors.append(
                            f"CSS url('{raw_url}') escapes dist/ in dist/{rel_name}:{line_no}"
                        )
                        continue
                    if not rel_target.is_file() or rel_target.stat().st_size == 0:
                        errors.append(
                            f"Broken relative CSS url('{raw_url}') in dist/{rel_name}:{line_no}"
                        )

    return errors, verified_images, css_links


def check_html_files(dist_dir: Path, base_path: str = "") -> tuple[list[str], int, int]:
    """Scan every ``.html`` under ``dist/`` for placeholders, base-path meta, and dead links."""
    errors: list[str] = []
    html_files = sorted(dist_dir.rglob("*.html"))
    if not html_files:
        return ["No .html files found under dist/."], 0, 0

    total_links = 0
    for html_file in html_files:
        rel_name = html_file.relative_to(dist_dir).as_posix()
        content = html_file.read_text(encoding="utf-8")

        for match in PLACEHOLDER_RE.finditer(content):
            line_no = content.count("\n", 0, match.start()) + 1
            errors.append(
                f"Unreplaced template variable {match.group(0)} in dist/{rel_name}:{line_no}"
            )

        extractor = InternalLinkExtractor()
        extractor.feed(content)
        extractor.close()

        if extractor.meta_base_path is None:
            errors.append(f"Missing <meta name=\"site-base-path\"> in dist/{rel_name}")
        elif extractor.meta_base_path != base_path:
            errors.append(
                f"Meta site-base-path '{extractor.meta_base_path}' != expected '{base_path}' "
                f"in dist/{rel_name}"
            )

        for ref in extractor.links:
            total_links += 1
            ok, reason = _resolve_internal_target(
                dist_dir,
                ref.raw_url,
                base_path=base_path,
                require_base_prefix=bool(base_path),
            )
            if not ok:
                errors.append(
                    f"Broken internal {ref.attr}='{ref.raw_url}' "
                    f"(<{ref.tag}>, {reason}) in dist/{rel_name}:{ref.line}"
                )

    return errors, len(html_files), total_links


def main(argv: list[str] | None = None) -> int:
    """Run all build and quality gate checks; return 0 on pass, 1 on failure."""
    _configure_stdio()
    args = parse_args(argv)
    base_path = normalize_base_path(args.base_path)
    expected_cname = _expected_cname(args.cname)
    errors: list[str] = []

    build_errors = run_build(
        base_path=base_path,
        site_url=args.site_url,
        cname=args.cname,
    )
    if build_errors:
        for err in build_errors:
            print(f"[ERROR] {err}", file=sys.stderr)
        return 1

    if not DIST_DIR.is_dir():
        print(f"[ERROR] Build output directory not found: {DIST_DIR}", file=sys.stderr)
        return 1

    errors.extend(check_required_files(DIST_DIR, expected_cname=expected_cname))
    asset_errors, image_count, css_link_count = check_static_assets(DIST_DIR, base_path=base_path)
    errors.extend(asset_errors)
    json_errors, posts_count, search_count = check_json_and_posts(DIST_DIR, base_path=base_path)
    errors.extend(json_errors)
    errors.extend(check_xml_files(DIST_DIR, base_path=base_path, posts_count=posts_count))
    html_errors, html_count, link_count = check_html_files(DIST_DIR, base_path=base_path)
    errors.extend(html_errors)

    if errors:
        print(f"\n[check] FAILED with {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    mode_desc = f"base_path='{base_path}'" if base_path else "root '/'"
    print(
        "[check] PASS: "
        f"{html_count} HTML files, {posts_count} posts, "
        f"{search_count} search entries, {image_count} image assets (.jpg/.svg), "
        f"{link_count + css_link_count} internal links verified ({mode_desc}), "
        "0 unreplaced placeholders, .nojekyll & JSON & XML valid."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
