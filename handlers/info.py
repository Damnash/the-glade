# handlers/info.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from content.locations import LOCATIONS
from db.players import get_player, get_lang, players_in_location, find_by_name


async def cmd_who(message: Message):
    lang = get_lang(message.from_user.id)
    player = get_player(message.from_user.id)
    if not player:
        await message.answer(t("start.need_start", lang))
        return

    others = players_in_location(player["location"], exclude_id=message.from_user.id)
    if not others:
        await message.answer(t("who.header", lang) + "\n\n" + t("who.empty", lang))
        return

    lines = [t("who.header", lang), ""]
    for p in others:
        status = t(f"status.{p['status']}", lang)
        name = p["display_name"] or p["username"]
        # Титул (если есть)
        try:
            from services.titles import get_player_title_display
            t_disp = get_player_title_display(p["user_id"], lang)
            if t_disp:
                name = f"{name} {t_disp}"
        except Exception:
            pass
        lines.append(t("who.line", lang, name=name, status=status))
    await message.answer("\n".join(lines))


async def cmd_where(message: Message):
    lang = get_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(t("where.no_args", lang))
        return

    target = find_by_name(args[1])
    if not target:
        await message.answer(t("where.not_found", lang))
        return

    loc_name = t(f"loc.{target['location']}.name", lang)
    name = target["display_name"] or target["username"]
    await message.answer(t("where.result", lang, name=name, location=loc_name))