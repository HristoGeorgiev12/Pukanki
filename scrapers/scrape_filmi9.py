from concurrent.futures import ThreadPoolExecutor, as_completed
import glob
import json
import os
import re
import ssl
import sys
import threading
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_JSON = os.path.join(DATA_DIR, "filmi9_data.json")
OUTPUT_JS = os.path.join(DATA_DIR, "filmi9_data.js")
SITEMAP_URL = "https://filmi9.com/sitemaps/movies.xml"

MAX_WORKERS = 10
SAVE_EVERY = 50

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
}

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def fetch_url(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
                if resp.status == 200:
                    return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        time.sleep(0.5 * (attempt + 1))
    return ""


def clean_norm(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "", str(s).lower())


def get_existing_keys() -> set[str]:
    keys = set()
    for p in glob.glob(os.path.join(DATA_DIR, "*.json")):
        if "filmi9" in p or "cache" in p or "sample" in p:
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            items = d if isinstance(d, list) else d.get("items", d.get("movies", []))
            for x in items:
                t = clean_norm(x.get("title"))
                ot = clean_norm(x.get("original_title"))
                y = x.get("year")
                tmdb = x.get("tmdb_id")
                imdb = x.get("imdb_id")
                if tmdb:
                    keys.add(f"tmdb_{tmdb}")
                if imdb:
                    keys.add(f"imdb_{imdb}")
                if t and y:
                    keys.add(f"ty_{t}_{y}")
                if ot and y:
                    keys.add(f"oy_{ot}_{y}")
                if t:
                    keys.add(f"t_{t}")
        except Exception:
            pass
    return keys


def parse_movie_page(url: str) -> dict | None:
    html = fetch_url(url)
    if not html:
        return None

    slug = url.rstrip("/").split("/")[-1]
    parts = [m.group(1) for m in re.finditer(r'self\.__next_f\.push\(\[1,"(.*?[^\\])"\]\)', html, re.DOTALL)]
    full = "".join(parts) if parts else html

    pos_img = full.find("movieImage")
    if pos_img == -1:
        pos_img = full.find("coverPhoto")
    if pos_img == -1:
        return None

    start = full.rfind('{\\"_id\\":', 0, pos_img)
    if start == -1:
        start = full.rfind('{"_id":', 0, pos_img)
    if start == -1:
        return None

    pos_v = full.find("videoUrl", pos_img)
    if pos_v == -1:
        pos_v = full.find("sources", pos_img)
    if pos_v == -1:
        return None

    m_slug = re.search(r'(?:\\"slug\\"|"slug")\s*:\s*(?:\\"[^"]+\\"|"[^"]+")\}', full[pos_v:])
    if m_slug:
        end = pos_v + m_slug.end()
    else:
        end = full.find("}}", pos_v) + 1
    if end <= start:
        return None

    raw_snippet = full[start:end]
    if '\\"' in raw_snippet:
        raw_snippet = raw_snippet.replace('\\"', '"').replace("\\\\", "\\")

    try:
        data = json.loads(raw_snippet)
    except Exception:
        return None

    raw_title = data.get("title") or ""
    bg_title = raw_title
    orig_title = ""
    if "/" in raw_title:
        parts = [p.strip() for p in raw_title.split("/") if p.strip()]
        if len(parts) >= 2:
            orig_title = parts[0]
            bg_title = parts[1]

    # Clean year if inside title
    ym = re.search(r"\((19\d{2}|20\d{2})\)", bg_title)
    if ym:
        bg_title = bg_title[: ym.start()].strip()

    year = data.get("year")
    genres = [g["name"] for g in data.get("genres", []) if isinstance(g, dict) and g.get("name")]
    if not genres and "genres" in data and isinstance(data["genres"], list):
        genres = [str(g) for g in data["genres"] if g]

    actors = [a["name"] for a in data.get("actors", []) if isinstance(a, dict) and a.get("name")]
    if not actors and "actors" in data and isinstance(data["actors"], list):
        actors = [str(a) for a in data["actors"] if a]

    sources_list = data.get("sources") or []
    video_url = data.get("videoUrl") or ""

    player_sources = []
    seen_embeds = set()

    if video_url:
        seen_embeds.add(video_url)
        vname = "💬 VOE" if "voe" in video_url.lower() else "💬 VidRu"
        player_sources.append({
            "id": f"filmi9-1",
            "name": vname,
            "group": "sub",
            "direct_embed": True,
            "embed_url": video_url,
        })

    for s in sources_list:
        if not isinstance(s, dict):
            continue
        s_url = s.get("url") or ""
        if not s_url or s_url in seen_embeds:
            continue
        seen_embeds.add(s_url)
        s_name = s.get("name") or "Сървър"
        if "voe" in s_name.lower():
            s_name = "💬 VOE"
        elif "vidru" in s_name.lower() or "vsembed" in s_url.lower():
            s_name = "💬 VidRu"
        else:
            s_name = f"💬 {s_name}"
        player_sources.append({
            "id": f"filmi9-{len(player_sources) + 1}",
            "name": s_name,
            "group": "sub",
            "direct_embed": True,
            "embed_url": s_url,
        })

    # Add external source link
    player_sources.append({
        "id": f"filmi9-ext",
        "name": "💬 Filmi9 (Нов таб)",
        "group": "sub",
        "direct_embed": False,
        "embed_url": url,
    })

    poster = data.get("movieImage") or data.get("coverPhoto") or ""
    backdrop = data.get("coverPhoto") or poster

    return {
        "post_id": f"filmi9-{slug}",
        "tmdb_id": data.get("tmdb_id"),
        "imdb_id": data.get("imdb_id"),
        "type": "movie",
        "slug": slug,
        "url": url,
        "title": bg_title or raw_title,
        "original_title": orig_title,
        "year": year,
        "age_rating": None,
        "duration_minutes": data.get("movieLength"),
        "rating": data.get("rating"),
        "countries": [c["name"] for c in data.get("countries", []) if isinstance(c, dict) and c.get("name")],
        "genres": genres if genres else ["БГ Субтитри"],
        "tags": [orig_title.lower(), "filmi9"] if orig_title else ["filmi9"],
        "actors": actors,
        "directors": [data["director"]] if data.get("director") else [],
        "overview": data.get("description") or "",
        "poster_url": poster,
        "backdrop_url": backdrop,
        "is_bg_audio": False,
        "is_subtitled": True,
        "origins": ["Filmi9"],
        "player_sources": player_sources,
    }


def save_catalog(items: list[dict]) -> None:
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.FILMI9_DATA = ")
        json.dump(items, f, ensure_ascii=False)
        f.write(";\n")


def main() -> None:
    print("[*] Зареждане на съществуващи ключове...")
    existing_keys = get_existing_keys()
    print(f"[*] Намерени съществуващи ключове в базата: {len(existing_keys)}")

    existing_filmi9 = {}
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                d = json.load(f)
                for item in d:
                    if item.get("url"):
                        existing_filmi9[item["url"]] = item
        except Exception:
            pass

    print(f"[*] Кеширани вече от Filmi9: {len(existing_filmi9)}")

    print(f"[*] Изтегляне на sitemap от {SITEMAP_URL}...")
    sitemap_xml = fetch_url(SITEMAP_URL)
    all_urls = re.findall(r"<loc>([^<]+)</loc>", sitemap_xml)
    print(f"[*] Общо филми в sitemap: {len(all_urls)}")

    to_scrape = [u for u in all_urls if u not in existing_filmi9]
    print(f"[*] За обработка: {len(to_scrape)}")

    lock = threading.Lock()
    done = 0
    new_added = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(parse_movie_page, u): u for u in to_scrape}
        for fut in as_completed(futures):
            res = fut.result()
            with lock:
                done += 1
                if res:
                    existing_filmi9[res["url"]] = res
                    new_added += 1

                if done % SAVE_EVERY == 0 or done == len(to_scrape):
                    ordered = [existing_filmi9[u] for u in all_urls if u in existing_filmi9]
                    save_catalog(ordered)
                    print(f"[*] Прогрес: {done}/{len(to_scrape)} (активни Filmi9: {len(ordered)})")

    ordered = [existing_filmi9[u] for u in all_urls if u in existing_filmi9]
    save_catalog(ordered)
    print(f"[SUCCESS] Готово! Общо записани филми от Filmi9: {len(ordered)}")


if __name__ == "__main__":
    main()
