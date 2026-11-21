"""Pure-Python Markdown parser with TOC extraction and Pygments highlighting."""

from __future__ import annotations

import html
import re
from typing import Any
import urllib.parse

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound


FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
ATX_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
HR_RE = re.compile(r"^\s{0,3}(?:(-\s*){3,}|(\*\s*){3,}|(_\s*){3,})\s*$")
BLOCKQUOTE_RE = re.compile(r"^(\s{0,3})>(?:\s?(.*))?$")
UL_ITEM_RE = re.compile(r"^(\s*)([-*+])\s+(.*)$")
OL_ITEM_RE = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
TABLE_SEP_CELL_RE = re.compile(r"^:?-{1,}:?$")
PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")

SAFE_URL_SCHEMES = {"http", "https", "mailto"}


def _neutralize_template_braces(rendered_html: str) -> str:
    """Prevent literal ``{{key}}`` in Markdown/code from matching template regexes."""
    return PLACEHOLDER_RE.sub(r"&#123;&#123;\1&#125;&#125;", rendered_html)


def _is_safe_url(raw_url: str) -> bool:
    """Allow root-relative, fragment, relative, and http(s)/mailto URLs only."""
    cleaned = re.sub(r"[\x00-\x20\x7f]+", "", raw_url.strip())
    if not cleaned:
        return False
    parsed = urllib.parse.urlsplit(cleaned)
    if not parsed.scheme:
        return True
    return parsed.scheme.lower() in SAFE_URL_SCHEMES


def _strip_inline_markdown(raw_text: str) -> str:
    """Reduce inline Markdown syntax to plain readable text for headings/TOC."""
    text = raw_text.strip()
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.strip()


def make_heading_id(raw_text: str, seen_ids: dict[str, int]) -> str:
    """Generate a deterministic, unique anchor ``id`` preserving CJK and ASCII."""
    plain = _strip_inline_markdown(raw_text)
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", plain.lower())
    base = re.sub(r"[\s_]+", "-", cleaned).strip("-") or "section"
    count = seen_ids.get(base, 0) + 1
    seen_ids[base] = count
    return base if count == 1 else f"{base}-{count}"


def render_code_block(code: str, lang: str = "") -> str:
    """Render a fenced code block using Pygments inside ``.code-block-wrapper``."""
    raw_lang = (lang or "").strip().split()[0] if lang and lang.strip() else "text"
    safe_lang = re.sub(r"[^a-zA-Z0-9_+-]", "", raw_lang) or "text"
    try:
        lexer = get_lexer_by_name(safe_lang)
    except ClassNotFound:
        lexer = TextLexer()

    formatter = HtmlFormatter(cssclass="highlight")
    code_payload = code if code.endswith("\n") else f"{code}\n"
    highlighted = highlight(code_payload, lexer, formatter).rstrip()
    highlighted = _neutralize_template_braces(highlighted)

    lang_label = html.escape(safe_lang, quote=True)
    return (
        '<div class="code-block-wrapper">'
        '<div class="code-block-header">'
        f'<span class="code-lang">{lang_label}</span>'
        '<button type="button" class="code-copy-btn" aria-label="复制代码">复制</button>'
        "</div>"
        f"{highlighted}"
        "</div>"
    )


def _extract_inline_code_spans(text: str, store: list[str]) -> str:
    """Replace inline code spans (`` `...` ``) with sentinels before HTML escaping."""
    out: list[str] = []
    idx = 0
    length = len(text)

    while idx < length:
        if text[idx] == "`":
            tick_end = idx
            while tick_end < length and text[tick_end] == "`":
                tick_end += 1
            tick_len = tick_end - idx
            close_pos = text.find("`" * tick_len, tick_end)
            while close_pos != -1:
                after = close_pos + tick_len
                if after < length and text[after] == "`":
                    # Skip longer backtick runs inside code span
                    while after < length and text[after] == "`":
                        after += 1
                    close_pos = text.find("`" * tick_len, after)
                    continue
                break
            if close_pos != -1:
                code_inner = text[tick_end:close_pos]
                if len(code_inner) >= 2 and code_inner.startswith(" ") and code_inner.endswith(" ") and code_inner.strip():
                    code_inner = code_inner[1:-1]
                token = f"\x00CODE{len(store)}\x00"
                store.append(f"<code>{_neutralize_template_braces(html.escape(code_inner, quote=True))}</code>")
                out.append(token)
                idx = close_pos + tick_len
                continue
            out.append(text[idx:tick_end])
            idx = tick_end
            continue

        out.append(text[idx])
        idx += 1

    return "".join(out)


def _format_emphasis(escaped_text: str) -> str:
    """Apply bold ``**...**`` / ``__...__`` and italic ``*...*`` / ``_..._``."""
    text = re.sub(r"\*\*([^\s*](?:.*?[^\s*])?)\*\*", r"<strong>\1</strong>", escaped_text)
    text = re.sub(
        r"(?<![A-Za-z0-9_])__([^\s_](?:.*?[^\s_])?)__(?![A-Za-z0-9_])",
        r"<strong>\1</strong>",
        text,
    )
    text = re.sub(r"(?<!\*)\*([^\s*](?:.*?[^\s*])?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(
        r"(?<![A-Za-z0-9_])_([^\s_](?:.*?[^\s_])?)_(?![A-Za-z0-9_])",
        r"<em>\1</em>",
        text,
    )
    return text


def render_inline(raw_text: str) -> str:
    """Safely render inline Markdown (code, images, links, bold, italic, XSS escape)."""
    code_store: list[str] = []
    protected = _extract_inline_code_spans(raw_text, code_store)

    link_store: list[str] = []

    def _replace_image(match: re.Match[str]) -> str:
        alt_raw = match.group(1)
        url_raw = match.group(2).strip()
        # Strip optional title in "url 'title'"
        url_only = re.split(r"\s+", url_raw, maxsplit=1)[0]
        alt_escaped = html.escape(alt_raw, quote=True)
        token = f"\x00LINK{len(link_store)}\x00"
        if _is_safe_url(url_only):
            src_escaped = html.escape(url_only, quote=True)
            link_store.append(f'<img src="{src_escaped}" alt="{alt_escaped}" loading="lazy">')
        else:
            link_store.append(alt_escaped)
        return token

    def _replace_link(match: re.Match[str]) -> str:
        label_raw = match.group(1)
        url_raw = match.group(2).strip()
        url_only = re.split(r"\s+", url_raw, maxsplit=1)[0]
        label_escaped = _format_emphasis(html.escape(label_raw, quote=True))
        token = f"\x00LINK{len(link_store)}\x00"
        if _is_safe_url(url_only):
            href_escaped = html.escape(url_only, quote=True)
            link_store.append(f'<a href="{href_escaped}">{label_escaped}</a>')
        else:
            link_store.append(label_escaped)
        return token

    # Extract images before links so ![alt](src) is not treated as ![text](url) link.
    protected = re.sub(r"!\[([^\]]*)\]\(([^)\n]+)\)", _replace_image, protected)
    protected = re.sub(r"\[([^\]]+)\]\(([^)\n]+)\)", _replace_link, protected)

    escaped = html.escape(protected, quote=True)
    formatted = _format_emphasis(escaped)

    for idx, link_html in enumerate(link_store):
        formatted = formatted.replace(f"\x00LINK{idx}\x00", link_html)
    for idx, code_html in enumerate(code_store):
        formatted = formatted.replace(f"\x00CODE{idx}\x00", code_html)

    return _neutralize_template_braces(formatted)


def _split_table_row(line: str) -> list[str]:
    """Split a Markdown table row into trimmed cell strings."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]

    cells: list[str] = []
    buf: list[str] = []
    in_code = False
    idx = 0
    while idx < len(stripped):
        ch = stripped[idx]
        if ch == "\\" and idx + 1 < len(stripped) and stripped[idx + 1] == "|":
            buf.append("|")
            idx += 2
            continue
        if ch == "`":
            in_code = not in_code
            buf.append(ch)
            idx += 1
            continue
        if ch == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf.clear()
            idx += 1
            continue
        buf.append(ch)
        idx += 1

    cells.append("".join(buf).strip())
    return cells


def _parse_table_alignments(sep_line: str) -> list[str | None] | None:
    """Return column alignments if ``sep_line`` is a valid Markdown table separator."""
    if "|" not in sep_line:
        return None
    cells = _split_table_row(sep_line)
    if not cells:
        return None
    alignments: list[str | None] = []
    for cell in cells:
        token = cell.strip()
        if not TABLE_SEP_CELL_RE.match(token):
            return None
        left = token.startswith(":")
        right = token.endswith(":")
        if left and right:
            alignments.append("center")
        elif left:
            alignments.append("left")
        elif right:
            alignments.append("right")
        else:
            alignments.append(None)
    return alignments


def _is_block_boundary(lines: list[str], idx: int) -> bool:
    """Check whether ``lines[idx]`` starts a block construct that interrupts paragraphs."""
    line = lines[idx]
    if not line.strip():
        return True
    if FENCE_OPEN_RE.match(line):
        return True
    if ATX_HEADING_RE.match(line):
        return True
    if HR_RE.match(line):
        return True
    if BLOCKQUOTE_RE.match(line):
        return True
    if UL_ITEM_RE.match(line) or OL_ITEM_RE.match(line):
        return True
    if idx + 1 < len(lines) and "|" in line and _parse_table_alignments(lines[idx + 1]) is not None:
        return True
    return False


def _parse_list_block(
    lines: list[str],
    start_idx: int,
    seen_ids: dict[str, int],
    toc: list[dict[str, Any]],
) -> tuple[str, int]:
    """Parse an ordered or unordered list (including nested sublists)."""
    first_ul = UL_ITEM_RE.match(lines[start_idx])
    first_ol = OL_ITEM_RE.match(lines[start_idx])
    if not first_ul and not first_ol:
        raise ValueError("Expected list item at start_idx")

    is_ordered = first_ol is not None
    tag = "ol" if is_ordered else "ul"
    base_indent = len((first_ol or first_ul).group(1))

    items_html: list[str] = []
    idx = start_idx
    total = len(lines)

    while idx < total:
        line = lines[idx]
        if not line.strip():
            # Allow single blank line only if next non-blank line continues same list level
            lookahead = idx + 1
            while lookahead < total and not lines[lookahead].strip():
                lookahead += 1
            if lookahead >= total:
                break
            next_match = (OL_ITEM_RE if is_ordered else UL_ITEM_RE).match(lines[lookahead])
            if next_match and len(next_match.group(1)) == base_indent:
                idx = lookahead
                continue
            break

        cur_match = (OL_ITEM_RE if is_ordered else UL_ITEM_RE).match(line)
        other_match = (UL_ITEM_RE if is_ordered else OL_ITEM_RE).match(line)

        if cur_match and len(cur_match.group(1)) == base_indent:
            item_parts = [cur_match.group(3).strip()]
            idx += 1
            nested_html: list[str] = []

            while idx < total:
                sub = lines[idx]
                if not sub.strip():
                    break
                sub_ul = UL_ITEM_RE.match(sub)
                sub_ol = OL_ITEM_RE.match(sub)
                sub_match = sub_ol or sub_ul
                if sub_match:
                    sub_indent = len(sub_match.group(1))
                    if sub_indent > base_indent:
                        sub_rendered, idx = _parse_list_block(lines, idx, seen_ids, toc)
                        nested_html.append(sub_rendered)
                        continue
                    break
                # Indented continuation line for current item
                if sub.startswith(" " * (base_indent + 2)) or sub.startswith("\t"):
                    item_parts.append(sub.strip())
                    idx += 1
                    continue
                break

            rendered_text = render_inline(" ".join(item_parts))
            if nested_html:
                items_html.append(f"<li>{rendered_text}{''.join(nested_html)}</li>")
            else:
                items_html.append(f"<li>{rendered_text}</li>")
            continue

        if other_match and len(other_match.group(1)) == base_indent:
            break
        break

    return f"<{tag}>\n" + "\n".join(items_html) + f"\n</{tag}>", idx


def _render_blocks(
    lines: list[str],
    seen_ids: dict[str, int],
    toc: list[dict[str, Any]],
    collect_toc: bool = True,
) -> list[str]:
    """Parse Markdown lines into a list of HTML block strings."""
    blocks: list[str] = []
    idx = 0
    total = len(lines)

    while idx < total:
        line = lines[idx]
        if not line.strip():
            idx += 1
            continue

        # 1. Fenced code block (``` or ~~~)
        fence_match = FENCE_OPEN_RE.match(line)
        if fence_match:
            fence = fence_match.group(1)
            lang_info = fence_match.group(2).strip()
            close_re = re.compile(rf"^\s{{0,3}}{re.escape(fence[0])}{{{len(fence)},}}\s*$")
            code_lines: list[str] = []
            idx += 1
            while idx < total and not close_re.match(lines[idx]):
                code_lines.append(lines[idx])
                idx += 1
            if idx < total:
                idx += 1
            blocks.append(render_code_block("\n".join(code_lines), lang_info))
            continue

        # 2. ATX Heading (# .. ######)
        heading_match = ATX_HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            raw_heading = re.sub(r"\s+#+\s*$", "", heading_match.group(2)).strip()
            plain_heading = _strip_inline_markdown(raw_heading)
            inline_heading = render_inline(raw_heading)
            if level in (2, 3, 4):
                hid = make_heading_id(raw_heading, seen_ids)
                if collect_toc and level in (2, 3):
                    toc.append({"level": level, "id": hid, "text": plain_heading})
                anchor = f'<a class="heading-anchor" href="#{hid}" aria-label="段落锚点">#</a>'
                blocks.append(f'<h{level} id="{hid}">{inline_heading}{anchor}</h{level}>')
            else:
                blocks.append(f"<h{level}>{inline_heading}</h{level}>")
            idx += 1
            continue

        # 3. Horizontal rule
        if HR_RE.match(line):
            blocks.append("<hr>")
            idx += 1
            continue

        # 4. Blockquote (consecutive `>` lines)
        if BLOCKQUOTE_RE.match(line):
            quote_lines: list[str] = []
            while idx < total:
                q_match = BLOCKQUOTE_RE.match(lines[idx])
                if not q_match:
                    break
                quote_lines.append(q_match.group(2) or "")
                idx += 1
            inner_blocks = _render_blocks(quote_lines, seen_ids, toc, collect_toc=False)
            blocks.append("<blockquote>\n" + "\n".join(inner_blocks) + "\n</blockquote>")
            continue

        # 5. Markdown Table (header + separator + body rows)
        if idx + 1 < total and "|" in line:
            alignments = _parse_table_alignments(lines[idx + 1])
            if alignments is not None:
                headers = _split_table_row(line)
                col_count = len(alignments)
                if len(headers) < col_count:
                    headers.extend([""] * (col_count - len(headers)))
                headers = headers[:col_count]

                idx += 2
                body_rows: list[list[str]] = []
                while idx < total:
                    row_line = lines[idx]
                    if not row_line.strip() or _is_block_boundary(lines, idx) or "|" not in row_line:
                        break
                    cells = _split_table_row(row_line)
                    if len(cells) < col_count:
                        cells.extend([""] * (col_count - len(cells)))
                    body_rows.append(cells[:col_count])
                    idx += 1

                th_html = []
                for col_i, cell_text in enumerate(headers):
                    align = alignments[col_i]
                    align_attr = f' style="text-align:{align}"' if align else ""
                    th_html.append(f"<th{align_attr}>{render_inline(cell_text)}</th>")

                tr_html = []
                for row in body_rows:
                    td_html = []
                    for col_i, cell_text in enumerate(row):
                        align = alignments[col_i]
                        align_attr = f' style="text-align:{align}"' if align else ""
                        td_html.append(f"<td{align_attr}>{render_inline(cell_text)}</td>")
                    tr_html.append("<tr>" + "".join(td_html) + "</tr>")

                table_html = (
                    '<div class="table-wrap"><table>'
                    f"<thead><tr>{''.join(th_html)}</tr></thead>"
                    f"<tbody>{''.join(tr_html)}</tbody>"
                    "</table></div>"
                )
                blocks.append(table_html)
                continue

        # 6. Lists (ordered / unordered)
        if UL_ITEM_RE.match(line) or OL_ITEM_RE.match(line):
            list_html, idx = _parse_list_block(lines, idx, seen_ids, toc)
            blocks.append(list_html)
            continue

        # 7. Paragraph
        para_lines = [line.strip()]
        idx += 1
        while idx < total and not _is_block_boundary(lines, idx):
            para_lines.append(lines[idx].strip())
            idx += 1
        blocks.append(f"<p>{render_inline(' '.join(para_lines))}</p>")

    return blocks


def render_toc_html(toc: list[dict[str, Any]]) -> str:
    """Render structured TOC items into the ``.toc-nav`` HTML contract."""
    if not toc:
        return (
            '<nav class="toc-nav" aria-label="文章目录">'
            '<p class="toc-empty">本文暂无二级目录</p>'
            '<ul class="toc-list"></ul>'
            "</nav>"
        )

    items: list[str] = []
    for entry in toc:
        level = int(entry["level"])
        hid = html.escape(str(entry["id"]), quote=True)
        text = html.escape(str(entry["text"]), quote=True)
        items.append(
            f'<li class="toc-item toc-level-{level} toc-item--h{level}">'
            f'<a class="toc-link" data-level="{level}" href="#{hid}">{text}</a>'
            "</li>"
        )
    return (
        '<nav class="toc-nav" aria-label="文章目录">\n'
        '  <ul class="toc-list">\n'
        + "\n".join(f"    {item}" for item in items)
        + "\n  </ul>\n</nav>"
    )


def render_markdown(markdown_text: str) -> tuple[str, list[dict[str, Any]]]:
    """Render Markdown to safe HTML and return ``(body_html, toc_list)``."""
    normalized = markdown_text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    seen_ids: dict[str, int] = {}
    toc: list[dict[str, Any]] = []
    blocks = _render_blocks(lines, seen_ids, toc, collect_toc=True)
    return "\n".join(blocks), toc
