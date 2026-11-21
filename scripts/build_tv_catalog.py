import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OUT_PATH = os.path.join(DATA_DIR, "tv_catalog.json")


def norm_key(title):
    s = str(title or "").lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[^\w\u0400-\u04FF]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_json(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def is_valid_direct_source(s):
    if not isinstance(s, dict):
        return False
    if s.get("direct_embed") is False:
        return False
    url = str(s.get("embed_url") or "").strip()
    if not url.startswith("http"):
        return False
    low = url.lower()
    if "filmizip.com/player.html" in low or "filmizip.com/filmi/" in low or "filmizip.com/seriali/" in low:
        return False
    if "playtube.tv/watch/" in low or "filmi9.com/film/" in low or "filmi2k.com/" in low:
        return False
    grp = str(s.get("group") or "").lower()
    if grp == "en":
        return False
    return True


def host_priority(url):
    u = url.lower()
    if "streamtape" in u or "streamta.pe" in u:
        return 1
    if "voe.sx" in u or "voe." in u:
        return 2
    if "videa.hu" in u:
        return 2
    if "ok.ru" in u:
        return 3
    if "vidon.to" in u:
        return 4
    if "uqload" in u or "dropload" in u or "abstream" in u or "luluvid" in u:
        return 5
    if "filemoon" in u or "byse" in u:
        return 6
    if "vsembed" in u or "vidsrc" in u:
        return 8
    return 7


def clean_source_name(name, url):
    n = str(name or "").strip()
    if not n:
        u = url.lower()
        if "streamtape" in u:
            n = "Streamtape"
        elif "voe" in u:
            n = "VOE"
        elif "vidon" in u:
            n = "Vidon"
        elif "ok.ru" in u:
            n = "OK.ru"
        elif "videa.hu" in u:
            n = "Videa"
        elif "filemoon" in u or "byse" in u:
            n = "Filemoon"
        elif "vsembed" in u:
            n = "VidRu"
        else:
            n = "Плеър"
    return n


def main():
    # Build metadata enrichment lookup from movies.json & tv_shows.json
    meta_by_tmdb = {}
    meta_by_key = {}
    for fname in ("movies.json", "tv_shows.json"):
        for item in load_json(fname):
            tid = item.get("tmdb_id")
            if tid:
                meta_by_tmdb[str(tid)] = item
            k = norm_key(item.get("title"))
            if k:
                meta_by_key[k] = item
            ok = norm_key(item.get("original_title"))
            if ok and ok not in meta_by_key:
                meta_by_key[ok] = item

    # Merge playable BG & SUB datasets
    datasets = [
        ("filmifen_bg.json", True, False),
        ("filmi2k_bg.json", True, False),
        ("playtube_bg.json", True, False),
        ("bg_serials.json", True, False),
        ("filmi9_data.json", False, True),
        ("filmi2k_sub.json", False, True),
        ("videa_dock.json", False, True),
        ("subtitled_movies.json", False, True),
    ]

    merged = {}
    tmdb_to_mkey = {}

    for fname, default_bg, default_sub in datasets:
        items = load_json(fname)
        for item in items:
            raw_sources = item.get("player_sources") or []
            valid_sources = [s for s in raw_sources if is_valid_direct_source(s)]
            if not valid_sources:
                continue

            title = str(item.get("title") or "").strip()
            if not title:
                continue

            year = item.get("year")
            try:
                year = int(year) if year else 0
            except Exception:
                year = 0

            tmdb_id = str(item.get("tmdb_id") or "").strip()
            base_k = norm_key(title)
            mkey = None
            if tmdb_id and tmdb_id in tmdb_to_mkey:
                mkey = tmdb_to_mkey[tmdb_id]
            else:
                cand_k = f"{base_k}|{year}" if year else base_k
                if cand_k in merged:
                    mkey = cand_k
                elif base_k in merged and not year:
                    mkey = base_k
                else:
                    mkey = cand_k

            if tmdb_id:
                tmdb_to_mkey[tmdb_id] = mkey

            # Enrich from movies.json / tv_shows.json if needed
            meta = (meta_by_tmdb.get(tmdb_id) if tmdb_id else None) or meta_by_key.get(base_k) or {}

            is_bg = bool(item.get("is_bg_audio")) if item.get("is_bg_audio") is not None else default_bg
            is_sub = bool(item.get("is_subtitled")) if item.get("is_subtitled") is not None else default_sub
            for vs in valid_sources:
                grp = str(vs.get("group") or "").lower()
                nm = str(vs.get("name") or "")
                if grp == "bg" or "🇧🇬" in nm:
                    is_bg = True
                if grp == "sub" or "💬" in nm:
                    is_sub = True

            is_tv = str(item.get("type") or meta.get("type") or "").lower() == "tv"

            if mkey not in merged:
                rating = item.get("rating") or meta.get("rating") or 0
                try:
                    rating = round(float(rating), 1)
                except Exception:
                    rating = 0.0

                dur = item.get("duration_minutes") or meta.get("duration_minutes") or 0
                try:
                    dur = int(dur)
                except Exception:
                    dur = 0

                overview = str(item.get("overview") or meta.get("overview") or "").strip()
                if len(overview) > 360:
                    overview = overview[:357].rsplit(" ", 1)[0] + "..."

                raw_genres = item.get("genres") or meta.get("genres") or []
                clean_genres = [
                    str(g).strip()
                    for g in raw_genres
                    if str(g).strip()
                    and "бг аудио" not in str(g).lower()
                    and "субтитри" not in str(g).lower()
                ][:4]

                merged[mkey] = {
                    "t": title,
                    "ot": str(item.get("original_title") or meta.get("original_title") or "").strip(),
                    "y": year or int(meta.get("year") or 0),
                    "r": rating,
                    "d": dur,
                    "p": str(item.get("poster_url") or meta.get("poster_url") or "").strip(),
                    "b": str(item.get("backdrop_url") or meta.get("backdrop_url") or "").strip(),
                    "o": overview,
                    "g": clean_genres,
                    "bg": 1 if is_bg else 0,
                    "sub": 1 if is_sub else 0,
                    "tp": "s" if is_tv else "m",
                    "s": [],
                    "_urls": set(),
                }

            rec = merged[mkey]
            if is_bg:
                rec["bg"] = 1
            if is_sub:
                rec["sub"] = 1
            if not rec["p"] and item.get("poster_url"):
                rec["p"] = str(item.get("poster_url")).strip()
            if not rec["b"] and item.get("backdrop_url"):
                rec["b"] = str(item.get("backdrop_url")).strip()
            if not rec["o"] and item.get("overview"):
                ov = str(item.get("overview")).strip()
                rec["o"] = ov[:357] + "..." if len(ov) > 360 else ov

            for vs in valid_sources:
                u = str(vs.get("embed_url")).strip()
                if u in rec["_urls"]:
                    continue
                rec["_urls"].add(u)
                grp = str(vs.get("group") or ("bg" if is_bg and not default_sub else "sub")).lower()
                if grp not in ("bg", "sub"):
                    grp = "bg" if is_bg else "sub"
                nm = clean_source_name(vs.get("name"), u)
                rec["s"].append([nm, grp, u])

    result = []
    for rec in merged.values():
        rec.pop("_urls", None)
        if not rec["s"] or not rec["p"]:
            continue
        # Sort sources: BG audio first, then best native-playable hosts
        rec["s"].sort(key=lambda x: (0 if x[1] == "bg" else 1, host_priority(x[2])))
        # Cap to top 8 sources per movie to keep payload super lean
        rec["s"] = rec["s"][:8]
        # Drop empty optional keys to shrink JSON
        if not rec["ot"]:
            rec.pop("ot", None)
        if not rec["b"]:
            rec.pop("b", None)
        if not rec["d"]:
            rec.pop("d", None)
        result.append(rec)

    # Sort catalog: BG audio with multiple players & realistic high ratings (ignore fake 10.0 ratings) & newest first
    def sort_key(x):
        r = x["r"] if 0 < x["r"] < 9.6 else 6.5
        multi_src = 1 if len(x["s"]) >= 2 else 0
        recent = 1 if x["y"] >= 2018 else 0
        return (x["bg"], recent, multi_src, round(r, 1), x["y"])

    result.sort(key=sort_key, reverse=True)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(OUT_PATH) / 1024
    bg_cnt = sum(1 for x in result if x["bg"] == 1)
    sub_cnt = sum(1 for x in result if x["bg"] == 0)
    print(f"Built {OUT_PATH}: {len(result)} playable items ({bg_cnt} BG audio, {sub_cnt} BG sub), size: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
