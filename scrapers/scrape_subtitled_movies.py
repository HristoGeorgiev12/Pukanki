import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_JSON = os.path.join(DATA_DIR, "subtitled_movies.json")
OUTPUT_JS = os.path.join(DATA_DIR, "subtitled_movies_data.js")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://filmizip.com/filmi/"
}

PLAYER_LABEL_MAP = {
    "vidm": "💬 Vidmoly",
    "fmoon": "💬 Filemoon",
    "stream0": "💬 Embedorigin",
    "abs": "💬 Abstream",
    "video1": "💬 Abstream",
    "video2": "💬 Filemoon",
    "video3": "💬 Vidmoly",
    "video4": "💬 Embedorigin",
    "vidme": "💬 VidMe",
    "embedm": "💬 EmbedM",
    "pstream": "💬 PlayStream",
    "content": "💬 ContentStream"
}


def fetch_url(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception:
            time.sleep(0.5 + attempt * 0.5)
    return ""


def discover_subtitled_movie_links(max_pages: int = 25) -> list[str]:
    links = []
    print(f"[*] Discovering subtitled movies from Filmizip (pages 1 to {max_pages})...")
    for page in range(1, max_pages + 1):
        url = f"https://filmizip.com/filmi/page/{page}/" if page > 1 else "https://filmizip.com/filmi/"
        html = fetch_url(url)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        page_links = []
        for a in soup.select("a"):
            href = a.get("href", "")
            if href.endswith(".html") and "/filmi/" in href:
                if href not in links and href not in page_links:
                    page_links.append(href)
        if not page_links:
            break
        links.extend(page_links)
        print(f"  Filmizip Filmi P.{page}: +{len(page_links)} (total {len(links)})")
    return links


def parse_subtitled_page(movie_url: str) -> dict:
    html = fetch_url(movie_url)
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    match_id = re.search(r"/filmi/(\d+)-", movie_url)
    news_id = match_id.group(1) if match_id else ""

    hash_match = re.search(r"dle_login_hash\s*=\s*['\"]([0-9a-fA-F]+)['\"]", html)
    dle_hash = hash_match.group(1) if hash_match else ""

    h1 = soup.find("h1")
    full_title = h1.get_text(strip=True) if h1 else ""
    orig_span = soup.select_one(".pmovie__original-title")
    original_title = ""
    if orig_span:
        original_title = orig_span.get_text(strip=True).replace("/", "").strip()

    title = full_title
    if "/" in title:
        title = title.split("/")[0].strip()

    is_bg_audio = bool(re.search(r"бг\s*аудио|bg\s*audio", full_title, re.I))

    year = None
    duration = None
    rating = None

    year_link = soup.select_one("a[href*='/year/']")
    if year_link and year_link.get_text(strip=True).isdigit():
        year = int(year_link.get_text(strip=True))

    quality_box = soup.select_one(".pmovie__quality")
    if quality_box:
        q_text = quality_box.get_text(separator=" ", strip=True)
        dur_match = re.search(r"(\d+)\s*мин", q_text)
        if dur_match:
            duration = int(dur_match.group(1))

        imdb_match = re.search(r"IMDb\s*(\d+(?:\.\d+)?)", q_text)
        if imdb_match:
            try:
                rating = float(imdb_match.group(1))
            except ValueError:
                pass

    genres = ["БГ Аудио"] if is_bg_audio else ["БГ Субтитри"]
    countries = []
    actors = []
    directors = []

    for row in soup.select(".pmovie__header-row"):
        label_el = row.select_one(".pmovie__header-label")
        if not label_el:
            continue
        label = label_el.get_text(strip=True).lower()
        row_links = [a.get_text(strip=True) for a in row.select(".pmovie__header-tags a") if a.get_text(strip=True)]

        if "жанр" in label:
            for g in row_links:
                if g not in genres:
                    genres.append(g)
        elif "държава" in label:
            countries.extend(row_links)
        elif "актьори" in label:
            actors.extend(row_links)
        elif "режисьор" in label:
            directors.extend(row_links)

    desc_el = soup.select_one(".page__subcol-desc, .pmovie__desc, .full-text, .pmovie__text")
    overview = desc_el.get_text(strip=True) if desc_el else ""

    poster_el = soup.select_one(".pmovie__poster img")
    poster_url = ""
    if poster_el:
        src = poster_el.get("src") or ""
        if src.startswith("http"):
            poster_url = src
        elif src:
            poster_url = f"https://filmizip.com{src}"

    player_sources = [
        {
            "id": f"fz-sub-{news_id}",
            "name": "💬 FilmiZip (Субтитри)",
            "group": "sub",
            "embed_url": movie_url,
            "direct_embed": False
        }
    ]

    tab_spans = soup.select(".pmovie__player-controls .tabs-block__select span")
    for span in tab_spans:
        data_link = span.get("data-link", "")
        label = span.get_text(strip=True).lower()
        if not data_link:
            continue

        player_page_url = f"https://filmizip.com/player.html?link={data_link}&news_id={news_id}&user_hash={dle_hash}"
        base_p_name = PLAYER_LABEL_MAP.get(label) or PLAYER_LABEL_MAP.get(data_link) or f"💬 {label.upper()}"
        player_sources.append({
            "id": f"fz-{news_id}-{data_link}",
            "name": base_p_name,
            "group": "sub",
            "embed_url": player_page_url,
            "direct_embed": True
        })

    slug = movie_url.split("/")[-1].replace(".html", "")

    return {
        "post_id": f"fz-sub-{news_id}",
        "tmdb_id": None,
        "type": "movie",
        "slug": slug,
        "url": movie_url,
        "title": title,
        "original_title": original_title or title,
        "year": year,
        "age_rating": None,
        "duration_minutes": duration,
        "rating": rating,
        "countries": countries,
        "genres": genres,
        "tags": actors[:5],
        "actors": actors,
        "directors": directors,
        "overview": overview,
        "poster_url": poster_url,
        "backdrop_url": poster_url,
        "is_bg_audio": is_bg_audio,
        "is_subtitled": not is_bg_audio,
        "origins": ["Filmizip Subtitles"],
        "player_sources": player_sources
    }


def scrape_all():
    links = discover_subtitled_movie_links(max_pages=25)
    print(f"[+] Total links discovered: {len(links)}")

    results = []
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = {executor.submit(parse_subtitled_page, u): u for u in links}
        done = 0
        for f in as_completed(futures):
            done += 1
            res = f.result()
            if res and res.get("title"):
                results.append(res)
            if done % 50 == 0 or done == len(futures):
                print(f"[*] Parsed {done}/{len(futures)} movies (valid: {len(results)})")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.SUBTITLED_MOVIES_DATA = ")
        json.dump(results, f, ensure_ascii=False)
        f.write(";\n")

    print(f"[SUCCESS] Scraped {len(results)} subtitled movies into {OUTPUT_JS}!")
    return len(results)


if __name__ == "__main__":
    scrape_all()

