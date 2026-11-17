import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "tmdb_genres_cache.json")

TMDB_API_KEY = "4e44d9029b1270a757cddc766a1bcb63"
MAX_WORKERS = 20

session = requests.Session()

CANONICAL_GENRE_MAP = {
    # Horror
    "ужас": "Ужаси",
    "ужаси": "Ужаси",
    
    # Adventure
    "приключение": "Приключенски",
    "приключенски": "Приключенски",
    "екшън и приключение": "Приключенски",
    
    # Romance
    "романс": "Романтичен",
    "романтичен": "Романтичен",
    
    # Sci-Fi
    "научна-фантастика": "Научна фантастика",
    "фантастика": "Научна фантастика",
    "научна-фантастика и фентъзи": "Научна фантастика",
    
    # History
    "исторически": "Исторически",
    "история": "Исторически",
    
    # Music
    "музика": "Музикален",
    "музикален": "Музикален",
    "мюзикъл": "Музикален",
    
    # Sport
    "спортен": "Спортен",
    "спортни": "Спортен",
    
    # War
    "военен": "Военен",
    "военен и политически": "Военен",
    
    # Family / Kids
    "семеен": "Семеен",
    "детски": "Семеен",
    
    # Core TMDB genres
    "екшън": "Екшън",
    "комедия": "Комедия",
    "криминален": "Криминален",
    "драма": "Драма",
    "фентъзи": "Фентъзи",
    "мистерия": "Мистерия",
    "анимация": "Анимация",
    "трилър": "Трилър",
    "документален": "Документален",
    "уестърн": "Уестърн",
    "телевизионен филм": "Телевизионен филм",
    
    # Valid thematic categories
    "европейски": "Европейски",
    "руски": "Руски",
    "азиатски": "Азиатски",
    "скандинавски": "Скандинавски",
    "турски": "Турски",
    "индийски": "Индийски",
    "български": "Български",
    "коледни": "Коледни",
    "тийн": "Тийн",
    "биографичен": "Биографичен",
    "еротичен": "Еротичен",
    "риалити": "Риалити",
}

DISCARD_GENRES = {"бг аудио", "бг субтитри", "сериал", "сериали", "сапун"}


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


def normalize_genre_list(raw_genres: list) -> list:
    if not isinstance(raw_genres, list):
        return []
    cleaned = []
    for g in raw_genres:
        if not g or not isinstance(g, str):
            continue
        gl = g.strip().lower()
        if gl in DISCARD_GENRES:
            continue
        canonical = CANONICAL_GENRE_MAP.get(gl, g.strip())
        if canonical and canonical not in cleaned:
            cleaned.append(canonical)
    return cleaned


def fetch_tmdb_genres(media_type: str, tmdb_id: int) -> list:
    endpoint = "tv" if media_type == "tv" else "movie"
    url = f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "bg-BG",
    }
    for attempt in range(3):
        try:
            resp = session.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                raw_genres = [g.get("name") for g in data.get("genres", []) if g.get("name")]
                return normalize_genre_list(raw_genres)
            if resp.status_code in (404, 400):
                return []
            if resp.status_code == 429:
                time.sleep(1.0 + attempt)
        except Exception:
            time.sleep(0.5)
    return []


def save_file_and_js(data: list, json_path: str, js_path: str, js_var: str):
    tmp_json = f"{json_path}.tmp"
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_json, json_path)

    tmp_js = f"{js_path}.tmp"
    with open(tmp_js, "w", encoding="utf-8") as f:
        f.write(f"window.{js_var} = {json.dumps(data, ensure_ascii=False)};\n")
    os.replace(tmp_js, js_path)


def enrich_dataset(json_file: str, js_file: str, js_var: str, default_media_type: str, cache: dict):
    json_path = os.path.join(DATA_DIR, json_file)
    js_path = os.path.join(DATA_DIR, js_file)
    if not os.path.exists(json_path):
        return

    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not isinstance(items, list):
        return

    to_fetch = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_genres = item.get("genres") or []
        for g in raw_genres:
            gl = str(g).strip().lower()
            if "аудио" in gl:
                item["is_bg_audio"] = True
            if "субтитри" in gl:
                item["is_subtitled"] = True

        tmdb_id = item.get("tmdb_id")
        mtype = item.get("type") or default_media_type
        if tmdb_id:
            cache_key = f"{mtype}_{tmdb_id}"
            if cache_key in cache:
                cached_genres = cache[cache_key]
                if cached_genres:
                    item["genres"] = cached_genres
                else:
                    item["genres"] = normalize_genre_list(raw_genres)
            else:
                to_fetch.append((item, cache_key, mtype, int(tmdb_id)))
        else:
            item["genres"] = normalize_genre_list(raw_genres)

    print(f"[{json_file}] Total: {len(items)}, To fetch from TMDB: {len(to_fetch)}")

    if to_fetch:
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {
                executor.submit(fetch_tmdb_genres, mtype, tid): (item, ckey)
                for item, ckey, mtype, tid in to_fetch
            }

            for i, future in enumerate(as_completed(future_map), 1):
                item, ckey = future_map[future]
                try:
                    genres = future.result()
                    cache[ckey] = genres
                    if genres:
                        item["genres"] = genres
                    else:
                        item["genres"] = normalize_genre_list(item.get("genres") or [])
                except Exception:
                    item["genres"] = normalize_genre_list(item.get("genres") or [])

                if i % 100 == 0 or i == len(to_fetch):
                    elapsed = time.time() - start_time
                    rate = i / elapsed if elapsed > 0 else 0
                    print(f"[{json_file}] {i}/{len(to_fetch)} ({i*100//len(to_fetch)}%) | {rate:.1f} req/s")
                    save_cache(cache)

        save_cache(cache)

    save_file_and_js(items, json_path, js_path, js_var)
    print(f"[{json_file}] Saved clean enriched data to {json_file} and {js_file}!")


def main():
    print("=== Starting TMDB Genre Enrichment and Canonical Normalization ===")
    cache = load_cache()
    print(f"Loaded existing TMDB genre cache: {len(cache)} entries.")

    datasets = [
        ("movies.json", "movies_data.js", "MOVIES_DATA", "movie"),
        ("tv_shows.json", "tv_shows_data.js", "TV_SHOWS_DATA", "tv"),
        ("filmi9_data.json", "filmi9_data.js", "FILMI9_DATA", "movie"),
        ("filmi2k_bg.json", "filmi2k_bg_data.js", "FILMI2K_BG_DATA", "movie"),
        ("filmi2k_sub.json", "filmi2k_sub_data.js", "FILMI2K_SUB_DATA", "movie"),
        ("filmifen_bg.json", "filmifen_bg_data.js", "FILMIFEN_BG_DATA", "movie"),
        ("filmizip_bg.json", "filmizip_bg_data.js", "FILMIZIP_BG_DATA", "movie"),
        ("playtube_bg.json", "playtube_bg_data.js", "PLAYTUBE_BG_DATA", "movie"),
        ("bg_serials.json", "bg_serials_data.js", "BG_SERIALS_DATA", "tv"),
        ("subtitled_movies.json", "subtitled_movies_data.js", "SUBTITLED_MOVIES_DATA", "movie"),
    ]

    for json_file, js_file, js_var, mtype in datasets:
        enrich_dataset(json_file, js_file, js_var, mtype, cache)

    print("\n=== ALL DATASETS SUCCESSFULLY ENRICHED & CANONICALIZED! ===")


if __name__ == "__main__":
    main()
