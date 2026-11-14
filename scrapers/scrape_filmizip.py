import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://filmizip.com/bgaudio/"
}

PLAYER_LABEL_MAP = {
    "vidm": "🇧🇬 Vidmoly",
    "fmoon": "🇧🇬 Filemoon",
    "stream0": "🇧🇬 Embedorigin",
    "abs": "🇧🇬 Abstream",
    "video1": "🇧🇬 Abstream",
    "video2": "🇧🇬 Filemoon",
    "video3": "🇧🇬 Vidmoly",
    "video4": "🇧🇬 Embedorigin",
    "vidme": "🇧🇬 VidMe",
    "embedm": "🇧🇬 EmbedM"
}


def fetch_url(url: str, retries: int = 3) -> str:
    headers = dict(HEADERS)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception:
            time.sleep(0.5 + attempt * 0.5)
    return ""


def get_all_bgaudio_links(base_url: str = "https://filmizip.com/bgaudio/") -> list[str]:
    all_links = []
    page = 1
    print("[*] Discovering all BG Audio movie & series links...")

    while True:
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        html = fetch_url(url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        page_links = []
        for a in soup.select("a"):
            href = a.get("href", "")
            if href.endswith(".html") and (href.startswith("https://filmizip.com/filmi/") or href.startswith("https://filmizip.com/seriali/")):
                if href not in all_links and href not in page_links:
                    page_links.append(href)

        if not page_links:
            break

        all_links.extend(page_links)
        print(f"  Page {page}: +{len(page_links)} links (total: {len(all_links)})")
        page += 1

    print(f"[+] Total links found: {len(all_links)}")
    return all_links


def parse_page(movie_url: str) -> dict:
    html = fetch_url(movie_url)
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    match_id = re.search(r"/(?:filmi|seriali)/(\d+)-", movie_url)
    news_id = match_id.group(1) if match_id else ""
    is_tv = "/seriali/" in movie_url
    item_type = "tv" if is_tv else "movie"

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

    season_num = None
    if is_tv:
        season_match = re.search(r"Сезон\s*(\d+)", full_title, flags=re.I)
        if season_match:
            season_num = int(season_match.group(1))
        title = re.sub(r"\s*Сезон\s*\d+.*$", "", title, flags=re.I).strip()
        original_title = re.sub(r"\s*(?:Сезон|Season)\s*\d+.*$", "", original_title, flags=re.I).strip()

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

    genres = ["БГ Аудио"]
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

    source_suffix = f" (С.{season_num})" if season_num else ""
    player_sources = [
        {
            "id": f"fz-out-{news_id}",
            "name": f"🇧🇬 FilmiZip{source_suffix}",
            "group": "bg",
            "embed_url": movie_url,
            "direct_embed": False,
            "season": season_num
        }
    ]

    tab_spans = soup.select(".pmovie__player-controls .tabs-block__select span")
    for span in tab_spans:
        data_link = span.get("data-link", "")
        label = span.get_text(strip=True).lower()
        if not data_link:
            continue

        player_page_url = f"https://filmizip.com/player.html?link={data_link}&news_id={news_id}&user_hash={dle_hash}"
        base_p_name = PLAYER_LABEL_MAP.get(label) or PLAYER_LABEL_MAP.get(data_link) or f"🇧🇬 {label.upper()}"
        p_name = f"{base_p_name}{source_suffix}"
        player_sources.append({
            "id": f"filmizip-{data_link}-{news_id}",
            "name": p_name,
            "group": "bg",
            "embed_url": player_page_url,
            "direct_embed": False,
            "season": season_num
        })

    slug = movie_url.split("/")[-1].replace(".html", "")

    return {
        "post_id": f"fz-{news_id}",
        "tmdb_id": None,
        "type": item_type,
        "season": season_num,
        "slug": slug,
        "url": movie_url,
        "title": title,
        "original_title": original_title,
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
        "is_bg_audio": True,
        "origins": ["Filmizip"],
        "player_sources": player_sources
    }


def main():
    start_time = time.time()
    out_json = "data/filmizip_bg.json"
    out_js = "data/filmizip_bg_data.js"
    os.makedirs("data", exist_ok=True)

    existing_by_url = {}
    if os.path.exists(out_json):
        try:
            with open(out_json, "r", encoding="utf-8") as f:
                cached = json.load(f)
                for item in cached:
                    if item.get("url"):
                        existing_by_url[item["url"]] = item
            print(f"[*] Found {len(existing_by_url)} previously scraped items in cache.")
        except Exception:
            pass

    links = get_all_bgaudio_links()
    total = len(links)
    to_scrape = [url for url in links if url not in existing_by_url]
    print(f"\n[*] Total links in category: {total}. Already cached: {len(existing_by_url)}. To fetch: {len(to_scrape)}")

    scraped_new = []
    failed_links = []

    if to_scrape:
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_url = {executor.submit(parse_page, url): url for url in to_scrape}
            completed = 0
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    data = future.result()
                    if data and data.get("title"):
                        scraped_new.append(data)
                        existing_by_url[url] = data
                    else:
                        failed_links.append(url)
                except Exception:
                    failed_links.append(url)
                completed += 1
                if completed % 10 == 0 or completed == len(to_scrape):
                    elapsed = time.time() - start_time
                    print(f"  [{completed}/{len(to_scrape)}] Fetched ({elapsed:.1f}s) - {len(scraped_new)} OK")

    if failed_links:
        print(f"\n[*] Retrying {len(failed_links)} failed links...")
        for url in failed_links:
            time.sleep(0.3)
            data = parse_page(url)
            if data and data.get("title"):
                scraped_new.append(data)
                existing_by_url[url] = data

    all_items = []
    for url in links:
        if url in existing_by_url:
            all_items.append(existing_by_url[url])

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    with open(out_js, "w", encoding="utf-8") as f:
        f.write(f"window.FILMIZIP_BG_DATA = {json.dumps(all_items, ensure_ascii=False, indent=2)};\n")

    elapsed = time.time() - start_time
    print(f"\n[+] SUCCESS! Total {len(all_items)} titles (movies & series) saved to {out_json} and {out_js} in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
