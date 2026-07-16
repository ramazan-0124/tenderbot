from __future__ import annotations

import json
import mimetypes
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from smart_search import smart_search


ROOT = Path(__file__).parent
STATIC = ROOT / "static"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_file(STATIC / "index.html")
            return

        if parsed.path.startswith("/static/"):
            self.send_file(STATIC / parsed.path.removeprefix("/static/"))
            return

        if parsed.path == "/api/search":
            params = urllib.parse.parse_qs(parsed.query)
            query = params.get("q", [""])[0].strip()
            min_amount = parse_float(params.get("min_amount", ["0"])[0])
            limit = int(parse_float(params.get("limit", ["30"])[0]) or 30)
            status_filter = params.get("status", ["all"])[0].strip() or "all"
            exclude_terms = parse_terms(params.get("exclude", [""])[0])
            if not query:
                self.send_json({"query": "", "terms": [], "searchPhrases": [], "count": 0, "items": []})
                return
            self.send_json(
                smart_search(
                    query=query,
                    min_amount=min_amount,
                    limit=limit,
                    status_filter=status_filter,
                    exclude_terms=exclude_terms,
                )
            )
            return

        self.send_error(404)

    def send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        return


def parse_float(value: str) -> float:
    try:
        return float(value.replace(" ", "").replace(",", "."))
    except ValueError:
        return 0


def parse_terms(value: str) -> list[str]:
    return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8090"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Tender smart search: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
