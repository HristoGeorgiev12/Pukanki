import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "tmdb_credits_cache.json")

TMDB_API_KEY = "4e44d9029b1270a757cddc766a1bcb63"
MAX_WORKERS = 16

session = requests.Session()


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    tmp_path = f"{CACHE_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp_path, CACHE_FILE)


def fetch_tmdb_credits(media_type: str, tmdb_id: int) -> dict:
    endpoint = "tv" if media_type == "tv" else "movie"
    url = f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}/credits"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "bg-BG",
    }
    for attempt in range(3):
        try:
            resp = session.get(url, params=params, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                cast_raw = data.get("cast", [])
                crew_raw = data.get("crew", [])

                actors = []
                for member in cast_raw[:10]:
                    name = (member.get("name") or "").strip()
                    if name and name not in actors:
                        actors.append(name)

                directors = []
                if media_type == "tv":
                    target_jobs = ["Director", "Creator", "Series Director", "Executive Producer"]
                else:
                    target_jobs = ["Director"]

                for member in crew_raw:
                    job = member.get("job") or ""
                    if job in target_jobs:
                        name = (member.get("name") or "").strip()
                        if name and name not in directors:
                            directors.append(name)
                    if len(directors) >= 4:
                        break

                return {
                    "actors": actors,
                    "directors": directors,
                }
            if resp.status_code in (404, 400):
                return {"actors": [], "directors": []}
            if resp.status_code == 429:
                time.sleep(1.0 + attempt)
        except Exception:
            time.sleep(0.5)
    return {"actors": [], "directors": []}


def save_file_and_js(data: list[dict], json_path: str, js_path: str, js_var: str):
    tmp_json = f"{json_path}.tmp"
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_json, json_path)

    tmp_js = f"{js_path}.tmp"
    with open(tmp_js, "w", encoding="utf-8") as f:
        f.write(f"window.{js_var} = {json.dumps(data, ensure_ascii=False)};\n")
    os.replace(tmp_js, js_path)


def enrich_items(items: list[dict], media_type: str, cache: dict, label: str) -> int:
    to_fetch = []
    for item in items:
        tmdb_id = item.get("tmdb_id")
        if not tmdb_id:
            continue
        cache_key = f"{media_type}_{tmdb_id}"
        if cache_key in cache:
            cached = cache[cache_key]
            if not item.get("actors") and cached.get("actors"):
                item["actors"] = cached["actors"]
            if not item.get("directors") and cached.get("directors"):
                item["directors"] = cached["directors"]
        else:
            to_fetch.append((item, cache_key, tmdb_id))

    print(f"[{label}] Total items: {len(items)}, Already cached: {len(items) - len(to_fetch)}, To fetch: {len(to_fetch)}")

    if not to_fetch:
        return 0

    fetched_count = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {
            executor.submit(fetch_tmdb_credits, media_type, tmdb_id): (item, cache_key)
            for item, cache_key, tmdb_id in to_fetch
        }

        for i, future in enumerate(as_completed(future_map), 1):
            item, cache_key = future_map[future]
            try:
                res = future.result()
                cache[cache_key] = res
                if res.get("actors"):
                    item["actors"] = res["actors"]
                if res.get("directors"):
                    item["directors"] = res["directors"]
                fetched_count += 1
            except Exception as e:
                pass

            if i % 100 == 0 or i == len(to_fetch):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"[{label}] Progress: {i}/{len(to_fetch)} ({i*100//len(to_fetch)}%) | {rate:.1f} req/s")
                save_cache(cache)

    save_cache(cache)
    return fetched_count


def parse_filmi2k_cast(html: str) -> tuple[list[str], list[str]]:
    actors = []
    directors = []
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")

    d_match = re.search(r"Режисьор\s*:\s*([^\r\n]+)", text, re.I)
    if d_match:
        raw_d = d_match.group(1).split("В ролите")[0].strip()
        directors = [d.strip() for d in re.split(r"[,;/]+", raw_d) if d.strip() and len(d.strip()) > 1]

    a_match = re.search(r"В\s*ролите\s*:\s*([^\r\n]+)", text, re.I)
    if a_match:
        raw_a = a_match.group(1)
        for sw in ["Държава", "Година", "Времетраене", "IMDb", "Сюжет"]:
            raw_a = raw_a.split(sw)[0]
        actors = [a.strip() for a in re.split(r"[,;/]+", raw_a) if a.strip() and a.strip() != "и др." and len(a.strip()) > 1]

    return actors[:10], directors[:4]


def enrich_filmi2k():
    filmi2k_json = os.path.join(DATA_DIR, "filmi2k_bg.json")
    filmi2k_js = os.path.join(DATA_DIR, "filmi2k_bg_data.js")
    if not os.path.exists(filmi2k_json):
        return

    with open(filmi2k_json, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"\n[Filmi2k] Checking {len(items)} items for actors/directors...")
    to_scrape = [x for x in items if not x.get("actors") and x.get("url")]
    print(f"[Filmi2k] Needs scraping: {len(to_scrape)}")

    if not to_scrape:
        return

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}

    def scrape_one(item):
        url = item.get("url")
        try:
            r = session.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                r.encoding = "utf-8"
                actors, directors = parse_filmi2k_cast(r.text)
                if actors:
                    item["actors"] = actors
                if directors:
                    item["directors"] = directors
                return bool(actors or directors)
        except Exception:
            pass
        return False

    success = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(scrape_one, item) for item in to_scrape]
        for i, fut in enumerate(as_completed(futures), 1):
            if fut.result():
                success += 1
            if i % 100 == 0 or i == len(to_scrape):
                print(f"[Filmi2k] Progress: {i}/{len(to_scrape)} | Enriched: {success}")

    save_file_and_js(items, filmi2k_json, filmi2k_js, "FILMI2K_BG_DATA")
    print(f"[Filmi2k] Done! Enriched {success} items.")


def main():
    print("=== STARTING CREDITS ENRICHMENT ===")
    cache = load_cache()
    print(f"Initial cache entries: {len(cache)}")

    # 1. TV SHOWS
    tv_json = os.path.join(DATA_DIR, "tv_shows.json")
    tv_js = os.path.join(DATA_DIR, "tv_shows_data.js")
    if os.path.exists(tv_json):
        with open(tv_json, "r", encoding="utf-8") as f:
            tv_items = json.load(f)
        enrich_items(tv_items, "tv", cache, "TV Shows")
        save_file_and_js(tv_items, tv_json, tv_js, "TV_SHOWS_DATA")

    # 2. MOVIES
    movies_json = os.path.join(DATA_DIR, "movies.json")
    movies_js = os.path.join(DATA_DIR, "movies_data.js")
    if os.path.exists(movies_json):
        with open(movies_json, "r", encoding="utf-8") as f:
            movies_items = json.load(f)
        enrich_items(movies_items, "movie", cache, "Movies")
        save_file_and_js(movies_items, movies_json, movies_js, "MOVIES_DATA")

    # 3. FILMI2K
    enrich_filmi2k()

    print("\n=== CREDITS ENRICHMENT COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()

