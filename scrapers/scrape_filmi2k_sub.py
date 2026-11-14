from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import threading
from bs4 import BeautifulSoup

import scrape_filmi2k as base

SITEMAP_INDEX = f"{base.SITE_ORIGIN}/sitemap_index.xml"
OUTPUT_JSON = os.path.join(base.DATA_DIR, "filmi2k_sub.json")
OUTPUT_JS = os.path.join(base.DATA_DIR, "filmi2k_sub_data.js")
BG_JSON = os.path.join(base.DATA_DIR, "filmi2k_bg.json")
MAX_WORKERS = 14
SAVE_EVERY = 100


def load_json_list(path: str) -> list:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return data


def collect_sitemap_urls() -> list[str]:
    index_xml = base.fetch_html(SITEMAP_INDEX)
    sitemaps = [u for u in re.findall(r"<loc>([^<]+)</loc>", index_xml) if "post-sitemap" in u]
    print(f"Открити post sitemap-и: {len(sitemaps)}")
    urls = []
    seen = set()
    for sm in sitemaps:
        xml = base.fetch_html(sm)
        for loc in re.findall(r"<loc>([^<]+)</loc>", xml):
            loc = loc.strip()
            if loc.rstrip("/") == base.SITE_ORIGIN:
                continue
            if "/wp-content/" in loc:
                continue
            if loc in seen:
                continue
            seen.add(loc)
            urls.append(loc)
    return urls


def parse_page_rating(soup: BeautifulSoup) -> float | None:
    span = soup.select_one(".rating-bar span")
    if not span:
        return None
    m = re.search(r"(\d+)", span.get_text(strip=True))
    if not m:
        return None
    pct = int(m.group(1))
    if pct <= 0 or pct > 100:
        return None
    return round(pct / 10.0, 1)


def scrape_sub_detail(url: str) -> dict | None:
    html = base.fetch_html(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    heading = h1.get_text(" ", strip=True) if h1 else ""
    is_bg = bool(re.search(r"(?i)\b(?:bg\s*audio|бг\s*аудио)\b", heading))

    slug = url.rstrip("/").split("/")[-1]
    article = soup.select_one("article[data-post-id]")
    post_id = None
    if article and str(article.get("data-post-id", "")).isdigit():
        post_id = int(article["data-post-id"])
    stub = {
        "post_id": post_id,
        "slug": slug,
        "url": url,
        "raw_title": heading,
        "poster_url": "",
        "rating": parse_page_rating(soup),
    }
    item = base.scrape_movie_detail(stub, html)
    if not item:
        return None
    if is_bg:
        return item

    genres = [g for g in item.get("genres", []) if g != "БГ Аудио"]
    if "БГ Субтитри" not in genres:
        genres.append("БГ Субтитри")
    item["genres"] = genres
    orig = item.get("original_title") or ""
    item["tags"] = ["bg subtitles", orig.lower()] if orig else ["bg subtitles"]
    item["is_bg_audio"] = False
    item["is_subtitled"] = True
    item["has_filmi2k_bg"] = False
    for src in item.get("player_sources", []):
        src["group"] = "sub"
        src["name"] = src["name"].replace("🇧🇬", "💬")
    return item


def save_outputs(items: list[dict]) -> None:
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.FILMI2K_SUB_DATA = ")
        json.dump(items, f, ensure_ascii=False)
        f.write(";\n")


def main() -> None:
    bg_urls = {x.get("url") for x in load_json_list(BG_JSON) if isinstance(x, dict)}
    existing = {}
    for x in load_json_list(OUTPUT_JSON):
        if isinstance(x, dict) and x.get("url"):
            existing[x["url"]] = x

    all_urls = collect_sitemap_urls()
    print(f"Общо публикации в sitemap: {len(all_urls)} (БГ аудио вече налични: {len(bg_urls)})")

    to_scrape = [u for u in all_urls if u not in bg_urls and u not in existing]
    print(f"За скрейпване: {len(to_scrape)} (кеширани: {len(existing)})")

    lock = threading.Lock()
    done = 0
    ordered_urls = [u for u in all_urls if u not in bg_urls]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_sub_detail, u): u for u in to_scrape}
        for future in as_completed(futures):
            try:
                res = future.result()
            except Exception:
                res = None
            with lock:
                done += 1
                if res:
                    existing[res["url"]] = res
                if done % SAVE_EVERY == 0 or done == len(to_scrape):
                    save_outputs([existing[u] for u in ordered_urls if u in existing])
                    print(f"Прогрес: {done}/{len(to_scrape)} (записани {len(existing)})")

    final = [existing[u] for u in ordered_urls if u in existing]
    save_outputs(final)
    sub_count = sum(1 for x in final if x.get("is_subtitled"))
    print(f"Готово! Записани: {len(final)} (субтитри: {sub_count}, пропуснати БГ аудио: {len(final) - sub_count})")


if __name__ == "__main__":
    main()

