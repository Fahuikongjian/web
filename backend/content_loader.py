"""Content loading, pure-Python Frontmatter parsing, and post metadata enrichment."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
import json
import math
from pathlib import Path
import re
from typing import Any


CJK_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
DATE_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FENCE_LINE_RE = re.compile(r"^```[^\n]*$", re.MULTILINE)
MD_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Post:
    """Normalized blog post record used across rendering and feed generation."""

    title: str
    slug: str
    date: str
    date_short: str
    year: str
    category: str
    tags: list[str]
    tags_csv: str
    summary: str
    cover: str
    featured: bool
    draft: bool
    url: str
    body_md: str
    excerpt: str
    word_count: int
    reading_time: int
    source_path: str = ""
    body_html: str = ""
    toc: list[dict[str, Any]] = field(default_factory=list)
    prev_post: dict[str, str] | None = None
    next_post: dict[str, str] | None = None
    related_posts: list[dict[str, str]] = field(default_factory=list)


def _strip_matching_quotes(value: str) -> str:
    """Remove matching outer single or double quotes and basic escapes."""
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        inner = text[1:-1]
        if text[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        else:
            inner = inner.replace("\\'", "'")
        return inner
    return text


def _split_inline_list(raw_inner: str) -> list[str]:
    """Split comma-separated items inside ``[...]`` respecting quotes."""
    items: list[str] = []
    buf: list[str] = []
    quote_char: str | None = None
    escaped = False

    for ch in raw_inner:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == "\\" and quote_char == '"':
            buf.append(ch)
            escaped = True
            continue
        if ch in ('"', "'"):
            if quote_char is None:
                quote_char = ch
            elif quote_char == ch:
                quote_char = None
            buf.append(ch)
            continue
        if ch == "," and quote_char is None:
            item = _strip_matching_quotes("".join(buf))
            if item:
                items.append(item)
            buf.clear()
            continue
        buf.append(ch)

    tail = _strip_matching_quotes("".join(buf))
    if tail:
        items.append(tail)
    return items


def _parse_scalar(raw_value: str) -> Any:
    """Parse a scalar YAML value (bool, inline list, date string, or string)."""
    stripped = raw_value.strip()
    if not stripped:
        return ""

    if stripped.startswith("[") and stripped.endswith("]"):
        return _split_inline_list(stripped[1:-1])

    is_quoted = (
        len(stripped) >= 2
        and stripped[0] == stripped[-1]
        and stripped[0] in ('"', "'")
    )
    if is_quoted:
        return _strip_matching_quotes(stripped)

    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    if DATE_ISO_RE.match(stripped):
        date.fromisoformat(stripped)
        return stripped

    return stripped


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML-style ``--- ... ---`` frontmatter and return ``(meta, body)``.

    Supports string scalars (quoted and unquoted), booleans, ISO dates,
    inline bracket lists ``[a, b]``, and multiline dash lists ``- a``.
    """
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, normalized

    end_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        raise ValueError("Unclosed frontmatter block: missing closing '---'.")

    meta: dict[str, Any] = {}
    pending_list_key: str | None = None

    for raw_line in lines[1:end_idx]:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped == "-" or stripped.startswith("- "):
            if pending_list_key is None:
                raise ValueError(f"List item without preceding key: {raw_line!r}")
            item_raw = stripped[1:].strip()
            existing = meta.get(pending_list_key)
            if existing == "":
                meta[pending_list_key] = []
            elif not isinstance(existing, list):
                raise ValueError(f"Key '{pending_list_key}' cannot mix scalar and list values.")
            item_val = _parse_scalar(item_raw)
            if item_val != "":
                meta[pending_list_key].append(item_val)
            continue

        if ":" not in raw_line:
            raise ValueError(f"Invalid frontmatter line (missing ':'): {raw_line!r}")

        key, raw_val = raw_line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Empty frontmatter key in line: {raw_line!r}")

        val_stripped = raw_val.strip()
        if val_stripped == "":
            meta[key] = ""
            pending_list_key = key
        else:
            meta[key] = _parse_scalar(val_stripped)
            pending_list_key = None

    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    return meta, body


def count_words(markdown_text: str) -> int:
    """Count Chinese characters plus English/numeric word tokens in Markdown."""
    cleaned = FENCE_LINE_RE.sub(" ", markdown_text)
    cleaned = MD_LINK_RE.sub(r" \1 ", cleaned)
    cleaned = HTML_TAG_RE.sub(" ", cleaned)
    cjk_count = len(CJK_RE.findall(cleaned))
    non_cjk = CJK_RE.sub(" ", cleaned)
    latin_count = len(LATIN_WORD_RE.findall(non_cjk))
    return cjk_count + latin_count


def estimate_reading_time(word_count: int, cjk_wpm: int = 350) -> int:
    """Estimate reading minutes at ~350 Chinese characters per minute (min 1)."""
    if word_count <= 0:
        return 1
    return max(1, math.ceil(word_count / cjk_wpm))


def extract_excerpt(markdown_text: str, max_chars: int = 180) -> str:
    """Build a clean plain-text excerpt from Markdown body for search indexing."""
    text = FENCE_LINE_RE.sub(" ", markdown_text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = text.replace("|", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _normalize_date(raw_date: Any, source_name: str) -> tuple[str, str, str]:
    """Validate and split ISO date ``YYYY-MM-DD`` into ``(date, mm-dd, yyyy)``."""
    date_str = str(raw_date).strip()
    if not DATE_ISO_RE.match(date_str):
        raise ValueError(f"Post '{source_name}' has invalid date {raw_date!r}; expected YYYY-MM-DD.")
    parsed = date.fromisoformat(date_str)
    return date_str, f"{parsed.month:02d}-{parsed.day:02d}", f"{parsed.year:04d}"


def _normalize_tags(raw_tags: Any) -> list[str]:
    """Coerce frontmatter ``tags`` into a deduplicated list of non-empty strings."""
    if raw_tags in (None, ""):
        return []
    if isinstance(raw_tags, str):
        candidates = [part.strip() for part in raw_tags.split(",")]
    elif isinstance(raw_tags, list):
        candidates = [str(item).strip() for item in raw_tags]
    else:
        raise ValueError(f"Unsupported tags value: {raw_tags!r}")
    seen: set[str] = set()
    result: list[str] = []
    for tag in candidates:
        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


def load_site_config(content_dir: Path) -> dict[str, Any]:
    """Load and validate ``content/site.json``."""
    site_path = content_dir / "site.json"
    data = json.loads(site_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("content/site.json must be a JSON object.")
    required = (
        "site_title",
        "site_tagline",
        "site_url",
        "author_name",
        "author_role",
        "author_location",
        "author_bio",
        "hero_eyebrow",
        "hero_title",
        "hero_subtitle",
        "now_status",
        "icp_number",
        "icp_url",
        "social_links",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"content/site.json missing required fields: {', '.join(missing)}")
    data["site_url"] = str(data["site_url"]).rstrip("/")
    return data


def load_projects(content_dir: Path) -> list[dict[str, Any]]:
    """Load and normalize ``content/projects.json``."""
    projects_path = content_dir / "projects.json"
    data = json.loads(projects_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("content/projects.json must be a JSON array.")
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"content/projects.json item #{idx} must be an object.")
        normalized.append(
            {
                "name": str(item.get("name", "")),
                "status": str(item.get("status", "")),
                "year": str(item.get("year", "")),
                "summary": str(item.get("summary", "")),
                "stack": [str(s) for s in item.get("stack", [])],
                "url": str(item.get("url") or "").strip(),
            }
        )
    return normalized


def load_about_markdown(content_dir: Path) -> str:
    """Load ``content/about.md`` body (stripping optional frontmatter if present)."""
    about_path = content_dir / "about.md"
    raw = about_path.read_text(encoding="utf-8")
    _, body = parse_frontmatter(raw)
    return body


def _compute_related_posts(posts: list[Post], limit: int = 2) -> None:
    """Populate ``prev_post``, ``next_post``, and ``related_posts`` for each post."""
    total = len(posts)
    for idx, post in enumerate(posts):
        if idx > 0:
            newer = posts[idx - 1]
            post.prev_post = {
                "title": newer.title,
                "url": newer.url,
                "date": newer.date,
                "slug": newer.slug,
            }
        if idx + 1 < total:
            older = posts[idx + 1]
            post.next_post = {
                "title": older.title,
                "url": older.url,
                "date": older.date,
                "slug": older.slug,
            }

        post_tags = set(post.tags)
        scored: list[tuple[int, int, str, Post]] = []
        for cand_idx, candidate in enumerate(posts):
            if candidate.slug == post.slug:
                continue
            shared_tags = len(post_tags & set(candidate.tags))
            same_cat = 1 if candidate.category and candidate.category == post.category else 0
            score = shared_tags * 3 + same_cat * 2
            if score > 0:
                scored.append((score, 1, candidate.date, candidate))

        scored.sort(key=lambda item: (item[0], item[2]), reverse=True)
        chosen = [item[3] for item in scored[:limit]]

        if len(chosen) < limit:
            chosen_slugs = {item.slug for item in chosen} | {post.slug}
            for candidate in posts:
                if candidate.slug not in chosen_slugs:
                    chosen.append(candidate)
                    chosen_slugs.add(candidate.slug)
                if len(chosen) >= limit:
                    break

        post.related_posts = [
            {
                "slug": rel.slug,
                "title": rel.title,
                "url": rel.url,
                "date": rel.date,
                "category": rel.category,
                "reading_time": str(rel.reading_time),
                "summary": rel.summary,
            }
            for rel in chosen
        ]


def load_posts(content_dir: Path, include_drafts: bool = False) -> list[Post]:
    """Load, validate, enrich, and date-sort posts from ``content/posts/*.md``."""
    posts_dir = content_dir / "posts"
    if not posts_dir.is_dir():
        return []

    posts: list[Post] = []
    seen_slugs: set[str] = set()

    for md_path in sorted(posts_dir.glob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)

        draft = bool(meta.get("draft", False))
        if draft and not include_drafts:
            continue

        slug = str(meta.get("slug") or md_path.stem).strip()
        if not slug:
            raise ValueError(f"Post '{md_path.name}' produced an empty slug.")
        if slug in seen_slugs:
            raise ValueError(f"Duplicate post slug detected: '{slug}'.")
        seen_slugs.add(slug)

        title = str(meta.get("title") or slug).strip()
        date_str, date_short, year = _normalize_date(meta.get("date", ""), md_path.name)
        tags = _normalize_tags(meta.get("tags", []))
        category = str(meta.get("category", "随笔")).strip()
        summary = str(meta.get("summary", "")).strip()
        cover = str(meta.get("cover", "")).strip()
        featured = bool(meta.get("featured", False))

        word_count = count_words(body)
        reading_time = estimate_reading_time(word_count)
        excerpt = extract_excerpt(body)

        posts.append(
            Post(
                title=title,
                slug=slug,
                date=date_str,
                date_short=date_short,
                year=year,
                category=category,
                tags=tags,
                tags_csv=",".join(tags),
                summary=summary,
                cover=cover,
                featured=featured,
                draft=draft,
                url=f"/articles/{slug}/",
                body_md=body,
                excerpt=excerpt,
                word_count=word_count,
                reading_time=reading_time,
                source_path=str(md_path),
            )
        )

    posts.sort(key=lambda p: (p.date, p.slug), reverse=True)
    _compute_related_posts(posts)
    return posts


def compute_tag_stats(posts: list[Post]) -> list[dict[str, Any]]:
    """Aggregate tag counts sorted by frequency descending, then tag name."""
    counts: Counter[str] = Counter()
    for post in posts:
        for tag in post.tags:
            counts[tag] += 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"name": name, "count": count} for name, count in ordered]


def compute_category_stats(posts: list[Post]) -> list[dict[str, Any]]:
    """Aggregate category counts sorted by frequency descending, then name."""
    counts: Counter[str] = Counter()
    for post in posts:
        if post.category:
            counts[post.category] += 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"name": name, "count": count} for name, count in ordered]


def load_all_content(content_dir: Path) -> dict[str, Any]:
    """Load site config, projects, about body, published posts, and tag stats."""
    site = load_site_config(content_dir)
    projects = load_projects(content_dir)
    about_md = load_about_markdown(content_dir)
    posts = load_posts(content_dir)
    tag_stats = compute_tag_stats(posts)
    category_stats = compute_category_stats(posts)
    return {
        "site": site,
        "projects": projects,
        "about_md": about_md,
        "posts": posts,
        "tag_stats": tag_stats,
        "category_stats": category_stats,
    }
