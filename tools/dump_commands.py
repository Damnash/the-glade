# tools/dump_commands.py

import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.i18n import load_locales, t, get_all_translations


COMMANDS = [
    "start", "help", "look", "go", "who", "where",
    "language", "stats", "sleep", "wake", "work",
    "eat", "inventory", "use",
]


def clean_desc(desc: str) -> str:
    desc = desc.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    for sep in (" — ", " - ", " – "):
        if sep in desc:
            desc = desc.split(sep, 1)[1]
            break
    return desc.strip()


def pick_alias(key: str, lang: str, all_langs: dict) -> str:
    lang_data = all_langs.get(lang, {})
    aliases = lang_data.get(key)
    if isinstance(aliases, str):
        aliases = [aliases]
    if aliases:
        return aliases[0]

    en_aliases = all_langs.get("en", {}).get(key)
    if isinstance(en_aliases, str):
        en_aliases = [en_aliases]
    return en_aliases[0] if en_aliases else "?"


def dump(lang: str, all_langs: dict) -> None:
    print(f"# === {lang.upper()} ===")
    for key in COMMANDS:
        alias = pick_alias(f"commands.{key}", lang, all_langs)
        desc = clean_desc(t(f"help.{key}", lang))
        print(f"{alias} - {desc}")
    print()


if __name__ == "__main__":
    load_locales()
    all_langs = get_all_translations()
    dump("en", all_langs)
    dump("ru", all_langs)