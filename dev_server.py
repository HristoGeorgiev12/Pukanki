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


DEAD_PATTERNS = [
    "404 not found",
    "404 - не е намерен",
    "не е намерен",
    "file was deleted",
    "file has been removed",
    "video has been removed",
    "video not found",
    "file not found",
    "deleted due to copyright",
    "not found or deleted",
    "file no longer exists",
    "the video was deleted",
    "file is no longer available",
    "expired or has been deleted",
    "the file expired",
    "video record missing",
]


def check_single_player_url(url: str, timeout_sec: float = 2.5) -> dict:
    if not url or not url.startswith("http"):
        return {"url": url, "alive": False, "status": 0}

    # YouTube is assumed alive
    if "youtube.com" in url or "youtu.be" in url:
        return {"url": url, "alive": True, "status": 200}

    import re
    import urllib.parse

    # 1. Byse / Filemoon: check the actual video record API
    fmo_match = re.search(r'(?:filemoon\.(?:sx|to|in|me|net)|bysesukior\.com)/e/([a-zA-Z0-9_-]+)', url, re.I)
    if fmo_match:
        vid_id = fmo_match.group(1)
        api_url = f"https://bysesukior.com/api/videos/{vid_id}/"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout_sec) as r:
                if r.status == 200:
                    return {"url": url, "alive": True, "status": 200}
                return {"url": url, "alive": False, "status": r.status}
        except urllib.error.HTTPError as e:
            return {"url": url, "alive": False, "status": e.code, "reason": "filemoon video missing"}
        except Exception:
            pass

    # 2. Vidon: check POST /dl with file_code
    vidon_match = re.search(r'vidon\.(?:to|me|cc)/e/([a-zA-Z0-9_-]+)', url, re.I)
    if vidon_match:
        file_code = vidon_match.group(1)
        try:
            data = urllib.parse.urlencode({"op": "embed", "file_code": file_code, "auto": "1"}).encode()
            req = urllib.request.Request(
                "https://vidon.to/dl",
                data=data,
                headers={"User-Agent": "Mozilla/5.0", "Referer": f"https://vidon.to/e/{file_code}"}
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as r:
                body = r.read().decode("utf-8", errors="ignore")
                if "jwplayer" in body or "sources" in body or ".m3u8" in body:
                    return {"url": url, "alive": True, "status": 200}
                if any(p in body.lower() for p in DEAD_PATTERNS):
                    return {"url": url, "alive": False, "status": 404, "reason": "vidon deleted"}
        except urllib.error.HTTPError as e:
            return {"url": url, "alive": False, "status": e.code}
        except Exception:
            pass

    # 3. Standard GET check for all other providers
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            code = resp.status
            raw = resp.read(4096).decode("utf-8", errors="ignore").lower()
            for pat in DEAD_PATTERNS:
                if pat in raw:
                    return {"url": url, "alive": False, "status": 404, "reason": pat}
            return {"url": url, "alive": (200 <= code < 400), "status": code}
    except urllib.error.HTTPError as e:
        return {"url": url, "alive": False, "status": e.code}
    except Exception:
        return {"url": url, "alive": False, "status": 0}


class LocalDevHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Prevent browser caching during local development
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_HEAD(self):
        if self.path.startswith("/api/ping"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "2")
            self.end_headers()
            return
        super().do_HEAD()

    def do_GET(self):
        print(f"[*] GET {self.path}", flush=True)
        if self.path.startswith("/api/ping"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"OK")
            return
        if self.path.startswith("/api/speedtest"):
            chunk = b"X" * (256 * 1024)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(chunk)))
            self.end_headers()
            self.wfile.write(chunk)
            return
        super().do_GET()

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
