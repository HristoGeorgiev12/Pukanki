import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
sys.path.append(os.path.join(BASE_DIR, "scrapers"))

import scrape_filmi2k
import scrape_subtitled_movies


def fetch_soup(url: str, retries: int = 3) -> BeautifulSoup | None:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", "ignore")
                return BeautifulSoup(html, "html.parser")
        except Exception:
            time.sleep(0.5 + attempt * 0.5)
    return None


def scrape_filmi2k_top250(max_pages: int = 8) -> list[dict]:
    print(f"\n[1/2] === SCRAPING FILMI2K TOP 250 (PAGES 1 TO {max_pages}) ===")
    base_tag_url = "https://www.filmi2k.com/tag/top-250-imdb-filmi/"
    all_stubs = []

    for page in range(1, max_pages + 1):
        page_url = base_tag_url if page == 1 else f"{base_tag_url}page/{page}/"
        soup = fetch_soup(page_url)
        if not soup:
            break
        articles = soup.select("article")
        if not articles:
            break

        count = 0
        for art in articles:
            a_tag = art.find("a", href=True)
            if not a_tag:
                continue
            movie_url = a_tag["href"].strip()
            if not movie_url.startswith("http"):
                movie_url = f"https://www.filmi2k.com{movie_url}"

            raw_pid = art.get("data-post-id")
            post_id = int(raw_pid) if raw_pid and str(raw_pid).isdigit() else None
            thumb = art.get("data-main-thumb") or ""
            if not thumb:
                img = art.find("img")
                if img:
                    thumb = img.get("src") or img.get("data-src") or ""
            if thumb and thumb.startswith("/"):
                thumb = f"https://www.filmi2k.com{thumb}"

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
            all_stubs.append({
                "post_id": post_id,
                "slug": slug,
                "url": movie_url,
                "raw_title": raw_title,
                "poster_url": thumb,
                "rating": rating_val,
            })
            count += 1
        print(f"  Top 250 Page {page}: +{count} movies")

    print(f"[+] Total Top 250 stubs found: {len(all_stubs)}")
    scraped_items = []

    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = {executor.submit(scrape_filmi2k.scrape_movie_detail, s): s for s in all_stubs}
        done = 0
        for f in as_completed(futures):
            done += 1
            item = f.result()
            if item and item.get("title"):
                scraped_items.append(item)
            if done % 20 == 0 or done == len(futures):
                print(f"  Parsed {done}/{len(futures)} Top 250 movies (valid: {len(scraped_items)})")

    return scraped_items


def scrape_filmizip_pages(start_page: int = 26, end_page: int = 75) -> list[dict]:
    print(f"\n[2/2] === SCRAPING FILMIZIP ARCHIVE (PAGES {start_page} TO {end_page}) ===")
    all_links = []

    for page in range(start_page, end_page + 1):
        page_url = f"https://filmizip.com/filmi/page/{page}/"
        soup = fetch_soup(page_url)
        if not soup:
            continue
        page_links = []
        for a in soup.select("a"):
            href = a.get("href", "")
            if href.endswith(".html") and "/filmi/" in href:
                if href not in all_links and href not in page_links:
                    page_links.append(href)
        all_links.extend(page_links)
        if page % 10 == 0 or page == end_page:
            print(f"  Filmizip Page {page}: total links collected: {len(all_links)}")

    print(f"[+] Total Filmizip archive links: {len(all_links)}")
    scraped_items = []

    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = {executor.submit(scrape_subtitled_movies.parse_subtitled_page, u): u for u in all_links}
        done = 0
        for f in as_completed(futures):
            done += 1
            item = f.result()
            if item and item.get("title"):
                scraped_items.append(item)
            if done % 50 == 0 or done == len(futures):
                print(f"  Parsed {done}/{len(futures)} archive movies (valid: {len(scraped_items)})")

    return scraped_items


def merge_and_save(top250_items: list[dict], archive_items: list[dict]):
    print("\n[3/3] === MERGING DATA FILES ===")

    # 1. Filmi2k
    f2k_json_path = os.path.join(DATA_DIR, "filmi2k_bg.json")
    f2k_js_path = os.path.join(DATA_DIR, "filmi2k_bg_data.js")
    with open(f2k_json_path, "r", encoding="utf-8") as f:
        existing_f2k = json.load(f)

    existing_slugs = {x.get("slug") for x in existing_f2k}
    added_f2k = 0
    for item in top250_items:
        if item.get("slug") not in existing_slugs:
            existing_f2k.append(item)
            existing_slugs.add(item.get("slug"))
            added_f2k += 1

    with open(f2k_json_path, "w", encoding="utf-8") as f:
        json.dump(existing_f2k, f, ensure_ascii=False, indent=2)
    with open(f2k_js_path, "w", encoding="utf-8") as f:
        f.write("window.FILMI2K_BG_DATA = ")
        json.dump(existing_f2k, f, ensure_ascii=False)
        f.write(";\n")
    print(f"[+] Added {added_f2k} new Top 250 items to Filmi2k (Total: {len(existing_f2k)})")

    # 2. Subtitled Movies
    sub_json_path = os.path.join(DATA_DIR, "subtitled_movies.json")
    sub_js_path = os.path.join(DATA_DIR, "subtitled_movies_data.js")
    with open(sub_json_path, "r", encoding="utf-8") as f:
        existing_sub = json.load(f)

    existing_sub_slugs = {x.get("slug") for x in existing_sub}
    added_sub = 0
    for item in archive_items:
        if item.get("slug") not in existing_sub_slugs:
            existing_sub.append(item)
            existing_sub_slugs.add(item.get("slug"))
            added_sub += 1

    with open(sub_json_path, "w", encoding="utf-8") as f:
        json.dump(existing_sub, f, ensure_ascii=False, indent=2)
    with open(sub_js_path, "w", encoding="utf-8") as f:
        f.write("window.SUBTITLED_MOVIES_DATA = ")
        json.dump(existing_sub, f, ensure_ascii=False)
        f.write(";\n")
    print(f"[+] Added {added_sub} new archive items to Subtitled catalog (Total: {len(existing_sub)})")


if __name__ == "__main__":
    t250 = scrape_filmi2k_top250(max_pages=8)
    arch = scrape_filmizip_pages(start_page=26, end_page=75)
    merge_and_save(t250, arch)
    print("\n[SUCCESS] Stage 1 scraping and merging completed!")

