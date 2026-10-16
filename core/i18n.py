# core/i18n.py

import json
import os
import random

LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "locales",
)
DEFAULT_LANG = "en"

_translations: dict[str, dict] = {}
_last_pick: dict[str, str] = {}  # кеш последних выборов


def load_locales():
    global _translations
    _translations = {}
    for filename in os.listdir(LOCALES_DIR):
        if filename.endswith(".json"):
            lang = filename[:-5]
            path = os.path.join(LOCALES_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                _translations[lang] = json.load(f)


def get_all_translations() -> dict[str, dict]:
    return _translations


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    lang_data = _translations.get(lang) or _translations.get(DEFAULT_LANG, {})
    value = lang_data.get(key)

    if value is None:
        value = _translations.get(DEFAULT_LANG, {}).get(key, key)

    # Если значение — список, выбираем случайный вариант
    if isinstance(value, list):
        value = _pick_random(value, key, lang)

    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError):
            return value
    return value


def _pick_random(options: list, key: str, lang: str) -> str:
    """Выбирает случайный вариант, избегая повтора последнего."""
    if not options:
        return key
    if len(options) == 1:
        return options[0]

    cache_key = f"{lang}:{key}"
    last = _last_pick.get(cache_key)

    # Фильтруем варианты, исключая последний
    candidates = [o for o in options if o != last]
    if not candidates:
        candidates = options

    choice = random.choice(candidates)
    _last_pick[cache_key] = choice
    return choice

import re as _re

_ALLOWED_TAGS = ('b', 'i', 'u', 's', 'code', 'pre', 'a', 'tg-spoiler')


def escape_html_entities(text: str) -> str:
    """Экранирует < и >, кроме настоящих HTML-тегов."""
    placeholders = {}
    
    def protect(match):
        key = f"\x00TAG{len(placeholders)}\x00"
        placeholders[key] = match.group(0)
        return key
    
    protected = _re.sub(
        r"</?(" + "|".join(_ALLOWED_TAGS) + r")(\s[^>]*)?>",
        protect,
        text,
    )
    protected = protected.replace("<", "&lt;").replace(">", "&gt;")
    
    for key, tag in placeholders.items():
        protected = protected.replace(key, tag)
    return protected
