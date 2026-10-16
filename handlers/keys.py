# handlers/keys.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from core.maze_current import get_current_season, get_season_day
from db.players import get_player, get_lang
from services.keys import get_player_keys_with_status
from core.bot_helpers import command_reply


async def cmd_keys(message: Message):
    """/ключи — статус ключей."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    season = get_current_season()
    day = get_season_day(season)

    keys = get_player_keys_with_status(season, user_id)

    lines = [
        f"🔑 <b>{t('keys.title', lang)}</b>",
        f"<i>{t('stats.season_line', lang, season=season, day=day)}</i>",
        "",
    ]

    for k in keys:
        name = t(f"key.{k['num']}.name", lang)
        if k["has"]:
            icon = "✅"
            status = t("keys.status_have", lang)
        elif k["available"]:
            icon = "❓"
            status = t("keys.status_search", lang)
        else:
            icon = "🔒"
            status = t("keys.status_locked", lang, day=k["day"])

        lines.append(f"{icon} {name} — {status}")

    lines.append("")
    lines.append(t("keys.hint", lang))

    await command_reply("\n".join(lines))

    # Вернуть контекст
    from handlers.location_render import send_current_context
    await send_current_context(message, message.from_user.id)

    # command_reply импортируется в шапке файла
