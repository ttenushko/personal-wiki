"""Валидация и очистка неструктурированного вывода LLM."""

from __future__ import annotations

import re
import unicodedata

# Символы, недопустимые в именах файлов Windows
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# "Reasoning-обрывки": текст, который LLM-модель выдала вместо чистого ответа
_REASONING_MARKERS = (
    "хорошо, ",
    "пожалуйста, ",
    "для этого",
    "мне нужно",
    "давайте",
    "итак",
    "итак,",
    "нужно",
    "сначала",
    "затем",
    "теперь",
)

_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def clean_tag(raw: str) -> str | None:
    """Очистить тег из вывода LLM; вернуть None, если тег невалиден."""
    tag = raw.strip().strip("`").strip("#").strip()
    if not tag:
        return None
    # Внутренние пробелы и спецсимволы (кроме дефиса/подчёркивания) — невалидны
    if re.search(r"\s", tag) or re.search(r"[^\w\-\_]+", tag, flags=re.UNICODE):
        return None
    if tag.lower() in {"и", "в", "на", "с", "по", "из", "или", "ибо", "нет", "ок"}:
        return None
    return tag


def extract_tags_from_text(text: str) -> list[str]:
    """Извлечь теги из сырого ответа LLM (через запятую, строки или #)."""
    tags: list[str] = []
    # 1) Явные #теги (модель может вернуть их разделёнными пробелами)
    for match in re.finditer(r"#([\w\-]+)", text):
        tag = clean_tag(match.group(1))
        if tag and tag not in tags:
            tags.append(tag)
    # 2) Список через запятую/точку с запятой/строки
    text_no_hashtags = re.sub(r"#[\w\-]+", "", text)
    for part in re.split(r"[,;\n]", text_no_hashtags):
        tag = clean_tag(part)
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def clean_slug(raw: str) -> str | None:
    """Очистить slug из вывода LLM; вернуть None, если он невалиден."""
    slug = raw.strip().strip("`\"'()").strip()
    if not slug:
        return None
    # Отбрасываем длинные рассуждения, которые модель выдала вместо slug
    lowered = slug.lower()
    if len(slug) > 100 or any(lowered.startswith(m) for m in _REASONING_MARKERS):
        return None
    slug = _INVALID_FILENAME_CHARS.sub("-", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^\w\-]+", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[-_]+", "-", slug).strip("-.")
    slug = slug.lower()
    # Windows reserved names (CON, PRN, AUX, NUL, COM1..)
    stem = slug.split(".")[0].upper()
    if stem in _WINDOWS_RESERVED:
        return None
    if not slug:
        return None
    # Кириллица в slug допустима (файловая система Windows её поддерживает)
    return slug


def transliterate_slug_fallback(title: str) -> str:
    """Создать slug из заголовка без LLM (транслитерация + чистка)."""
    translit = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
        "А": "a", "Б": "b", "В": "v", "Г": "g", "Д": "d", "Е": "e", "Ё": "e",
        "Ж": "zh", "З": "z", "И": "i", "Й": "y", "К": "k", "Л": "l", "М": "m",
        "Н": "n", "О": "o", "П": "p", "Р": "r", "С": "s", "Т": "t", "У": "u",
        "Ф": "f", "Х": "kh", "Ц": "ts", "Ч": "ch", "Ш": "sh", "Щ": "shch",
        "Ъ": "", "Ы": "y", "Ь": "", "Э": "e", "Ю": "yu", "Я": "ya",
    }
    slug = "".join(translit.get(ch, ch) for ch in title)
    slug = unicodedata.normalize("NFKD", slug)
    slug = slug.encode("ascii", "ignore").decode()
    slug = _INVALID_FILENAME_CHARS.sub("-", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[-_]+", "-", slug).strip("-.")
    slug = slug.lower()
    return slug[:80] or "untitled"
