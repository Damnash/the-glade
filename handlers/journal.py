# handlers/journal.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from db.players import get_player, get_lang
from services.event_log import get_recent_events


async def cmd_journal(message: Message):
    """/journal — история событий (чат, радио, клан, бой, находки)."""
    user_id = message.from_user.id
    lang = get_lang(user_id)
    player = get_player(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    events = get_recent_events(user_id, limit=50)
    if not events:
        await message.answer(t("journal.empty", lang))
        return

    lines = [f"📖 <b>{t('journal.header', lang)}</b>\n"]
    for e in events:
        lines.append(e["text"])

    await message.answer("\n".join(lines))

async def on_journal_show(callback):
    """Показать дневник (из кнопки)."""
    from core.bot_helpers import check_session, edit_main, make_bot
    from core.i18n import t
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    events = get_recent_events(user_id, limit=50)

    if not events:
        text = t("journal.empty", lang)
    else:
        lines = [f"📖 <b>{t('journal.header', lang)}</b>\n"]
        for e in events:
            lines.append(e["text"])
        text = "\n".join(lines)

    session = player.get("current_session", "")
    s = f":{session}" if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}")
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()

