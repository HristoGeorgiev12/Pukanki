#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev_server.py
Локален сървър с поддръжка на статични файлове, no-cache за разработка
и API ендпойнт /api/check-player за паралелна проверка на плеъри.
"""

import http.server
import json
import socketserver
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PORT = 8080


def check_single_player_url(url: str, timeout_sec: float = 2.5) -> dict:
    if not url or not url.startswith("http"):
        return {"url": url, "alive": False, "status": 0}

    # YouTube is assumed alive
    if "youtube.com" in url or "youtu.be" in url:
        return {"url": url, "alive": True, "status": 200}

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            code = resp.status
            raw = resp.read(2048).decode("utf-8", errors="ignore").lower()
            if any(k in raw for k in ["404 - не е намерен", "file not found", "video not found", "файлът не е намерен"]):
                return {"url": url, "alive": False, "status": 404}
            return {"url": url, "alive": (200 <= code < 400), "status": code}
    except urllib.error.HTTPError as e:
        return {"url": url, "alive": False, "status": e.code}
    except Exception:
        # If timeout or blocked, keep neutral/true
        return {"url": url, "alive": True, "status": 0}


class LocalDevHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Prevent browser caching during local development
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_POST(self):
        if self.path.startswith("/api/check-player"):
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                data = {}

            urls = data.get("urls", [])
            if not isinstance(urls, list):
                urls = []

            results = []
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(check_single_player_url, u) for u in urls]
                results = [f.result() for f in futures]

            active_index = -1
            for i, r in enumerate(results):
                if r.get("alive"):
                    active_index = i
                    break

            payload = json.dumps({"results": results, "activeIndex": active_index}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_error(404, "Not Found")


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), LocalDevHandler) as httpd:
        print(f"[*] Dev server running at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
