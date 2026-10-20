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

    await command_reply(message, "\n".join(lines))

    # Вернуть контекст
    from handlers.location_render import send_current_context
    await send_current_context(message, message.from_user.id)

    # command_reply импортируется в шапке файла

async def on_keys_show(callback):
    """keys:show:<session> — показать ключи из кнопки."""
    from core.bot_helpers import check_session, edit_main, make_bot
    from core.i18n import t
    from core.maze_current import get_current_season, get_season_day
    from services.keys import get_player_keys_with_status
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
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

    session = player.get("current_session", "")
    s = f":{session}" if session else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, "\n".join(lines), kb)
    finally:
        await bot.session.close()
    await callback.answer()

