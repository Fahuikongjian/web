"""JSON API, RSS 2.0, Sitemap XML, and robots.txt generators."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
import json
from pathlib import Path
from typing import Any
import urllib.parse
import xml.etree.ElementTree as ET

from backend.content_loader import Post


SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _normalize_bp(base_path: str | None) -> str:
    """Normalize a subpath prefix to ``''`` or ``'/subpath'``."""
    if not base_path:
        return ""
    stripped = base_path.strip().strip("/")
    return f"/{stripped}" if stripped else ""


def prefix_url(path: str, base_path: str = "") -> str:
    """Prefix a root-relative path with ``base_path`` without double-prefixing."""
    bp = _normalize_bp(base_path)
    if not bp or not path or not path.startswith("/") or path.startswith("//"):
        return path
    if path == bp or path.startswith(f"{bp}/"):
        return path
    if path == "/":
        return f"{bp}/"
    return f"{bp}{path}"


def effective_site_url(site_url: str, base_path: str = "") -> str:
    """Return canonical site origin+subpath without duplicating ``base_path``."""
    base_url = str(site_url).strip().rstrip("/")
    bp = _normalize_bp(base_path)
    if not bp:
        return base_url
    parsed = urllib.parse.urlsplit(base_url)
    url_path = parsed.path.rstrip("/")
    if url_path == bp or url_path.endswith(bp):
        return base_url
    if not url_path:
        return f"{base_url}{bp}"
    return base_url


def _iso_date_to_rfc822(date_str: str) -> str:
    """Convert ``YYYY-MM-DD`` string into an RFC 822 UTC timestamp."""
    year, month, day = (int(part) for part in date_str.split("-"))
    dt = datetime(year, month, day, 9, 0, 0, tzinfo=timezone.utc)
    return format_datetime(dt, usegmt=True)


def build_search_index(posts: list[Post], base_path: str = "") -> list[dict[str, Any]]:
    """Build ``/api/search-index.json`` payload ordered newest-first."""
    return [
        {
            "title": post.title,
            "slug": post.slug,
            "url": prefix_url(post.url, base_path),
            "date": post.date,
            "category": post.category,
            "tags": post.tags,
            "summary": post.summary,
            "excerpt": post.excerpt,
            "reading_time": post.reading_time,
        }
        for post in posts
    ]


def build_posts_api(
    posts: list[Post],
    tag_stats: list[dict[str, Any]],
    category_stats: list[dict[str, Any]],
    base_path: str = "",
) -> dict[str, Any]:
    """Build ``/api/posts.json`` payload with metadata and tag/category counts."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "generated_at": generated_at,
        "total": len(posts),
        "posts": [
            {
                "title": post.title,
                "slug": post.slug,
                "url": prefix_url(post.url, base_path),
                "date": post.date,
                "category": post.category,
                "tags": post.tags,
                "summary": post.summary,
                "cover": prefix_url(post.cover, base_path),
                "featured": post.featured,
                "word_count": post.word_count,
                "reading_time": post.reading_time,
            }
            for post in posts
        ],
        "tags": tag_stats,
        "categories": category_stats,
    }


def build_projects_api(
    projects: list[dict[str, Any]],
    tag_stats: list[dict[str, Any]],
    category_stats: list[dict[str, Any]],
    base_path: str = "",
) -> dict[str, Any]:
    """Build ``/api/projects.json`` payload with normalized project metadata and counts."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "generated_at": generated_at,
        "total": len(projects),
        "projects": [
            {
                "name": str(proj.get("name", "")),
                "status": str(proj.get("status", "")),
                "year": str(proj.get("year", "")),
                "summary": str(proj.get("summary", "")),
                "stack": list(proj.get("stack", [])),
                "category": str(proj.get("category", "")),
                "tags": list(proj.get("tags", [])),
                "url": (
                    prefix_url(str(proj.get("url", "")), base_path)
                    if proj.get("url")
                    else ""
                ),
            }
            for proj in projects
        ],
        "tags": tag_stats,
        "categories": category_stats,
    }


def build_gallery_api(
    gallery: list[dict[str, Any]],
    tag_stats: list[dict[str, Any]],
    category_stats: list[dict[str, Any]],
    base_path: str = "",
) -> dict[str, Any]:
    """Build ``/api/gallery.json`` payload with image prompts, metadata, and counts."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "generated_at": generated_at,
        "total": len(gallery),
        "items": [
            {
                "id": str(item.get("id", "")),
                "title": str(item.get("title", "")),
                "image": prefix_url(str(item.get("image", "")), base_path),
                "prompt": str(item.get("prompt", "")),
                "negative_prompt": str(item.get("negative_prompt", "")),
                "model": str(item.get("model", "")),
                "params": str(item.get("params", "")),
                "category": str(item.get("category", "")),
                "tags": list(item.get("tags", [])),
                "date": str(item.get("date", "")),
            }
            for item in gallery
        ],
        "tags": tag_stats,
        "categories": category_stats,
    }


def build_rss_xml(
    site: dict[str, Any],
    posts: list[Post],
    base_path: str = "",
) -> str:
    """Generate a valid RSS 2.0 XML document with automatic XML escaping."""
    site_root = effective_site_url(str(site["site_url"]), base_path)
    rss_el = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss_el, "channel")

    ET.SubElement(channel, "title").text = str(site["site_title"])
    ET.SubElement(channel, "link").text = f"{site_root}/"
    ET.SubElement(channel, "description").text = str(site["site_tagline"])
    ET.SubElement(channel, "language").text = "zh-CN"

    if posts:
        ET.SubElement(channel, "lastBuildDate").text = _iso_date_to_rfc822(posts[0].date)
    else:
        ET.SubElement(channel, "lastBuildDate").text = format_datetime(
            datetime.now(timezone.utc), usegmt=True
        )

    for post in posts:
        item = ET.SubElement(channel, "item")
        abs_url = f"{site_root}{post.url}"
        ET.SubElement(item, "title").text = post.title
        ET.SubElement(item, "link").text = abs_url
        guid = ET.SubElement(item, "guid", {"isPermaLink": "true"})
        guid.text = abs_url
        ET.SubElement(item, "pubDate").text = _iso_date_to_rfc822(post.date)
        if post.category:
            ET.SubElement(item, "category").text = post.category
        ET.SubElement(item, "description").text = post.summary or post.excerpt

    ET.indent(rss_el, space="  ")
    xml_bytes = ET.tostring(rss_el, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8") + "\n"


def build_sitemap_xml(
    site: dict[str, Any],
    posts: list[Post],
    base_path: str = "",
) -> str:
    """Generate a valid Sitemap XML document covering core routes and posts."""
    site_root = effective_site_url(str(site["site_url"]), base_path)
    latest_date = posts[0].date if posts else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ET.register_namespace("", SITEMAP_NS)
    urlset = ET.Element(f"{{{SITEMAP_NS}}}urlset")

    static_routes = [
        ("/", latest_date, "1.0"),
        ("/articles/", latest_date, "0.9"),
        ("/projects/", latest_date, "0.8"),
        ("/gallery/", latest_date, "0.8"),
        ("/games/", latest_date, "0.7"),
        ("/about/", latest_date, "0.7"),
    ]
    for route, lastmod, priority in static_routes:
        url_el = ET.SubElement(urlset, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url_el, f"{{{SITEMAP_NS}}}loc").text = f"{site_root}{route}"
        ET.SubElement(url_el, f"{{{SITEMAP_NS}}}lastmod").text = lastmod
        ET.SubElement(url_el, f"{{{SITEMAP_NS}}}priority").text = priority

    for post in posts:
        url_el = ET.SubElement(urlset, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url_el, f"{{{SITEMAP_NS}}}loc").text = f"{site_root}{post.url}"
        ET.SubElement(url_el, f"{{{SITEMAP_NS}}}lastmod").text = post.date
        ET.SubElement(url_el, f"{{{SITEMAP_NS}}}priority").text = "0.8"

    ET.indent(urlset, space="  ")
    xml_bytes = ET.tostring(urlset, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8") + "\n"


def build_robots_txt(site: dict[str, Any], base_path: str = "") -> str:
    """Generate ``robots.txt`` pointing crawlers to ``sitemap.xml``."""
    site_root = effective_site_url(str(site["site_url"]), base_path)
    return f"User-agent: *\nAllow: /\nSitemap: {site_root}/sitemap.xml\n"


def write_feeds(
    dist_dir: Path,
    site: dict[str, Any],
    posts: list[Post],
    tag_stats: list[dict[str, Any]],
    category_stats: list[dict[str, Any]],
    base_path: str = "",
    projects: list[dict[str, Any]] | None = None,
    project_tag_stats: list[dict[str, Any]] | None = None,
    project_category_stats: list[dict[str, Any]] | None = None,
    gallery: list[dict[str, Any]] | None = None,
    gallery_tag_stats: list[dict[str, Any]] | None = None,
    gallery_category_stats: list[dict[str, Any]] | None = None,
) -> list[Path]:
    """Write JSON APIs (``posts``, ``projects``, ``gallery``, ``search-index``), RSS, Sitemap, and robots."""
    api_dir = dist_dir / "api"
    api_dir.mkdir(parents=True, exist_ok=True)

    posts_api_path = api_dir / "posts.json"
    projects_api_path = api_dir / "projects.json"
    gallery_api_path = api_dir / "gallery.json"
    search_index_path = api_dir / "search-index.json"
    rss_path = dist_dir / "rss.xml"
    sitemap_path = dist_dir / "sitemap.xml"
    robots_path = dist_dir / "robots.txt"

    posts_payload = build_posts_api(posts, tag_stats, category_stats, base_path=base_path)
    projects_payload = build_projects_api(
        projects or [],
        project_tag_stats or [],
        project_category_stats or [],
        base_path=base_path,
    )
    gallery_payload = build_gallery_api(
        gallery or [],
        gallery_tag_stats or [],
        gallery_category_stats or [],
        base_path=base_path,
    )
    search_payload = build_search_index(posts, base_path=base_path)

    posts_api_path.write_text(
        json.dumps(posts_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    projects_api_path.write_text(
        json.dumps(projects_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    gallery_api_path.write_text(
        json.dumps(gallery_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    search_index_path.write_text(
        json.dumps(search_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    rss_path.write_text(build_rss_xml(site, posts, base_path=base_path), encoding="utf-8")
    sitemap_path.write_text(build_sitemap_xml(site, posts, base_path=base_path), encoding="utf-8")
    robots_path.write_text(build_robots_txt(site, base_path=base_path), encoding="utf-8")

    return [
        posts_api_path,
        projects_api_path,
        gallery_api_path,
        search_index_path,
        rss_path,
        sitemap_path,
        robots_path,
    ]
