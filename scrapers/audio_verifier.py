#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audio_verifier.py

Модул и CLI скрипт за разпознаване и коригиране на противоречия между
„БГ Аудио“ и „БГ Субтитри“ в кодовата база и скраперите.
"""

import json
import os
import re

SUBTITLE_REGEXES = [
    re.compile(r"(?i)\b(?:бг\s*субтитри|български\s*субтитри|(?:със|с|и|без)\s*субтитри|вградени\s*субтитри)\b"),
    re.compile(r"(?i)\b(?:само\s*субтитри|само\s*със\s*субтитри|няма\s*(?:бг\s*)?(?:аудио|дублаж))\b"),
    re.compile(r"(?i)(?:превод|субтитри)\s*:\s*(?:български\s*)?субтитри"),
    re.compile(r"(?i)аудио\s*:\s*(?:английско|оригинално|руско|турско|испанско)"),
    re.compile(r"(?i)език\s*:\s*(?:английски|оригинален|руски)"),
    re.compile(r"(?i)\((?:бг\s*)?суб(?:титри)?\)"),
    re.compile(r"(?i)\[(?:бг\s*)?суб(?:титри)?\]"),
    re.compile(r"(?i)/\s*(?:бг\s*)?субтитри"),
    re.compile(r"(?i)\b(?:bg\s*subs?|subtitled|bulgarian\s*subs)\b"),
]

DUBBING_REGEXES = [
    re.compile(r"(?i)\b(?:български\s*дублаж|професионален\s*дублаж|дублиран\s*на\s*български)\b"),
    re.compile(r"(?i)\b(?:озвучен(?:о|и)?\s*на\s*български|ролите\s*озвучиха|озвучаващи\s*артисти)\b"),
    re.compile(r"(?i)\b(?:александра\s*аудио|доли\s*медия|андарта|про\s*филмс|арс\s*диджитал|бнт|нова\s*телевизия|btv)\b"),
    re.compile(r"(?i)аудио\s*:\s*българско"),
    re.compile(r"(?i)дублаж\s*:\s*български"),
    re.compile(r"(?i)\b(?:едногласово\s*българско\s*аудио|българско\s*аудио\s*с\s*включени\s*субтитри)\b"),
    re.compile(r"(?i)\bсубтитри\s*само\s*на\s*песните\b"),
]


def classify_audio_type(title: str, overview: str, genres: list[str] | None = None, player_sources: list[dict] | None = None) -> tuple[bool, bool, str]:
    """
    Класифицира дали филмът е БГ Аудио или БГ Субтитри.
    Връща (is_bg_audio, is_subtitled, reason).
    """
    title_str = str(title or "")
    overview_str = str(overview or "")
    full_text = f"{title_str} {overview_str}"

    genres = genres or []
    sources = player_sources or []

    # 1. Проверка за потвърден реален дублаж (изрично споменаване на озвучаване/студио)
    for dp in DUBBING_REGEXES:
        if dp.search(full_text):
            return True, False, "Потвърден дублаж в текста"

    # 2. Проверка за индикатори на субтитри в заглавието
    if re.search(r"(?i)(?:бг\s*субтитри|български\s*субтитри|/\s*субтитри|\(субтитри\)|\(суб\.?\)|\(sub\)|и\s*субтитри|bg\s*subs?)", title_str):
        return False, True, f"Заглавието съдържа маркер за субтитри: '{title_str}'"

    # 3. Проверка на плеърите - ако всички са изрично sub
    if sources:
        all_sub = True
        has_named = False
        for s in sources:
            name = str(s.get("name") or "").lower()
            if name:
                has_named = True
                if not any(k in name for k in ["суб", "sub", "💬"]):
                    all_sub = False
                    break
        if has_named and all_sub:
            return False, True, "Всички налични плеъри са маркирани като (Субтитри / Sub)"

    # 4. Проверка в жанровете/категориите от източника
    for g in genres:
        g_low = str(g).lower()
        if ("субтитр" in g_low or "sub" in g_low) and "аудио" not in g_low:
            return False, True, f"В жанровете/категориите присъства '{g}'"

    # 5. Проверка в описанието
    for sp in SUBTITLE_REGEXES:
        m = sp.search(full_text)
        if m:
            return False, True, f"В описанието пише: '{m.group(0)}'"

    # По подразбиране остава БГ Аудио
    return True, False, "Нормално БГ Аудио"


def audit_and_fix_movie_item(item: dict) -> bool:
    """
    Проверява и коригира един запис. Връща True, ако е направена корекция.
    """
    title = item.get("title") or item.get("original_title") or ""
    overview = item.get("overview") or ""
    genres = item.get("genres") or []
    sources = item.get("player_sources") or []

    is_marked_bg = item.get("is_bg_audio") is True or "БГ Аудио" in genres
    if not is_marked_bg:
        return False

    is_bg, is_sub, reason = classify_audio_type(title, overview, genres, sources)
    if not is_bg and is_sub:
        item["is_bg_audio"] = False
        item["is_subtitled"] = True
        new_genres = [g for g in genres if g != "БГ Аудио"]
        if "БГ Субтитри" not in new_genres:
            new_genres.append("БГ Субтитри")
        item["genres"] = new_genres
        for s in sources:
            if s.get("group") == "bg":
                s["group"] = "sub"
        return True

    return False


def clean_all_catalogs(data_dir: str) -> int:
    catalogs = [
        ("filmi2k_bg.json", "FILMI2K_BG_DATA"),
        ("filmifen_bg.json", "FILMIFEN_BG_DATA"),
        ("filmizip_bg.json", "FILMIZIP_BG_DATA"),
        ("playtube_bg.json", "PLAYTUBE_BG_DATA"),
        ("movies.json", "MOVIES_DATA"),
        ("bg_serials.json", "BG_SERIALS_DATA"),
        ("tv_shows.json", "TV_SHOWS_DATA"),
    ]

    total_fixed = 0
    for json_file, js_var in catalogs:
        json_path = os.path.join(data_dir, json_file)
        if not os.path.exists(json_path):
            continue
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            continue
        if not isinstance(items, list):
            continue

        fixed_in_file = 0
        for it in items:
            if audit_and_fix_movie_item(it):
                fixed_in_file += 1

        if fixed_in_file > 0:
            total_fixed += fixed_in_file
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)

            js_file = json_file.replace(".json", "_data.js")
            js_path = os.path.join(data_dir, js_file)
            if os.path.exists(js_path):
                try:
                    with open(js_path, "w", encoding="utf-8") as f:
                        f.write(f"window.{js_var} = ")
                        json.dump(items, f, ensure_ascii=False)
                        f.write(";\n")
                except Exception:
                    pass

    return total_fixed


if __name__ == "__main__":
    import sys
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    count = clean_all_catalogs(data_dir)
    print(f"[✓] Одитът приключи. Коригирани записи: {count}")
