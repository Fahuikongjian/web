"""Local static preview server for the generated ``dist/`` site.

Serves clean directory URLs (``/``, ``/articles/``, ``/articles/<slug>/``)
and falls back to ``dist/404.html`` with HTTP status 404 on unknown paths.
"""

from __future__ import annotations

import argparse
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
import urllib.parse


DEFAULT_DIST_DIR = Path(__file__).resolve().parent.parent / "dist"


class BlogHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Static file handler with custom 404 page support and clean MIME types."""

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".xml": "application/xml; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
        ".webp": "image/webp",
        ".woff2": "font/woff2",
    }

    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        """Serve ``404.html`` when a requested resource does not exist."""
        if code == HTTPStatus.NOT_FOUND:
            not_found_file = Path(self.directory) / "404.html"
            if not_found_file.is_file():
                body = not_found_file.read_bytes()
                self.send_response(HTTPStatus.NOT_FOUND, "Not Found")
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)
                return
        super().send_error(code, message, explain)

    def translate_path(self, path: str) -> str:
        """Map URL path safely to a file inside ``self.directory``."""
        parsed = urllib.parse.urlsplit(path)
        decoded = urllib.parse.unquote(parsed.path, errors="surrogatepass")
        parts = [part for part in decoded.split("/") if part and part not in (".", "..")]
        root = Path(self.directory).resolve()
        candidate = root.joinpath(*parts)
        try:
            candidate.resolve().relative_to(root)
        except ValueError:
            return str(root / "__forbidden__")
        return str(candidate)

    def log_message(self, format: str, *args: object) -> None:
        """Emit concise request logs to stderr."""
        sys.stderr.write(f"[serve] {self.address_string()} - {format % args}\n")


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    directory: Path | str = DEFAULT_DIST_DIR,
) -> ThreadingHTTPServer:
    """Create a configured ``ThreadingHTTPServer`` serving ``directory``."""
    dist_path = Path(directory).resolve()
    if not dist_path.is_dir():
        raise FileNotFoundError(
            f"Build directory not found: {dist_path}. Run scripts/build.py first."
        )
    handler_cls = partial(BlogHTTPRequestHandler, directory=os.fspath(dist_path))
    return ThreadingHTTPServer((host, port), handler_cls)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options for the preview server."""
    parser = argparse.ArgumentParser(description="Preview the built static blog site.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_DIST_DIR,
        help="Directory to serve (default: ./dist)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the static HTTP preview server until interrupted."""
    args = parse_args(argv)
    server = create_server(host=args.host, port=args.port, directory=args.dir)
    actual_host, actual_port = server.server_address[:2]
    print(f"Serving {Path(args.dir).resolve()} at http://{actual_host}:{actual_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping preview server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
