"""Build CLI entrypoint for generating the static blog into ``dist/``."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.renderer import render_site  # noqa: E402


def _configure_stdio() -> None:
    """Avoid UnicodeEncodeError on Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the static site builder."""
    parser = argparse.ArgumentParser(description="Build static site output into dist/.")
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root containing content/, templates/, static/",
    )
    parser.add_argument(
        "--dist",
        type=Path,
        default=None,
        help="Output directory (defaults to <root>/dist)",
    )
    parser.add_argument(
        "--base-path",
        default=os.environ.get("SITE_BASE_PATH", ""),
        help="Optional URL subpath prefix for project GitHub Pages (e.g. /repo-name)",
    )
    parser.add_argument(
        "--site-url",
        default=os.environ.get("SITE_URL") or None,
        help="Override site_url from content/site.json for canonical/RSS/Sitemap",
    )
    parser.add_argument(
        "--cname",
        default=os.environ.get("SITE_CNAME", ""),
        help="Optional custom domain to write into dist/CNAME",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not wipe the output directory before rebuilding",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the static build and print summary statistics."""
    _configure_stdio()
    args = parse_args(argv)
    stats = render_site(
        project_root=args.root.resolve(),
        dist_dir=args.dist.resolve() if args.dist else None,
        clean=not args.no_clean,
        base_path=args.base_path,
        site_url=args.site_url,
        cname=args.cname,
    )
    bp_label = stats["base_path"] or "/"
    cname_label = "yes" if stats["has_cname"] else "no"
    print(
        "[build] OK: "
        f"{stats['html_pages_count']} HTML pages "
        f"({stats['posts_count']} posts, {stats['projects_count']} projects, {stats['tags_count']} tags), "
        f"{stats['feed_files_count']} feeds/APIs, "
        f"{stats['static_files_count']} static files "
        f"[base_path={bp_label}, cname={cname_label}] -> {stats['dist_dir']} "
        f"({stats['elapsed_ms']} ms)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
