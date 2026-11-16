import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import threading
import time
import urllib.parse
from bs4 import BeautifulSoup
import requests

BASE_URL = "https://www.filmi2k.com/tag/filmi-bg-audio/"
SITE_ORIGIN = "https://www.filmi2k.com"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_JSON = os.path.join(DATA_DIR, "filmi2k_bg.json")
OUTPUT_JS = os.path.join(DATA_DIR, "filmi2k_bg_data.js")
MAX_WORKERS = 14

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
}

PROVIDER_NAMES = {
    "luluvid": "🇧🇬 LuluVid",
    "lulustream": "🇧🇬 LuluStream",
    "uqload": "🇧🇬 Uqload",
    "streamtape": "🇧🇬 Streamtape",
    "myvidplay": "🇧🇬 MyVidPlay",
    "dood": "🇧🇬 DoodStream",
    "filemoon": "🇧🇬 Filemoon",
    "voe": "🇧🇬 VOE",
    "ok.ru": "🇧🇬 OK.ru",
    "vk.com": "🇧🇬 VK Video",
    "vkvideo": "🇧🇬 VK Video",
    "mixdrop": "🇧🇬 MixDrop",
    "netu": "🇧🇬 Netu",
    "hqq": "🇧🇬 Netu",
    "vidguard": "🇧🇬 VidGuard",
    "vidoza": "🇧🇬 Vidoza",
    "upstream": "🇧🇬 UpStream",
    "highload": "🇧🇬 HighLoad",
    "supervideo": "🇧🇬 SuperVideo",
    "dropload": "🇧🇬 DropLoad",
    "vtube": "🇧🇬 VTube",
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


def decode_rtp(rtp_raw: str) -> str:
    try:
        clean = urllib.parse.unquote(rtp_raw).strip()
        if clean.startswith("/?rtp="):
            clean = clean[6:]
        rev1 = clean[::-1]
        pad1 = rev1 + ("=" * ((4 - len(rev1) % 4) % 4))
        step1 = base64.b64decode(pad1).decode("utf-8", "ignore").strip()
        pad2 = step1 + ("=" * ((4 - len(step1) % 4) % 4))
        step2 = base64.b64decode(pad2).decode("utf-8", "ignore")
        decoded = step2[::-1].strip()
        if decoded.startswith("http"):
            return decoded
    except Exception:
        return ""
    return ""


def resolve_provider_label(embed_url: str, index: int) -> str:
    try:
        host = urllib.parse.urlparse(embed_url).hostname or ""
        host_lower = host.lower()
        for key, label in PROVIDER_NAMES.items():
            if key in host_lower:
                return label
        short_host = host_lower.replace("www.", "").split(".")[0].capitalize()
        if short_host:
            return f"🇧🇬 {short_host}"
    except Exception:
        pass
    return f"🇧🇬 Сървър {index + 1}"


def clean_genre_name(raw_genre: str) -> str:
    cleaned = re.sub(r"(?i)\bфилми\b", "", raw_genre).strip(" -–/")
    if not cleaned:
        return ""
    lower = cleaned.lower()
    if "bg audio" in lower or "бг аудио" in lower:
        return "БГ Аудио"
    if "екшън" in lower:
        return "Екшън"
    if "комедия" in lower:
        return "Комедия"
    if "фантастика" in lower:
        return "Фантастика"
    if "ужаси" in lower:
        return "Ужаси"
    if "приключенски" in lower:
        return "Приключенски"
    if "драма" in lower:
        return "Драма"
    if "трилър" in lower:
        return "Трилър"
    if "анимация" in lower:
        return "Анимация"
    if "семейни" in lower or "семеен" in lower:
        return "Семеен"
    if "романтични" in lower or "романс" in lower:
        return "Романс"
    if "криминални" in lower or "криминален" in lower:
        return "Криминален"
    if "мистерия" in lower:
        return "Мистерия"
    if "военни" in lower or "военен" in lower:
        return "Военен"
    if "биографични" in lower or "биография" in lower:
        return "Биография"
    if "исторически" in lower or "история" in lower:
        return "История"
    if "документални" in lower or "документален" in lower:
        return "Документален"
    if "уестърн" in lower:
        return "Уестърн"
    return cleaned.capitalize()


def parse_heading_title(raw_heading: str) -> tuple[str, str, int | None]:
    cleaned = re.sub(r"(?i)\b(?:bg\s*audio|бг\s*аудио)\b", "", raw_heading).strip()
    year = None
    year_match = re.search(r"\((19\d{2}|20\d{2})\)", cleaned)
    if year_match:
        year = int(year_match.group(1))
        cleaned = cleaned[:year_match.start()] + cleaned[year_match.end():]
    cleaned = cleaned.strip(" -–/()")
    if "/" in cleaned:
        parts = [p.strip() for p in cleaned.split("/") if p.strip()]
        if len(parts) >= 2:
            return parts[-1], parts[0], year
    return cleaned, "", year


def detect_total_pages() -> int:
    html = fetch_html(BASE_URL)
    if not html:
        return 94
    soup = BeautifulSoup(html, "html.parser")
    max_page = 1
    for a_tag in soup.select(".pagination a, .page-numbers, .wp-pagenavi a"):
        href = a_tag.get("href") or ""
        m = re.search(r"/page/(\d+)/?", href)
        if m:
            num = int(m.group(1))
            if num > max_page:
                max_page = num
    return max_page


def parse_listing_page(page_num: int) -> list[dict]:
    url = BASE_URL if page_num == 1 else f"{BASE_URL}page/{page_num}/"
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    stubs = []
    for art in soup.select("article"):
        a_tag = art.find("a", href=True)
        if not a_tag:
            continue
        movie_url = a_tag["href"].strip()
        if not movie_url.startswith("http"):
            movie_url = f"{SITE_ORIGIN}{movie_url}"

        post_id = None
        raw_pid = art.get("data-post-id")
        if raw_pid and str(raw_pid).isdigit():
            post_id = int(raw_pid)

        thumb = art.get("data-main-thumb") or ""
        if not thumb:
            img = art.find("img")
            if img:
                thumb = img.get("src") or img.get("data-src") or ""
        if thumb and thumb.startswith("/"):
            thumb = f"{SITE_ORIGIN}{thumb}"

        rating_val = None
        rating_span = art.select_one(".rating-bar span")
        if rating_span:
            pct_match = re.search(r"(\d+)", rating_span.get_text(strip=True))
            if pct_match:
                pct = int(pct_match.group(1))
                if 0 < pct <= 100:
                    rating_val = round(pct / 10.0, 1)

        raw_title = a_tag.get("title") or a_tag.get_text(" ", strip=True)
        slug = movie_url.rstrip("/").split("/")[-1]
        stubs.append({
            "post_id": post_id,
            "slug": slug,
            "url": movie_url,
            "raw_title": raw_title,
            "poster_url": thumb,
            "rating": rating_val,
        })
    return stubs


def scrape_movie_detail(stub: dict, html: str | None = None) -> dict | None:
    if html is None:
        html = fetch_html(stub["url"])
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    heading_text = h1.get_text(" ", strip=True) if h1 else stub.get("raw_title", "")
    bg_title, orig_title, year = parse_heading_title(heading_text)

    poster_url = stub.get("poster_url") or ""
    if not poster_url:
        og_img = soup.find("meta", {"property": "og:image"})
        if og_img and og_img.get("content"):
            poster_url = og_img["content"].strip()
            if poster_url.startswith("/"):
                poster_url = f"{SITE_ORIGIN}{poster_url}"

    overview_parts = []
    duration_minutes = None
    countries = []

    for p_tag in soup.select("#video-about p, .entry-content p, .video-description p"):
        txt = p_tag.get_text(" ", strip=True)
        if not txt:
            continue
        if "Режисьор:" in txt or "Времетраене:" in txt or "Година:" in txt:
            if not year:
                ym = re.search(r"Година:\s*(19\d{2}|20\d{2})", txt)
                if ym:
                    year = int(ym.group(1))
            dm = re.search(r"Времетраене:\s*(\d+)", txt)
            if dm:
                duration_minutes = int(dm.group(1))
            cm = re.search(r"Държава:\s*([^,]+(?:,\s*[^,]+)*?)(?:,\s*Година:|,\s*Времетраене:|$)", txt)
            if cm:
                countries = [c.strip() for c in cm.group(1).split(",") if c.strip()]
            continue
        if len(txt) > 25:
            overview_parts.append(txt)

    overview = "\n\n".join(overview_parts).strip()
    if not overview:
        og_desc = soup.find("meta", {"property": "og:description"})
        if og_desc and og_desc.get("content"):
            overview = og_desc["content"].strip()

    genres = []
    for a_tag in soup.select('a[rel*="category"], .cat-links a, .entry-categories a'):
        g_name = clean_genre_name(a_tag.get_text(strip=True))
        if g_name and g_name not in genres:
            genres.append(g_name)
    if "БГ Аудио" not in genres:
        genres.append("БГ Аудио")

    rtp_tokens = re.findall(r"/\?rtp=([A-Za-z0-9%+/=_-]+)", html)
    seen_urls = set()
    player_sources = []

    for idx, token in enumerate(rtp_tokens):
        decoded_url = decode_rtp(token)
        if not decoded_url or decoded_url in seen_urls:
            continue
        seen_urls.add(decoded_url)
        label = resolve_provider_label(decoded_url, len(player_sources))
        player_sources.append({
            "id": f"filmi2k-{len(player_sources) + 1}",
            "name": label,
            "group": "bg",
            "direct_embed": True,
            "embed_url": decoded_url,
        })

    if not player_sources:
        return None

    try:
        from scrapers.audio_verifier import classify_audio_type
        final_title = bg_title or heading_text
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
        "title": bg_title or heading_text,
        "original_title": orig_title,
        "year": year,
        "age_rating": None,
        "duration_minutes": duration_minutes,
        "rating": stub.get("rating"),
        "countries": countries,
        "genres": genres,
        "tags": ["bg audio", orig_title.lower()] if orig_title else ["bg audio"],
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
        f.write("window.FILMI2K_BG_DATA = ")
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
    print(f"Открити страници във Filmi2k БГ Аудио: {total_pages}")

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
            if completed_pages % 10 == 0 or completed_pages == total_pages:
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
                if scraped_count % 50 == 0 or scraped_count == len(to_scrape):
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
    print(f"Готово! Общо записани БГ Аудио филми от Filmi2k: {len(final_ordered)}")


if __name__ == "__main__":
    main()

