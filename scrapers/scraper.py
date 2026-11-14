from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

BASE_URL = "https://zenoplay.to"
MOVIES_URL = f"{BASE_URL}/movies/"
TV_SHOWS_URL = f"{BASE_URL}/tv-shows/"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

MOVIES_JSON = os.path.join(DATA_DIR, "movies.json")
MOVIES_JS = os.path.join(DATA_DIR, "movies_data.js")
TV_JSON = os.path.join(DATA_DIR, "tv_shows.json")
TV_JS = os.path.join(DATA_DIR, "tv_shows_data.js")

MAX_WORKERS = 12

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
}

TMDB_PROVIDERS = [
    ("vidsrc", "VidSrc", "https://vidsrc.sh/embed/movie/{tmdb_id}?autoplay=true"),
    ("1src", "1Src", "https://www.1src.org/embed/movie/{tmdb_id}"),
    ("yapgrid", "YapGrid", "https://yapgrid.com/embed/movie/{tmdb_id}"),
    ("embedmaster", "EmbedMaster", "https://embedmaster.link/movie/{tmdb_id}?autoplay=true"),
    ("vidsrc2", "VidSrc2", "https://vidsrc.ru/movie/{tmdb_id}?autoplay=true"),
    ("vidapi", "VidAPI", "https://vaplayer.ru/embed/movie/{tmdb_id}"),
    ("2embed", "2Embed", "https://www.2embed.cc/embed/{tmdb_id}"),
    ("vidlink", "VidLink", "https://vidlink.pro/movie/{tmdb_id}"),
    ("videasy", "Videasy", "https://videasy.xyz/embed/movie/{tmdb_id}"),
    ("vidy", "Vidy", "https://www.vidy.st/movie/{tmdb_id}"),
    ("vidzee", "Vidzee", "https://player.vidzee.wtf/embed/movie/{tmdb_id}"),
    ("cinesrc", "CineSRC", "https://cinesrc.st/embed/movie/{tmdb_id}"),
    ("vidcore", "VidCore", "https://vidcore.org/embed/movie/{tmdb_id}"),
]


def create_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


def extract_bg_url(style_str: str) -> str | None:
    if not style_str:
        return None
    match = re.search(r"--detail-bg:\s*url\(['\"]?(.*?)['\"]?\)", style_str)
    if match:
        return match.group(1)
    return None


def build_movie_player_sources(tmdb_id: str | int | None, movie_url: str) -> list[dict]:
    sources = []
    if tmdb_id:
        for provider_id, name, template in TMDB_PROVIDERS:
            sources.append({
                "id": provider_id,
                "name": name,
                "group": "en",
                "embed_url": template.format(tmdb_id=tmdb_id),
            })

    sources.append({
        "id": "custom-1",
        "name": "BG Player",
        "group": "bg",
        "embed_url": f"{movie_url}#player",
    })
    return sources


def parse_tv_seasons(soup: BeautifulSoup) -> list[dict]:
    seasons = []
    for block in soup.select("section.season-block"):
        episodes = []
        season_num = None

        for ep_card in block.select("a.episode-card"):
            ep_url = ep_card.get("href")
            s_raw = ep_card.get("data-season-number") or ""
            e_raw = ep_card.get("data-episode-number") or ""
            s_num = int(s_raw) if s_raw.isdigit() else 1
            e_num = int(e_raw) if e_raw.isdigit() else (len(episodes) + 1)

            if season_num is None:
                season_num = s_num

            img_el = ep_card.select_one("img")
            episodes.append({
                "episode": e_num,
                "url": ep_url,
                "thumb": img_el.get("src") if img_el else None,
            })

        if episodes:
            seasons.append({
                "season": season_num or (len(seasons) + 1),
                "episodes": episodes,
            })

    return seasons


def scrape_item_details(session: requests.Session, card_info: dict, media_type: str = "movie") -> dict | None:
    item_url = card_info["url"]
    try:
        resp = session.get(item_url, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[!] Грешка при зареждане на {item_url}: {exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    article_el = soup.select_one("article.detail-page")
    hero_el = soup.select_one("section.detail-hero")
    info_el = soup.select_one("div.detail-info")
    player_el = soup.select_one("section[data-player-panel]")

    title_el = info_el.select_one("h1") if info_el else None
    year_el = info_el.select_one(".detail-meta .detail-year-link") if info_el else None
    rating_el = info_el.select_one(".detail-meta .rating-pill") if info_el else None

    duration_minutes = None
    seasons_count = None
    if info_el:
        for span in info_el.select(".detail-meta span"):
            text = span.get_text(strip=True)
            if "min" in text.lower():
                num_match = re.search(r"(\d+)", text)
                if num_match:
                    duration_minutes = int(num_match.group(1))
            if "season" in text.lower():
                num_match = re.search(r"(\d+)", text)
                if num_match:
                    seasons_count = int(num_match.group(1))

    rating_value = None
    if rating_el:
        rating_match = re.search(r"(\d+(?:\.\d+)?)", rating_el.get_text(strip=True))
        if rating_match:
            rating_value = float(rating_match.group(1))

    countries = []
    country_el = info_el.select_one(".detail-country") if info_el else None
    if country_el:
        raw_country = re.sub(r"^Country:\s*", "", country_el.get_text(strip=True), flags=re.IGNORECASE)
        countries = [c.strip() for c in raw_country.split(",") if c.strip()]

    overview_el = info_el.select_one(".detail-overview") if info_el else None
    overview = overview_el.get_text(strip=True) if overview_el else None

    poster_el = soup.select_one("img.detail-poster")
    poster_url = poster_el.get("src") if poster_el else card_info.get("poster_url")
    backdrop_url = extract_bg_url(hero_el.get("style", "")) if hero_el else None

    genres = [g.get_text(strip=True) for g in soup.select(".genre-chip-row a.chip") if g.get_text(strip=True)]
    is_bg_audio = any(g.lower() == "бг аудио" for g in genres)
    tags = [t.get_text(strip=True).lstrip("#") for t in soup.select(".tag-chip-row a.chip") if t.get_text(strip=True)]

    post_id = player_el.get("data-post-id") if player_el else None
    tmdb_id = (
        (player_el.get("data-tmdb-id") if player_el else None)
        or (article_el.get("data-tmdb-id") if article_el else None)
    )
    slug = card_info["slug"]

    year_text = year_el.get_text(strip=True) if year_el else (card_info.get("year") or "")
    parsed_year = int(year_text) if year_text.isdigit() else None

    item_data = {
        "type": media_type,
        "post_id": int(post_id) if post_id and post_id.isdigit() else post_id,
        "tmdb_id": int(tmdb_id) if tmdb_id and str(tmdb_id).isdigit() else tmdb_id,
        "slug": slug,
        "url": item_url,
        "title": title_el.get_text(strip=True) if title_el else card_info.get("title"),
        "year": parsed_year,
        "age_rating": card_info.get("age_rating"),
        "duration_minutes": duration_minutes,
        "rating": rating_value,
        "is_bg_audio": is_bg_audio,
        "countries": countries,
        "genres": genres,
        "tags": tags,
        "overview": overview,
        "poster_url": poster_url,
        "backdrop_url": backdrop_url,
    }

    if media_type == "tv":
        seasons = parse_tv_seasons(soup)
        item_data["seasons_count"] = seasons_count or len(seasons)
        item_data["seasons"] = seasons
        return item_data

    item_data["player_sources"] = build_movie_player_sources(tmdb_id, item_url)
    return item_data


def load_existing_items(file_path: str) -> dict[str, dict]:
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            return {}
        return {item["slug"]: item for item in items if isinstance(item, dict) and item.get("slug")}
    except Exception:
        return {}


def save_snapshot(items: list[dict], json_path: str, js_path: str, window_var: str) -> None:
    tmp_json = f"{json_path}.tmp"
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp_json, json_path)

    tmp_js = f"{js_path}.tmp"
    with open(tmp_js, "w", encoding="utf-8") as f:
        f.write(f"window.{window_var} = {json.dumps(items, ensure_ascii=False)};\n")
    os.replace(tmp_js, js_path)


def get_catalog_page_url(base_catalog_url: str, page: int) -> str:
    if page <= 1:
        return base_catalog_url
    return f"{base_catalog_url}page/{page}/"


def detect_total_pages(soup: BeautifulSoup, path_segment: str) -> int:
    max_page = 1
    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = re.search(rf"/{path_segment}/page/(\d+)/", href)
        if match:
            page_num = int(match.group(1))
            if page_num > max_page:
                max_page = page_num
    return max_page


def parse_catalog_cards(soup: BeautifulSoup) -> list[dict]:
    cards = soup.select(".catalog-grid a.media-card")
    parsed = []
    for card in cards:
        url = card.get("href")
        if not url:
            continue
        slug = url.rstrip("/").split("/")[-1]
        title_el = card.select_one(".media-title")
        year_el = card.select_one(".media-year")
        age_el = card.select_one(".content-label")
        img_el = card.select_one("img")

        parsed.append({
            "url": url,
            "slug": slug,
            "title": title_el.get_text(strip=True) if title_el else None,
            "year": year_el.get_text(strip=True) if year_el else None,
            "age_rating": age_el.get_text(strip=True) if age_el else None,
            "poster_url": img_el.get("src") if img_el else None,
        })
    return parsed


def scrape_catalog(
    base_catalog_url: str,
    path_segment: str,
    media_type: str,
    json_path: str,
    js_path: str,
    window_var: str,
    limit: int | None = None,
) -> list[dict]:
    session = create_session()
    existing_by_slug = load_existing_items(json_path)
    all_by_slug = dict(existing_by_slug)
    ordered_slugs = list(existing_by_slug.keys())

    page = 1
    total_pages = 1

    while True:
        if limit and len(ordered_slugs) >= limit:
            break

        page_url = get_catalog_page_url(base_catalog_url, page)
        try:
            resp = session.get(page_url, timeout=15)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
        except Exception as exc:
            print(f"[!] Грешка при страница {page} ({page_url}): {exc}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        if page == 1:
            total_pages = detect_total_pages(soup, path_segment)
            print(f"[*] [{media_type.upper()}] Открити общо {total_pages} страници (~{total_pages * 24} заглавия).")

        cards = parse_catalog_cards(soup)
        if not cards:
            break

        to_fetch = []
        for card in cards:
            slug = card["slug"]
            if slug not in ordered_slugs:
                ordered_slugs.append(slug)
            if slug not in all_by_slug:
                to_fetch.append(card)
            if limit and len(ordered_slugs) >= limit:
                break

        if not to_fetch:
            print(f"[{media_type.upper()} Страница {page}/{total_pages}] Всички {len(cards)} заглавия са вече в кеша.")
            page += 1
            if page > total_pages:
                break
            continue

        print(f"[{media_type.upper()} Страница {page}/{total_pages}] Извличане на {len(to_fetch)} нови заглавия...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_card = {
                executor.submit(scrape_item_details, session, card, media_type): card
                for card in to_fetch
            }
            for future in as_completed(future_to_card):
                item_data = future.result()
                if item_data:
                    all_by_slug[item_data["slug"]] = item_data

        current_list = [all_by_slug[s] for s in ordered_slugs if s in all_by_slug]
        save_snapshot(current_list, json_path, js_path, window_var)
        print(f"    -> Запазени общо {len(current_list)} заглавия в {json_path}")

        page += 1
        if page > total_pages:
            break
        time.sleep(0.15)

    return [all_by_slug[s] for s in ordered_slugs if s in all_by_slug]


def main():
    start_time = time.time()
    tv_shows = scrape_catalog(
        base_catalog_url=TV_SHOWS_URL,
        path_segment="tv-shows",
        media_type="tv",
        json_path=TV_JSON,
        js_path=TV_JS,
        window_var="TV_SHOWS_DATA",
        limit=None,
    )
    elapsed = time.time() - start_time
    print(f"\n[+] Готово! Извлечени общо {len(tv_shows)} сериала за {elapsed:.1f} сек.")


if __name__ == "__main__":
    main()
