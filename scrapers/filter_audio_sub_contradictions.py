#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filter_audio_sub_contradictions.py

Преглежда каталозите и скраперите за противоречия между "БГ Аудио" и "БГ Субтитри".
Ако филм е маркиран като "БГ Аудио", но заглавието, описанието или източниците
показват, че всъщност е със субтитри (без дублаж), скриптът:
1. Коригира is_bg_audio = False, is_subtitled = True
2. Заменя "БГ Аудио" с "БГ Субтитри" в genres
3. Опреснява JSON и JS файловете на базата
"""

import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Индикатори за субтитри (без дублаж)
SUBTITLE_PATTERNS = [
    re.compile(r"(?i)\b(?:бг\s*субтитри|български\s*субтитри|със\s*субтитри|вградени\s*субтитри)\b"),
    re.compile(r"(?i)\b(?:само\s*субтитри|само\s*със\s*субтитри|няма\s*(?:бг\s*)?(?:аудио|дублаж))\b"),
    re.compile(r"(?i)(?:превод|субтитри)\s*:\s*(?:български\s*)?субтитри"),
    re.compile(r"(?i)аудио\s*:\s*(?:английско|оригинално|руско|турско|испанско)"),
    re.compile(r"(?i)език\s*:\s*(?:английски|оригинален|руски)"),
    re.compile(r"(?i)\((?:бг\s*)?суб(?:титри)?\)"),
    re.compile(r"(?i)\[(?:бг\s*)?суб(?:титри)?\]"),
    re.compile(r"(?i)/\s*(?:бг\s*)?субтитри"),
]

# Индикатори за реален дублаж (отхвърлят подозрението за само субтитри)
DUBBING_PATTERNS = [
    re.compile(r"(?i)\b(?:български\s*дублаж|професионален\s*дублаж|дублиран\s*на\s*български)\b"),
    re.compile(r"(?i)\b(?:озвучен(?:о|и)?\s*на\s*български|ролите\s*озвучиха|озвучаващи\s*артисти)\b"),
    re.compile(r"(?i)\b(?:александра\s*аудио|доли\s*медия|андарта|про\s*филмс|арс\s*диджитал|бнт|нова\s*телевизия|btv)\b"),
    re.compile(r"(?i)аудио\s*:\s*българско"),
    re.compile(r"(?i)дублаж\s*:\s*български"),
]


def detect_audio_contradiction(item: dict) -> tuple[bool, str]:
    """
    Проверява дали филмът има признаци за субтитри, въпреки че е маркиран като БГ Аудио.
    Връща (is_contradiction, reason).
    """
    title = str(item.get("title") or "")
    overview = str(item.get("overview") or "")
    full_text = f"{title} {overview}"

    is_marked_bg = item.get("is_bg_audio") is True or "БГ Аудио" in (item.get("genres") or [])
    if not is_marked_bg:
        return False, ""

    # Проверка за сигурни признаци на дублаж
    for dp in DUBBING_PATTERNS:
        if dp.search(full_text):
            return False, "Има потвърден дублаж"

    # 1. Проверка в заглавието (най-силен индикатор)
    if re.search(r"(?i)(?:бг\s*субтитри|/\s*субтитри|\(субтитри\)|\(суб\.?\)|\(sub\))", title):
        return True, f"Заглавието съдържа индикатор за субтитри: '{title}'"

    # 2. Проверка в описанието
    for sp in SUBTITLE_PATTERNS:
        m = sp.search(full_text)
        if m:
            matched_phrase = m.group(0)
            return True, f"В описанието пише: '{matched_phrase}'"

    # 3. Проверка на плеърите
    sources = item.get("player_sources") or []
    if sources and isinstance(sources, list):
        all_sub = True
        has_named_source = False
        for s in sources:
            s_name = str(s.get("name") or "").lower()
            if s_name:
                has_named_source = True
                if not any(k in s_name for k in ["суб", "sub"]):
                    all_sub = False
                    break
        if has_named_source and all_sub:
            return True, "Всички плеъри са маркирани като (Субтитри / Sub)"

    return False, ""


def fix_contradiction(item: dict, reason: str) -> None:
    """Коригира метаданните на филма да сочат БГ Субтитри вместо БГ Аудио."""
    item["is_bg_audio"] = False
    item["is_subtitled"] = True

    genres = item.get("genres") or []
    if isinstance(genres, list):
        genres = [g for g in genres if g != "БГ Аудио"]
        if "БГ Субтитри" not in genres:
            genres.append("БГ Субтитри")
        item["genres"] = genres

    sources = item.get("player_sources") or []
    if isinstance(sources, list):
        for s in sources:
            if s.get("group") == "bg":
                s["group"] = "sub"


def process_catalog_file(json_filename: str, js_var_name: str | None = None) -> int:
    json_path = os.path.join(DATA_DIR, json_filename)
    if not os.path.exists(json_path):
        return 0

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception as e:
        print(f"[!] Грешка при зареждане на {json_filename}: {e}")
        return 0

    if not isinstance(items, list):
        return 0

    fixed_count = 0
    for it in items:
        is_contra, reason = detect_audio_contradiction(it)
        if is_contra:
            title = it.get("title") or it.get("original_title") or "Без заглавие"
            year = it.get("year") or ""
            print(f"  [FIX] {title} ({year}) -> {reason}")
            fix_contradiction(it, reason)
            fixed_count += 1

    if fixed_count > 0:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"  [*] Записан обновен JSON: {json_filename} ({fixed_count} коригирани)")

        # Обновяване и на прилежащия JS файл ако има такъв
        if js_var_name:
            js_filename = json_filename.replace(".json", "_data.js")
            js_path = os.path.join(DATA_DIR, js_filename)
            try:
                with open(js_path, "w", encoding="utf-8") as f:
                    f.write(f"window.{js_var_name} = ")
                    json.dump(items, f, ensure_ascii=False)
                    f.write(";\n")
                print(f"  [*] Записан обновен JS: {js_filename}")
            except Exception as e:
                print(f"  [!] Грешка при запис на {js_filename}: {e}")

    return fixed_count


def main():
    print("==========================================================")
    print("   ПРОВЕРКА И ФИЛТРИРАНЕ НА ПРОТИВОРЕЧИЯ (АУДИО vs СУБ)")
    print("==========================================================")

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
        print(f"\n[+] Сканиране на {json_file}...")
        c = process_catalog_file(json_file, js_var)
        total_fixed += c

    print(f"\n[✓] ГОТОВО! Общо коригирани филма: {total_fixed}")


if __name__ == "__main__":
    main()
