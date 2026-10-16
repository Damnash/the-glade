# handlers/movement.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from content.locations import LOCATIONS
from content.hints import HINTS
from db.players import get_player, get_lang, players_in_location
from services.movement import move, MoveError


def render_location(lang: str, loc_key: str, viewer_id: int) -> str:
    name = t(f"loc.{loc_key}.name", lang)
    desc = t(f"loc.{loc_key}.desc", lang)
    exits = ", ".join(
        t(f"loc.{e}.name", lang) for e in LOCATIONS[loc_key]["exits"]
    )
    others = players_in_location(loc_key, exclude_id=viewer_id)
    if others:
        names = ", ".join(p["display_name"] or p["username"] for p in others)
    else:
        names = t("look.empty", lang)

    parts = [
        t("look.header", lang, name=name),
        desc,
        t("look.exits", lang, exits=exits),
        t("look.players", lang, players=names),
    ]

    # Подсказка — добавляем ТОЛЬКО если есть ключ
    hint_key = HINTS.get(loc_key)
    if hint_key:
        parts.append(f"💡 {t(hint_key, lang)}")

    return "\n\n".join(parts)


async def cmd_look(message: Message):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer(t("start.need_start", "en"))
        return
    lang = player["language"]
    text = render_location(lang, player["location"], message.from_user.id)
    await message.answer(text)


async def cmd_go(message: Message):
    lang = get_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(t("move.no_args", lang))
        return

    try:
        target = move(message.from_user.id, args[1])
    except MoveError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    text = render_location(lang, target, message.from_user.id)
    await message.answer(text)