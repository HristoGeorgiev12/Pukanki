from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import threading
import time
from bs4 import BeautifulSoup
import requests

BASE_URL = "https://filmifen.com/filmi-bg-audio/"
SITE_ORIGIN = "https://filmifen.com"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_JSON = os.path.join(DATA_DIR, "filmifen_bg.json")
OUTPUT_JS = os.path.join(DATA_DIR, "filmifen_bg_data.js")
MAX_WORKERS = 14

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
}

PLAYER_KEY_LABELS = {
    "vdn": "🇧🇬 Vidon",
    "icf": "🇧🇬 IceyFile",
    "okr": "🇧🇬 OK.ru",
    "fmo": "🇧🇬 Filemoon",
    "voe": "🇧🇬 VOE",
    "ytb": "🇧🇬 YouTube",
}


def fetch_html(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                return resp.text
        except requests.RequestException:
            pass
        time.sleep(0.8 * (attempt + 1))
    return ""


def detect_total_pages() -> int:
    html = fetch_html(BASE_URL)
    if not html:
        return 157
    soup = BeautifulSoup(html, "html.parser")
    max_page = 1
    for a_tag in soup.select(".pagination a, .page-numbers, .wp-pagenavi a, .nav-links a, a[href*='/page/']"):
        href = a_tag.get("href") or ""
        m = re.search(r"/filmi-bg-audio/page/(\d+)/?", href)
        if m:
            num = int(m.group(1))
            if num > max_page:
                max_page = num
    return max_page


def clean_genre_name(raw_genre: str) -> str:
    cleaned = re.sub(r"(?i)\bфилми\b", "", raw_genre).strip(" -–/")
    if not cleaned:
        return ""
    lower = cleaned.lower()
    if "бг аудио" in lower or "bg audio" in lower:
        return "БГ Аудио"
    if "екшън" in lower:
        return "Екшън"
    if "комед" in lower:
        return "Комедия"
    if "фантаст" in lower:
        return "Фантастика"
    if "ужас" in lower or "хорър" in lower:
        return "Ужаси"
    if "приключен" in lower:
        return "Приключенски"
    if "драм" in lower:
        return "Драма"
    if "трилър" in lower:
        return "Трилър"
    if "анимац" in lower or "детск" in lower:
        return "Анимация"
    if "семейн" in lower or "семеен" in lower:
        return "Семеен"
    if "романт" in lower or "романс" in lower:
        return "Романс"
    if "криминал" in lower:
        return "Криминален"
    if "мистери" in lower:
        return "Мистерия"
    if "воен" in lower:
        return "Военен"
    if "биограф" in lower:
        return "Биография"
    if "истори" in lower:
        return "История"
    if "документал" in lower:
        return "Документален"
    if "уестърн" in lower:
        return "Уестърн"
    return cleaned.capitalize()


def parse_duration(raw_dur: str) -> int | None:
    if not raw_dur:
        return None
    hours = 0
    mins = 0
    hm = re.search(r"(\d+)\s*ч", raw_dur)
    if hm:
        hours = int(hm.group(1))
    mm = re.search(r"(\d+)\s*мин", raw_dur)
    if mm:
        mins = int(mm.group(1))
    total = hours * 60 + mins
    if total > 0:
        return total
    only_num = re.search(r"(\d+)", raw_dur)
    if only_num:
        return int(only_num.group(1))
    return None


def parse_listing_page(page_num: int) -> list[dict]:
    url = BASE_URL if page_num == 1 else f"{BASE_URL}page/{page_num}/"
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    stubs = []

    for card in soup.select("a.item-poster"):
        href = (card.get("href") or "").strip()
        if not href:
            continue
        if not href.startswith("http"):
            href = f"{SITE_ORIGIN}{href}"

        post_id = None
        id_match = re.search(r"/(\d+)-[^/]+\.html", href)
        if id_match:
            post_id = int(id_match.group(1))

        slug = href.rstrip("/").split("/")[-1].replace(".html", "")

        title_el = card.select_one(".item-poster__title")
        bg_title = title_el.get_text(" ", strip=True) if title_el else ""

        aria = card.get("aria-label") or ""
        orig_title = re.sub(r"^Преглед на\s+", "", aria).strip()

        year = None
        time_el = card.select_one(".item-poster__year time")
        if time_el:
            y_txt = time_el.get("datetime") or time_el.get_text(strip=True)
            if y_txt and y_txt.isdigit():
                year = int(y_txt)

        rating_val = None
        imdb_el = card.select_one(".imdb-rating-label")
        if imdb_el:
            r_match = re.search(r"(\d+(?:\.\d+)?)", imdb_el.get_text(" ", strip=True))
            if r_match:
                val = float(r_match.group(1))
                if val > 0:
                    rating_val = val

        poster_url = ""
        img = card.find("img")
        if img:
            poster_url = img.get("data-src") or img.get("src") or ""
            if poster_url.startswith("data:image"):
                poster_url = img.get("data-src") or ""
            if poster_url.startswith("/"):
                poster_url = f"{SITE_ORIGIN}{poster_url}"

        stubs.append({
            "post_id": post_id,
            "slug": slug,
            "url": href,
            "title": bg_title,
            "original_title": orig_title,
            "year": year,
            "rating": rating_val,
            "poster_url": poster_url,
        })

    return stubs


def extract_players_from_html(html: str) -> list[dict]:
    sources = []
    seen_urls = set()

    for key, label in PLAYER_KEY_LABELS.items():
        pattern = rf'\b{key}\s*:\s*"(https?://[^"]+)"'
        m = re.search(pattern, html)
        if not m:
            continue
        embed_url = m.group(1).strip()
        if not embed_url or embed_url in seen_urls:
            continue
        seen_urls.add(embed_url)
        sources.append({
            "id": f"filmifen-{key}",
            "name": label,
            "group": "bg",
            "direct_embed": True,
            "embed_url": embed_url,
        })

    return sources


def scrape_movie_detail(stub: dict) -> dict | None:
    html = fetch_html(stub["url"])
    if not html:
        return None

    player_sources = extract_players_from_html(html)
    if not player_sources:
        return None

    soup = BeautifulSoup(html, "html.parser")

    bg_title = stub.get("title") or ""
    orig_title = stub.get("original_title") or ""
    year = stub.get("year")

    if not year:
        y_el = soup.select_one(".pmovie-info__year")
        if y_el:
            ym = re.search(r"(19\d{2}|20\d{2})", y_el.get_text(strip=True))
            if ym:
                year = int(ym.group(1))

    dur_el = soup.select_one(".pmovie-info__duration")
    duration_minutes = parse_duration(dur_el.get_text(" ", strip=True)) if dur_el else None

    rating_val = stub.get("rating")
    imdb_span = soup.select_one(".pmovie-info__imdb-rating")
    if imdb_span:
        rm = re.search(r"(\d+(?:\.\d+)?)", imdb_span.get_text(strip=True))
        if rm:
            v = float(rm.group(1))
            if v > 0:
                rating_val = v

    genres = []
    for a_tag in soup.select(".js-genres a"):
        g_name = clean_genre_name(a_tag.get_text(strip=True))
        if g_name and g_name not in genres:
            genres.append(g_name)
    if "БГ Аудио" not in genres:
        genres.append("БГ Аудио")

    countries = []
    for a_tag in soup.select(".js-countries a"):
        c_name = a_tag.get_text(strip=True)
        if c_name and c_name not in countries:
            countries.append(c_name)

    overview = ""
    desc_el = soup.select_one(".js-schema-description, #movie-description")
    if desc_el:
        overview = desc_el.get_text(" ", strip=True)

    poster_url = stub.get("poster_url") or ""
    if not poster_url:
        p_img = soup.select_one(".pmovie__img img")
        if p_img:
            poster_url = p_img.get("data-src") or p_img.get("src") or ""
            if poster_url.startswith("/"):
                poster_url = f"{SITE_ORIGIN}{poster_url}"

    tags = ["bg audio"]
    if orig_title:
        tags.append(orig_title.lower())

    try:
        from scrapers.audio_verifier import classify_audio_type
        final_title = bg_title or orig_title
        is_bg, is_sub, _ = classify_audio_type(final_title, overview, genres, player_sources)
        if is_sub and not is_bg:
            genres = [g for g in genres if g != "БГ Аудио"]
            if "БГ Субтитри" not in genres:
                genres.append("БГ Субтитри")
            for s in player_sources:
                s["group"] = "sub"
    except Exception:
        is_bg, is_sub = True, False

    return {
        "post_id": stub.get("post_id"),
        "tmdb_id": None,
        "slug": stub["slug"],
        "url": stub["url"],
        "title": bg_title or orig_title,
        "original_title": orig_title,
        "year": year,
        "age_rating": None,
        "duration_minutes": duration_minutes,
        "rating": rating_val,
        "countries": countries,
        "genres": genres,
        "tags": tags,
        "overview": overview,
        "poster_url": poster_url,
        "backdrop_url": poster_url,
        "is_bg_audio": is_bg,
        "is_subtitled": is_sub,
        "has_filmi2k_bg": is_bg,
        "player_sources": player_sources,
    }


def save_outputs(items: list[dict]) -> None:
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.FILMIFEN_BG_DATA = ")
        json.dump(items, f, ensure_ascii=False)
        f.write(";\n")


def main() -> None:
    existing_by_url = {}
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    for item in loaded:
                        if item.get("url"):
                            existing_by_url[item["url"]] = item
        except Exception:
            pass

    total_pages = detect_total_pages()
    print(f"Открити страници във Filmifen БГ Аудио: {total_pages}")

    all_stubs = []
    seen_stub_urls = set()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_page = {
            executor.submit(parse_listing_page, p): p
            for p in range(1, total_pages + 1)
        }
        completed_pages = 0
        for future in as_completed(future_to_page):
            completed_pages += 1
            page_stubs = future.result()
            for st in page_stubs:
                if st["url"] not in seen_stub_urls:
                    seen_stub_urls.add(st["url"])
                    all_stubs.append(st)
            if completed_pages % 15 == 0 or completed_pages == total_pages:
                print(f"Листинг страници: {completed_pages}/{total_pages} (намерени {len(all_stubs)} филма)")

    to_scrape = [s for s in all_stubs if s["url"] not in existing_by_url]
    print(f"Общо за детайлно скрейпване: {len(to_scrape)} (кеширани: {len(existing_by_url)})")

    lock = threading.Lock()
    scraped_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_movie_detail, st): st for st in to_scrape}
        for future in as_completed(futures):
            res = future.result()
            with lock:
                scraped_count += 1
                if res:
                    existing_by_url[res["url"]] = res
                if scraped_count % 75 == 0 or scraped_count == len(to_scrape):
                    ordered = [
                        existing_by_url[s["url"]]
                        for s in all_stubs
                        if s["url"] in existing_by_url
                    ]
                    save_outputs(ordered)
                    print(f"Прогрес детайли: {scraped_count}/{len(to_scrape)} (записани {len(ordered)} с активни плеъри)")

    final_ordered = [
        existing_by_url[s["url"]]
        for s in all_stubs
        if s["url"] in existing_by_url
    ]
    save_outputs(final_ordered)
    print(f"Готово! Общо записани БГ Аудио филми от Filmifen: {len(final_ordered)}")


if __name__ == "__main__":
    main()

