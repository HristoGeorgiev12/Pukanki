import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

MOVIES_JSON = os.path.join(DATA_DIR, "movies.json")
MOVIES_JS = os.path.join(DATA_DIR, "movies_data.js")

def normalize_key(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r'[\(\)\[\]\{\}\<\>\"\'`«»„“,\.:;!?_\-—–/\\\|+*~#@$%^&=]', ' ', str(s))
    return re.sub(r'\s+', ' ', s).strip().lower()

def enrich_zenoplay():
    print("[*] Зареждане на ZenoPlay базата...")
    with open(MOVIES_JSON, "r", encoding="utf-8") as f:
        movies = json.load(f)

    # 1. Зареждане на Filmi9 (за точно TMDB_ID съвпадение)
    f9_path = os.path.join(DATA_DIR, "filmi9_data.json")
    f9_by_tmdb = {}
    f9_by_title_year = {}
    f9_by_title = {}
    if os.path.exists(f9_path):
        with open(f9_path, "r", encoding="utf-8") as f:
            f9_data = json.load(f)
        for it in f9_data:
            ot = it.get("original_title")
            if not ot:
                continue
            tid = it.get("tmdb_id")
            if tid:
                try:
                    f9_by_tmdb[int(tid)] = ot
                except:
                    pass
            k = normalize_key(it.get("title"))
            y = it.get("year")
            if k:
                if y:
                    f9_by_title_year[f"{k}|{y}"] = ot
                if k not in f9_by_title:
                    f9_by_title[k] = ot

    # 2. Зареждане на останалите каталози (Filmifen, Filmi2k, Filmizip, Subtitled)
    other_catalogs = [
        os.path.join(DATA_DIR, "filmifen_bg.json"),
        os.path.join(DATA_DIR, "filmi2k_bg.json"),
        os.path.join(DATA_DIR, "filmi2k_sub.json"),
    ]
    cross_title_year = {}
    cross_title = {}

    for path in other_catalogs:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            cat_data = json.load(f)
        for it in cat_data:
            ot = it.get("original_title")
            if not ot:
                continue
            raw_t = it.get("title", "")
            y = it.get("year")
            variants = [raw_t]
            if "/" in raw_t:
                variants.extend(raw_t.split("/"))
            if ":" in raw_t:
                variants.append(raw_t.split(":")[0])
            for v in variants:
                k = normalize_key(v)
                if k:
                    if y:
                        cross_title_year[f"{k}|{y}"] = ot
                    if k not in cross_title:
                        cross_title[k] = ot

    # 3. Обогатяване на ZenoPlay
    matched_tmdb = 0
    matched_f9_title = 0
    matched_cross = 0
    already_had = 0

    for m in movies:
        if m.get("original_title"):
            already_had += 1
            continue

        tid = m.get("tmdb_id")
        ot = None
        # Метод 1: Filmi9 TMDB ID (най-надежден, 100% точност)
        if tid:
            try:
                ot = f9_by_tmdb.get(int(tid))
                if ot:
                    matched_tmdb += 1
            except:
                pass

        # Метод 2: Filmi9 заглавие + година
        t = normalize_key(m.get("title"))
        y = m.get("year")
        if not ot and t and y:
            ot = f9_by_title_year.get(f"{t}|{y}")
            if ot:
                matched_f9_title += 1

        # Метод 3: Крос-каталог заглавие + година
        if not ot and t and y:
            ot = cross_title_year.get(f"{t}|{y}")
            if ot:
                matched_cross += 1

        # Метод 4: Без година (ако разликата е малка)
        if not ot and t:
            ot = cross_title.get(t) or f9_by_title.get(t)
            if ot:
                matched_cross += 1

        # Метод 5: Базово заглавие преди ':'
        if not ot and ":" in m.get("title", ""):
            base_t = normalize_key(m.get("title", "").split(":")[0])
            if base_t and y:
                ot = cross_title_year.get(f"{base_t}|{y}") or f9_by_title_year.get(f"{base_t}|{y}")
                if ot:
                    matched_cross += 1

        if ot:
            m["original_title"] = ot.strip()

    total_with_orig = sum(1 for m in movies if m.get("original_title"))
    print(f"[+] Обогатяване завършено:")
    print(f"  - Чрез TMDB ID от Filmi9: {matched_tmdb}")
    print(f"  - Чрез Filmi9 заглавие: {matched_f9_title}")
    print(f"  - Чрез Filmifen / Filmi2k / Filmizip: {matched_cross}")
    print(f"  - Общо с попълнен original_title: {total_with_orig} / {len(movies)} ({round(total_with_orig/len(movies)*100, 1)}%)")

    # Запис във файловете
    print(f"[*] Записване в {MOVIES_JSON}...")
    with open(MOVIES_JSON, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=2)

    print(f"[*] Записване в {MOVIES_JS}...")
    with open(MOVIES_JS, "w", encoding="utf-8") as f:
        f.write("window.MOVIES_DATA = ")
        json.dump(movies, f, ensure_ascii=False)
        f.write(";\n")

    print("[✔] movies.json и movies_data.js бяха успешно обновени!")

if __name__ == "__main__":
    enrich_zenoplay()

