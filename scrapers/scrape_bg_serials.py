import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_JSON = os.path.join(DATA_DIR, "bg_serials.json")
OUTPUT_JS = os.path.join(DATA_DIR, "bg_serials_data.js")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://filmizip.com/seriali/"
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

def discover_filmizip_serials(max_pages: int = 15) -> list[str]:
    links = []
    print(f"[*] Discovering Filmizip serials (pages 1 to {max_pages})...")
    for page in range(1, max_pages + 1):
        url = f"https://filmizip.com/seriali/page/{page}/" if page > 1 else "https://filmizip.com/seriali/"
        html = fetch_url(url)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        page_links = []
        for a in soup.select("a"):
            href = a.get("href", "")
            if href.endswith(".html") and "/seriali/" in href:
                if href not in links and href not in page_links:
                    page_links.append(href)
        if not page_links:
            break
        links.extend(page_links)
        print(f"  Filmizip Serials P.{page}: +{len(page_links)} (total {len(links)})")
    return links

def parse_filmizip_serial(url: str) -> dict:
    from scrape_filmizip import parse_page
    item = parse_page(url)
    if item:
        item["type"] = "tv"
        if not item.get("genres"):
            item["genres"] = ["Сериали"]
        elif "Сериали" not in item["genres"]:
            item["genres"].append("Сериали")
    return item

def scrape_all_bg_serials():
    filmizip_links = discover_filmizip_serials(max_pages=20)
    print(f"[+] Total serial links discovered: {len(filmizip_links)}")
    
    results = []
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = {executor.submit(parse_filmizip_serial, url): url for url in filmizip_links}
        done = 0
        for f in as_completed(futures):
            done += 1
            res = f.result()
            if res and res.get("title"):
                results.append(res)
            if done % 25 == 0 or done == len(futures):
                print(f"[*] Parsed {done}/{len(futures)} serials (valid: {len(results)})")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.BG_SERIALS_DATA = ")
        json.dump(results, f, ensure_ascii=False)
        f.write(";\n")

    print(f"[SUCCESS] Scraped {len(results)} serials into {OUTPUT_JS}!")
    return len(results)

if __name__ == "__main__":
    scrape_all_bg_serials()

