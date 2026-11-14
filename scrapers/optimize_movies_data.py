import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

MOVIES_SRC = os.path.join(DATA_DIR, "movies.json")
MOVIES_JS_DEST = os.path.join(DATA_DIR, "movies_data.js")

STD_IDS = {
    "vidsrc", "1src", "yapgrid", "embedmaster", "vidsrc2", "vidapi",
    "2embed", "vidlink", "videasy", "vidy", "vidzee", "cinesrc", "vidcore"
}


def optimize():
    print(f"Reading {MOVIES_SRC}...")
    with open(MOVIES_SRC, "r", encoding="utf-8") as f:
        movies = json.load(f)

    initial_count = len(movies)
    optimized = []
    for m in movies:
        item = dict(m)
        sources = item.get("player_sources", [])
        # Keep all non-standard sources (such as BG Player / custom-1, Filmi2k, Filmizip, etc.)
        custom = [s for s in sources if s.get("id") not in STD_IDS]
        item["player_sources"] = custom
        optimized.append(item)

    print(f"Processed {initial_count} movies.")
    tmp_js = f"{MOVIES_JS_DEST}.tmp"
    with open(tmp_js, "w", encoding="utf-8") as f:
        f.write(f"window.MOVIES_DATA = {json.dumps(optimized, ensure_ascii=False)};\n")
    os.replace(tmp_js, MOVIES_JS_DEST)

    orig_size = os.path.getsize(os.path.join(DATA_DIR, "movies_data.js.bak")) / (1024 * 1024)
    new_size = os.path.getsize(MOVIES_JS_DEST) / (1024 * 1024)
    print(f"Size reduced from {orig_size:.2f} MB to {new_size:.2f} MB! (Saved {orig_size - new_size:.2f} MB)")


if __name__ == "__main__":
    optimize()

