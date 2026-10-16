# core/commands.py

from core.i18n import get_all_translations


def command_aliases(key: str, fallback: list[str] | None = None) -> list[str]:
    """
    Возвращает список алиасов команды со всех языков.
    key: например "commands.go"
    """
    seen = set()
    result = []

    for lang_data in get_all_translations().values():
        aliases = lang_data.get(key)
        if not aliases:
            continue
        if isinstance(aliases, str):
            aliases = [aliases]
        for a in aliases:
            a = a.strip().lower()
            if a and a not in seen:
                seen.add(a)
                result.append(a)

    if not result and fallback:
        result = fallback

    if not result:
        raise RuntimeError(
            f"No aliases found for '{key}'. "
            f"Did you call load_locales() before registering commands?"
        )

    return result