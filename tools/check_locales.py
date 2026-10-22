# tools/check_locales.py
#
# Проверка локалей: все ключи, используемые в коде, должны быть в en.json + ru.json.

import os
import re
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def collect_keys_from_code() -> set[str]:
    """Собрать все t("key") и t("key", ...) из кода."""
    keys = set()
    skip_dirs = {"__pycache__", ".venv", "venv", "backups", "data", ".git"}
    for py in ROOT.rglob("*.py"):
        if any(p in py.parts for p in skip_dirs):
            continue
        try:
            s = py.read_text(encoding="utf-8")
        except Exception:
            continue
        # t("...")
        for m in re.finditer(r'\bt\(\s*"([a-zA-Z0-9_.]+)"', s):
            keys.add(m.group(1))
        for m in re.finditer(r"\bt\(\s*'([a-zA-Z0-9_.]+)'", s):
            keys.add(m.group(1))
        # t(f"...{var}...") — фрагменты. Собираем префикс.
        for m in re.finditer(r'\bt\(\s*f"([a-zA-Z0-9_.]+)\{', s):
            keys.add(m.group(1) + "*")
    # Убрать динамические (с *) — их нельзя проверить статически
    return {k for k in keys if "*" not in k}


def collect_dynamic_prefixes() -> set[str]:
    """Собрать префиксы для f-строк t(f"...{x}")."""
    prefixes = set()
    skip_dirs = {"__pycache__", ".venv", "venv", "backups", "data", ".git"}
    for py in ROOT.rglob("*.py"):
        if any(p in py.parts for p in skip_dirs):
            continue
        try:
            s = py.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in re.finditer(r'\bt\(\s*f"([a-zA-Z0-9_.]+)\{', s):
            prefixes.add(m.group(1))
        for m in re.finditer(r"\bt\(\s*f'([a-zA-Z0-9_.]+)\{", s):
            prefixes.add(m.group(1))
    return prefixes


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FATAL: {path}: {e}")
        return {}


def main():
    print("=== LOCALES CHECK ===\n")

    en = load_json(ROOT / "locales/en.json")
    ru = load_json(ROOT / "locales/ru.json")
    print(f"en.json: {len(en)} keys")
    print(f"ru.json: {len(ru)} keys\n")

    keys = collect_keys_from_code()
    prefixes = collect_dynamic_prefixes()
    # Дополнительные статические префиксы (для f-строк, которые не поймались regex)
    prefixes |= {"clan.role.", "story.giver_intro.", "maze.section.", "key.", "item.", "weather.", "world_events."}
    # Дополнительные статические префиксы (для f-строк, которые не поймались regex)
    prefixes |= {"clan.role.", "story.giver_intro.", "maze.section.", "key.", "item."}

    # Пропустить ключи, которые начинаются с префиксов (f-строки)
    def is_dynamic(k: str) -> bool:
        return any(k.startswith(p) for p in prefixes)

    # Проверить missing в en/ru
    # Игнорировать ложные (из докстрингов, тестов)
    IGNORE = {"key"}
    missing_en = sorted(k for k in keys if k not in en and not is_dynamic(k) and k not in IGNORE)
    missing_ru = sorted(k for k in keys if k not in ru and not is_dynamic(k) and k not in IGNORE)

    print(f"Ключей в коде (статических): {len(keys)}")
    print(f"Динамических префиксов (f-строк): {len(prefixes)}")
    for p in sorted(prefixes):
        print(f"  {p}*")

    print(f"\nMissing in en.json: {len(missing_en)}")
    for k in missing_en:
        print(f"  {k}")

    print(f"\nMissing in ru.json: {len(missing_ru)}")
    for k in missing_ru:
        print(f"  {k}")

    # Ключи в en, но не в ru (и наоборот)
    only_en = sorted(k for k in en if k not in ru)
    only_ru = sorted(k for k in ru if k not in en)
    print(f"\nOnly in en.json: {len(only_en)}")
    for k in only_en[:10]:
        print(f"  {k}")
    print(f"\nOnly in ru.json: {len(only_ru)}")
    for k in only_ru[:10]:
        print(f"  {k}")

    total = len(missing_en) + len(missing_ru)
    print(f"\n=== RESULT: {total} missing ===")
    sys.exit(0 if total == 0 else 1)


if __name__ == "__main__":
    main()
