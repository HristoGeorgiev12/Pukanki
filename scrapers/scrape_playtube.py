#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlayTube.tv Scraper
Extracts Bulgarian audio and subtitled full movies and series (>= 15 minutes) from playtube.tv.
Outputs to:
  - data/playtube_bg.json
  - data/playtube_bg_data.js
"""

import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "bg,en-US;q=0.9,en;q=0.8"
}

KEYWORDS = [
    # General queries
    "бг аудио", "филм бг аудио", "целият филм бг аудио", "пълният филм бг аудио",
    "комедия бг аудио", "екшън бг аудио", "анимация бг аудио", "драма бг аудио",
    "ужаси бг аудио", "трилър бг аудио", "фантастика бг аудио", "приключенски бг аудио",
    "семеен бг аудио", "детски бг аудио", "български филм", "бг субтитри", "бг суб",
    "bg audio", "дисни бг аудио", "disney бг аудио", "бг аудио 1080p", "бг аудио 720p",
    "сериал бг аудио", "сезон бг аудио", "епизод бг аудио",
    # Specific years
    "2024 бг аудио", "2023 бг аудио", "2022 бг аудио", "2021 бг аудио", "2020 бг аудио",
    "2019 бг аудио", "2018 бг аудио", "2017 бг аудио", "2016 бг аудио", "2015 бг аудио",
    "2014 бг аудио", "2013 бг аудио", "2012 бг аудио", "2011 бг аудио", "2010 бг аудио",
    "2005 бг аудио", "2000 бг аудио", "1999 бг аудио", "1995 бг аудио", "1990 бг аудио",
    # Genres & Themes
    "зимен", "зимен бг аудио", "уикенд", "един зимен уикенд", "семеен уикенд",
    "коледен", "коледа бг аудио", "нова година бг аудио", "романтичен", "романтика бг аудио",
    "любовен", "любов бг аудио", "холмърк", "hallmark", "криминален бг аудио",
    "мистерия бг аудио", "детектив бг аудио", "военен бг аудио", "исторически бг аудио",
    "фентъзи бг аудио", "вестерн бг аудио", "уестърн бг аудио", "документален бг аудио",
    "игрален филм", "игрален филм бг аудио", "телевизионен филм",
    # Well-known animated & family franchises
    "ледена епоха бг аудио", "шрек бг аудио", "мадагаскар бг аудио", "спайдърмен бг аудио",
    "хари потър бг аудио", "барби бг аудио", "том и джери бг аудио", "скуби ду бг аудио",
    "миньоните бг аудио", "кунг фу панда бг аудио", "коли бг аудио", "рапунцел бг аудио",
    "замръзналото кралство бг аудио", "крал лъв бг аудио", "тарзан бг аудио",
    "астерикс бг аудио", "смърфовете бг аудио", "хотел трансилвания бг аудио",
    "мързелград бг аудио", "адвокатите от бостън бг аудио"
]

CHANNELS = [
    "Gloripeace", "tvnovelas1993", "Blackened", "magnolia", "stupiddreams",
    "Dante93", "senpaiThings", "calinergjt"
]


def parse_duration_seconds(d_str: str) -> int:
    if not d_str:
        return 0
    parts = d_str.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        pass
    return 0


def clean_title_and_extract_metadata(raw_title: str):
    raw = raw_title.strip()
    
    # Extract year
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", raw)
    year = int(year_match.group(1)) if year_match else None

    # Detect BG audio vs subs
    is_bg = bool(re.search(r"бг\s*аудио|bg\s*audio|озвучен|дублаж", raw, re.IGNORECASE))
    is_sub = bool(re.search(r"бг\s*суб|субтитри|bg\s*sub", raw, re.IGNORECASE))
    if not is_bg and not is_sub:
        is_bg = True # default for movies on Bulgarian channels

    # Detect TV / Series
    is_tv = bool(re.search(r"сезон|епизод|еп\.|\b[sс]\d{1,2}\s*[eе]\d{1,2}\b", raw, re.IGNORECASE))
    item_type = "tv" if is_tv else "movie"

    # Clean display title
    cleaned = raw
    # Strip bracketed tags [1080p FULL HD], [Целия филм...]
    cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
    # Strip phrases like целият филм, с бг аудио, озвучен на български, трейлър, 12+, etc.
    cleaned = re.sub(r"(?i)\b(?:целият|целия|пълният|пълен)\s+(?:филм|епизод)\b", "", cleaned)
    cleaned = re.sub(r"(?i)\b(?:с\s+)?бг\s*аудио\b", "", cleaned)
    cleaned = re.sub(r"(?i)\b(?:с\s+)?бг\s*субтитри\b", "", cleaned)
    cleaned = re.sub(r"(?i)\b(?:с\s+)?бг\s*суб\b", "", cleaned)
    cleaned = re.sub(r"(?i)\b(?:озвучен\s+на\s+български(?:\s+език)?)\b", "", cleaned)
    cleaned = re.sub(r"(?i)\b(?:професионален\s+дублаж)\b", "", cleaned)
    cleaned = re.sub(r"(?i)\b(?:на\s+български(?:\s+език)?)\b", "", cleaned)
    cleaned = re.sub(r"\b\d{1,2}\+\b", "", cleaned)
    # Strip year in parentheses (2020) from title if extracted
    cleaned = re.sub(r"\(\s*(?:19\d{2}|20\d{2})\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -—:|*")

    if not cleaned:
        cleaned = raw

    return cleaned, year, is_bg, is_sub, item_type


def fetch_url(url: str, retries: int = 2) -> str:
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12, context=SSL_CTX) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception as e:
            if attempt == retries:
                return ""
            time.sleep(0.5)
    return ""


def parse_video_wrappers(html: str):
    results = []
    if not html:
        return results

    soup = BeautifulSoup(html, "html.parser")
    wrappers = soup.find_all(class_="video-wrapper")

    for w in wrappers:
        a_thumb = w.find("a", href=lambda h: h and "/watch/" in h)
        if not a_thumb:
            continue
        href = a_thumb["href"]

        # Extract title
        title = ""
        img = w.find("img")
        if img and img.get("alt"):
            title = img["alt"].strip()
        if not title:
            h4 = w.find("h4")
            if h4:
                title = h4.get("title") or h4.get_text(strip=True)
        if not title:
            title = a_thumb.get_text(strip=True)

        if not title or len(title) < 3:
            continue

        # Extract duration
        dur_el = w.find(class_=lambda c: c and "duration" in c.lower())
        dur_str = dur_el.get_text(strip=True) if dur_el else ""

        # Extract poster
        poster = ""
        if img:
            poster = img.get("src") or img.get("data-src") or ""

        # Extract uploader channel
        ch_el = w.find("a", href=lambda h: h and "/@" in h)
        uploader = ""
        if ch_el:
            uploader = ch_el["href"].split("/@")[-1].split("/")[0].strip()

        results.append({
            "raw_title": title,
            "url": href,
            "duration_str": dur_str,
            "poster_url": poster,
            "uploader": uploader
        })

    return results


def scrape_keyword(kw: str):
    url = f"https://playtube.tv/search?keyword={urllib.parse.quote(kw)}"
    html = fetch_url(url)
    return parse_video_wrappers(html)


def scrape_channel(ch_name: str):
    url = f"https://playtube.tv/@{ch_name}"
    html = fetch_url(url)
    return parse_video_wrappers(html)


def main():
    print("=" * 60)
    print("Starting PlayTube.tv Scraper")
    print("=" * 60)

    raw_items = []
    seen_urls = set()

    # 1. Scrape Keywords
    print(f"Scraping {len(KEYWORDS)} keywords...")
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(scrape_keyword, kw): kw for kw in KEYWORDS}
        for fut in as_completed(futures):
            kw = futures[fut]
            try:
                items = fut.result()
                count_new = 0
                for it in items:
                    u = it["url"]
                    if u not in seen_urls:
                        seen_urls.add(u)
                        raw_items.append(it)
                        count_new += 1
                print(f"  [KW] '{kw}' -> {len(items)} found ({count_new} new)")
            except Exception as e:
                print(f"  [KW Error] '{kw}': {e}")

    # 2. Scrape Channels (known + discovered)
    all_channels = set(CHANNELS)
    for it in raw_items:
        up = it.get("uploader", "")
        if up and len(up) > 2 and up not in ["login", "register", "terms", "privacy"]:
            all_channels.add(up)

    print(f"\nScraping {len(all_channels)} channels...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scrape_channel, ch): ch for ch in all_channels}
        for fut in as_completed(futures):
            ch = futures[fut]
            try:
                items = fut.result()
                count_new = 0
                for it in items:
                    u = it["url"]
                    if u not in seen_urls:
                        seen_urls.add(u)
                        raw_items.append(it)
                        count_new += 1
                if count_new > 0 or len(items) > 0:
                    print(f"  [CH] '@{ch}' -> {len(items)} found ({count_new} new)")
            except Exception as e:
                print(f"  [CH Error] '@{ch}': {e}")

    print(f"\nTotal unique videos collected: {len(raw_items)}")

    # 3. Filter by duration (>= 15 minutes = 900 seconds) to exclude trailers/clips
    min_duration_sec = 15 * 60
    final_movies = []

    for it in raw_items:
        dur_sec = parse_duration_seconds(it["duration_str"])
        if dur_sec < min_duration_sec:
            continue

        clean_title, year, is_bg, is_sub, item_type = clean_title_and_extract_metadata(it["raw_title"])
        dur_min = round(dur_sec / 60)

        # Video slug/id
        video_id = it["url"].split("_")[-1].replace(".html", "")

        genres = ["БГ Аудио"] if is_bg else ["БГ Субтитри"]
        if item_type == "tv":
            genres.append("Сериал")

        entry = {
            "post_id": f"pt-{video_id}",
            "tmdb_id": None,
            "slug": f"pt-{video_id}",
            "url": it["url"],
            "title": clean_title,
            "original_title": "",
            "year": year,
            "age_rating": None,
            "duration_minutes": dur_min,
            "rating": None,
            "countries": [],
            "genres": genres,
            "tags": [],
            "actors": [],
            "directors": [],
            "overview": f"Гледай {clean_title} онлайн с българско аудио в PlayTube.",
            "poster_url": it["poster_url"],
            "backdrop_url": it["poster_url"],
            "is_bg_audio": is_bg,
            "is_subtitled": is_sub,
            "type": item_type,
            "origins": ["PlayTube"],
            "player_sources": [
                {
                    "id": f"pt-ext-{video_id}",
                    "name": "🌐 PlayTube (Сайт)",
                    "group": "bg" if is_bg else "sub",
                    "embed_url": it["url"],
                    "direct_embed": False
                }
            ]
        }
        final_movies.append(entry)

    print(f"Full-length movies and episodes (>= 15 min): {len(final_movies)}")

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    json_path = os.path.join("data", "playtube_bg.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_movies, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON catalog to: {json_path}")

    js_path = os.path.join("data", "playtube_bg_data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.PLAYTUBE_BG_DATA = ")
        json.dump(final_movies, f, ensure_ascii=False)
        f.write(";\n")
    print(f"Saved JS catalog to: {js_path}")

    print("=" * 60)
    print("Scraper completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
