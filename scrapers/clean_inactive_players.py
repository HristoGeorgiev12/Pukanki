import glob
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "player_health_cache.json")

# 100% Confirmed Dead Domains / Broken URL prefixes
KNOWN_DEAD_HOSTS = {
    "",
    ".",
    "0.0.0.0.io",
    "0.0.0.0.tv",
    "f",
    "iceyfile.com",
    "myvidplay.com",
    "playmogo.com",
    "rollo.uno",
    "upbolt.to",
    "cloudvideo.tv",
    "vidsrc.xyz",
    "vidsrc-embed.ru",
    "vudeo.io",
    "videobin.co",
    "hlswish.com",
    "playerwish.com",
    "sbrapid.com",
    "streamz.cc",
    "data4.fastshare.cz",
    "data7.fastshare.cz",
    "data9.fastshare.cz",
}

DEAD_BODY_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"file was deleted",
        r"file has been removed",
        r"video has been removed",
        r"video not found",
        r"file not found",
        r"deleted due to copyright",
        r"not found or deleted",
        r"file no longer exists",
        r"the video was deleted",
        r"404 not found",
    ]
]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def load_cache() -> dict[str, bool]:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict[str, bool]) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:
        pass


def get_url_host(url: str) -> str:
    if not url or not url.startswith("http"):
        return ""
    try:
        parts = url.split("/")
        if len(parts) >= 3:
            return parts[2].lower()
    except Exception:
        pass
    return ""


def check_player_url_live(url: str) -> bool:
    host = get_url_host(url)
    if not host or host in KNOWN_DEAD_HOSTS:
        return False

    # External source links / news pages are always kept
    if "filmi9.com/film" in url or "filmi2k.com" in url or "filmizip.com" in url:
        return True

    # OK.ru videoembed, YouTube, VOE redirectors are fast
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
            if resp.status not in (200, 301, 302):
                return False
            # Check small initial chunk for dead file message
            chunk = resp.read(4096).decode("utf-8", errors="ignore")
            for pattern in DEAD_BODY_PATTERNS:
                if pattern.search(chunk):
                    return False
            return True
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return False
        # Some servers return 403 to python bots but work in browser iframe
        if e.code == 403:
            return True
        return False
    except Exception:
        return False


def prune_dead_hosts_from_catalog(filepath: str) -> int:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Грешка при зареждане на {filepath}: {e}")
        return 0

    is_list = isinstance(data, list)
    items = data if is_list else data.get("items", data.get("movies", []))
    if not isinstance(items, list):
        return 0

    removed_count = 0
    modified = False

    for item in items:
        sources = item.get("player_sources")
        if not isinstance(sources, list):
            continue
        cleaned = []
        for s in sources:
            url = s.get("embed_url") or ""
            host = get_url_host(url)
            if not url or host in KNOWN_DEAD_HOSTS:
                removed_count += 1
                modified = True
                continue
            cleaned.append(s)
        item["player_sources"] = cleaned

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Also update corresponding _data.js file
        js_file = filepath.replace(".json", "_data.js")
        if os.path.exists(js_file):
            update_js_file(js_file, data)

    return removed_count


def update_js_file(js_file: str, data: any) -> None:
    basename = os.path.basename(js_file)
    var_map = {
        "movies_data.js": "window.MOVIES_DATA",
        "tv_shows_data.js": "window.TV_SHOWS_DATA",
        "filmi2k_bg_data.js": "window.FILMI2K_BG_DATA",
        "filmi2k_sub_data.js": "window.FILMI2K_SUB_DATA",
        "filmifen_bg_data.js": "window.FILMIFEN_BG_DATA",
        "filmizip_bg_data.js": "window.FILMIZIP_BG_DATA",
        "subtitled_movies_data.js": "window.SUBTITLED_MOVIES_DATA",
        "filmi9_data.js": "window.FILMI9_DATA",
        "bg_serials_data.js": "window.BG_SERIALS_DATA",
    }
    var_name = var_map.get(basename)
    if not var_name:
        return

    with open(js_file, "w", encoding="utf-8") as f:
        f.write(f"{var_name} = ")
        json.dump(data, f, ensure_ascii=False)
        f.write(";\n")


def quick_clean_known_dead() -> int:
    print("[*] Фаза 1: Бързо премахване на известни мъртви домейни и счупени линкове...")
    total_removed = 0
    for p in glob.glob(os.path.join(DATA_DIR, "*.json")):
        if "cache" in p or "sample" in p:
            continue
        cnt = prune_dead_hosts_from_catalog(p)
        if cnt > 0:
            print(f"  [-] {os.path.basename(p)}: премахнати {cnt} мъртви плеъра")
            total_removed += cnt
    print(f"[*] Фаза 1 завършена. Общо премахнати неактивни плеъри: {total_removed}")
    return total_removed


def deep_check_and_clean(max_checks: int = 500) -> None:
    print(f"\n[*] Фаза 2: Дълбока проверка на индивидуални линкове (до {max_checks} проверки)...")
    cache = load_cache()
    print(f"[*] Зареден кеш за състояние на плеъри: {len(cache)} записа")

    # Collect all embed URLs to check
    urls_to_check = []
    seen = set()

    for p in glob.glob(os.path.join(DATA_DIR, "*.json")):
        if "cache" in p or "sample" in p:
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            items = d if isinstance(d, list) else d.get("items", d.get("movies", []))
            for item in items:
                for s in item.get("player_sources", []):
                    u = s.get("embed_url") or ""
                    if u and u.startswith("http") and u not in cache and u not in seen:
                        seen.add(u)
                        urls_to_check.append(u)
        except Exception:
            pass

    print(f"[*] Намерени нови линкове за проверка: {len(urls_to_check)}")
    to_run = urls_to_check[:max_checks]

    checked = 0
    dead_found = 0

    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_url = {executor.submit(check_player_url_live, u): u for u in to_run}
        for fut in as_completed(future_to_url):
            url = future_to_url[fut]
            try:
                is_alive = fut.result()
            except Exception:
                is_alive = False
            cache[url] = is_alive
            checked += 1
            if not is_alive:
                dead_found += 1
            if checked % 100 == 0:
                print(f"  Проверени: {checked}/{len(to_run)} (мъртви открити: {dead_found})")

    save_cache(cache)
    print(f"[*] Проверката приключи. Открити неактивни: {dead_found} от {checked}")

    # Now prune newly confirmed dead URLs
    dead_urls = {u for u, alive in cache.items() if not alive}
    if not dead_urls:
        return

    removed = 0
    for p in glob.glob(os.path.join(DATA_DIR, "*.json")):
        if "cache" in p or "sample" in p:
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else data.get("items", data.get("movies", []))
            modified = False
            for item in items:
                sources = item.get("player_sources")
                if not isinstance(sources, list):
                    continue
                new_sources = [s for s in sources if s.get("embed_url") not in dead_urls]
                if len(new_sources) != len(sources):
                    removed += (len(sources) - len(new_sources))
                    item["player_sources"] = new_sources
                    modified = True
            if modified:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                js_file = p.replace(".json", "_data.js")
                if os.path.exists(js_file):
                    update_js_file(js_file, data)
        except Exception:
            pass

    print(f"[*] Премахнати индивидуални мъртви плеъри от файловете: {removed}")


if __name__ == "__main__":
    quick_clean_known_dead()
    # Check if --deep flag is passed
    if "--deep" in sys.argv:
        limit = 1000
        for arg in sys.argv:
            if arg.startswith("--limit="):
                limit = int(arg.split("=")[1])
        deep_check_and_clean(limit)

