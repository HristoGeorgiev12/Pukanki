import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

OUT_JSON = os.path.join(DATA_DIR, "videa_dock.json")
OUT_JS = os.path.join(DATA_DIR, "videa_dock_data.js")
TMDB_API_KEY = "4e44d9029b1270a757cddc766a1bcb63"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
}

TMDB_GENRES_BG = {
    28: "Екшън",
    12: "Приключенски",
    16: "Анимация",
    35: "Комедия",
    80: "Криминален",
    99: "Документален",
    18: "Драма",
    10751: "Семеен",
    14: "Фентъзи",
    36: "Исторически",
    27: "Ужаси",
    10402: "Музикален",
    9648: "Мистерия",
    10749: "Романтичен",
    878: "Фантастика",
    10770: "ТВ Филм",
    53: "Трилър",
    10752: "Военен",
    37: "Уестърн",
}


def parse_videa_title(raw_title: str):
    t = re.sub(r"\s+", " ", raw_title or "").strip()
    m = re.search(r"\((\d{4})\)", t)
    year = int(m.group(1)) if m else None
    if m:
        bg_title = t[:m.start()].strip(" -–—:")
        orig_title = t[m.end():].strip(" -–—:")
    else:
        bg_title = t
        orig_title = ""
    if not bg_title:
        bg_title = orig_title or t
    return bg_title, orig_title, year


def collect_channel_videos():
    urls = [
        "https://videa.hu/tagok/DOCK-2318764",
        "https://videa.hu/tagok/DOCK-2318764?oldest",
        "https://videa.hu/tagok/DOCK-2318764?popular",
    ]
    found = {}  # vid_id -> {url, raw_title}
    for u in urls:
        try:
            r = requests.get(u, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue
            html = r.text
            for href, title in re.findall(
                r'<a[^>]+href="(https://videa\.hu/videok/[^"]+)"[^>]*>([^<]{4,180})</a>',
                html,
            ):
                vid_id = href.rstrip("/").split("-")[-1]
                if not vid_id or len(vid_id) < 8:
                    continue
                if vid_id not in found:
                    found[vid_id] = {
                        "vid_id": vid_id,
                        "video_url": href,
                        "raw_title": title.strip(),
                    }
        except Exception as e:
            print(f"[WARN] Failed {u}: {e}")
    return list(found.values())


def enrich_with_tmdb(entry):
    vid_id = entry["vid_id"]
    bg_title, orig_title, year = parse_videa_title(entry["raw_title"])
    query = orig_title if orig_title else bg_title

    tmdb_data = None
    for q_try in ([query, bg_title] if query != bg_title else [query]):
        try:
            params = {
                "api_key": TMDB_API_KEY,
                "query": q_try,
                "language": "bg-BG",
                "include_adult": "false",
            }
            if year:
                params["year"] = year
            resp = requests.get(
                "https://api.themoviedb.org/3/search/movie",
                params=params,
                timeout=12,
            )
            if resp.status_code == 200:
                results = resp.json().get("results") or []
                if results:
                    tmdb_data = results[0]
                    break
        except Exception:
            pass

    tmdb_id = tmdb_data.get("id") if tmdb_data else None
    duration = None
    overview = (tmdb_data.get("overview") or "").strip() if tmdb_data else ""
    rating = round(float(tmdb_data.get("vote_average") or 0), 1) if tmdb_data else 0.0
    poster_url = (
        f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"
        if tmdb_data and tmdb_data.get("poster_path")
        else ""
    )
    backdrop_url = (
        f"https://image.tmdb.org/t/p/w780{tmdb_data['backdrop_path']}"
        if tmdb_data and tmdb_data.get("backdrop_path")
        else poster_url
    )
    genres = []
    if tmdb_data and tmdb_data.get("genre_ids"):
        for gid in tmdb_data["genre_ids"]:
            if gid in TMDB_GENRES_BG:
                genres.append(TMDB_GENRES_BG[gid])

    if tmdb_id:
        try:
            det = requests.get(
                f"https://api.themoviedb.org/3/movie/{tmdb_id}",
                params={"api_key": TMDB_API_KEY, "language": "bg-BG"},
                timeout=10,
            )
            if det.status_code == 200:
                dj = det.json()
                duration = dj.get("runtime") or None
                if not overview and dj.get("overview"):
                    overview = dj["overview"].strip()
        except Exception:
            pass

    embed_url = f"https://videa.hu/player?v={vid_id}"
    return {
        "tmdb_id": tmdb_id,
        "title": bg_title,
        "original_title": orig_title or (tmdb_data.get("original_title") if tmdb_data else ""),
        "year": year,
        "rating": rating,
        "duration_minutes": duration,
        "genres": genres,
        "overview": overview,
        "poster_url": poster_url,
        "backdrop_url": backdrop_url,
        "url": entry["video_url"],
        "is_bg_audio": False,
        "is_subtitled": True,
        "type": "movie",
        "source_site": "videa_dock",
        "player_sources": [
            {
                "name": "💬 Videa",
                "group": "sub",
                "embed_url": embed_url,
                "direct_embed": True,
            }
        ],
    }


def main():
    raw_videos = collect_channel_videos()
    print(f"Found {len(raw_videos)} unique videos on Videa.hu DOCK channel")

    # Deduplicate same movie (title + year) keeping multiple Videa sources if uploaded twice
    items = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(enrich_with_tmdb, v) for v in raw_videos]
        for fut in as_completed(futs):
            try:
                items.append(fut.result())
            except Exception as e:
                print(f"[WARN] Enrich error: {e}")

    by_key = {}
    for it in items:
        k = (it.get("tmdb_id") or f"{it['title'].lower()}|{it.get('year') or 0}")
        if k not in by_key:
            by_key[k] = it
        else:
            existing_urls = {s["embed_url"] for s in by_key[k]["player_sources"]}
            for s in it["player_sources"]:
                if s["embed_url"] not in existing_urls:
                    by_key[k]["player_sources"].append(s)

    final_items = sorted(
        by_key.values(),
        key=lambda x: (-(x.get("year") or 0), -(x.get("rating") or 0)),
    )

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_items, f, ensure_ascii=False, indent=2)
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write("window.VIDEA_DOCK_DATA = ")
        json.dump(final_items, f, ensure_ascii=False)
        f.write(";\n")

    matched = sum(1 for x in final_items if x.get("tmdb_id"))
    print(f"Saved {len(final_items)} unique movies to {OUT_JSON} ({matched} matched with TMDB)")


if __name__ == "__main__":
    main()
