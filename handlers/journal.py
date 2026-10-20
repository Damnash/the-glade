# handlers/journal.py

from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from db.players import get_player, get_lang
from services.event_log import get_recent_events


# Категории: (ключ, i18n-ключ, event_types)
CATEGORIES = {
    "location": ("journal.cat.location", ["say", "say_received"]),
    "radio":    ("journal.cat.radio",    ["radio", "radio_received", "radio_center"]),
    "whisper":  ("journal.cat.whisper",  ["whisper", "whisper_received"]),
    "clan":     ("journal.cat.clan",     ["clan", "clan_received"]),
    "important":("journal.cat.important",["kill_griever", "found_fragment", "found_key",
                                         "died", "work_done", "attacked_by", "killed", "map_drawn"]),
    "all":      ("journal.cat.all",      None),
}


def _render_menu(lang: str, session: str) -> tuple[str, InlineKeyboardMarkup]:
    s = f":{session}" if session else ""
    text = f"<b>{t('journal.header', lang)}</b>\n\n{t('journal.choose', lang)}"
    rows = []
    # 2 кнопки в ряд
    keys = list(CATEGORIES.keys())
    for i in range(0, len(keys), 2):
        pair = keys[i:i+2]
        rows.append([
            InlineKeyboardButton(
                text=t(CATEGORIES[k][0], lang),
                callback_data=f"journal:show:{k}{s}",
            )
            for k in pair
        ])
    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}")
    ])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _render_category(lang: str, cat: str, session: str) -> tuple[str, InlineKeyboardMarkup]:
    s = f":{session}" if session else ""
    if cat not in CATEGORIES:
        return (t("journal.empty", lang), InlineKeyboardMarkup(inline_keyboard=[]))

    title_key, event_types = CATEGORIES[cat]
    events = get_recent_events(0, limit=50, event_types=event_types)  # user_id подставим ниже
    # (функция ниже передаёт user_id, здесь — заглушка)
    return (title_key, event_types)


async def cmd_journal(message: Message):
    """/journal — меню дневника."""
    user_id = message.from_user.id
    lang = get_lang(user_id)
    player = get_player(user_id)
    if not player:
        await message.answer(t("start.need_start", lang))
        return

    session = player.get("current_session", "")
    text, kb = _render_menu(lang, session)
    await message.answer(text, reply_markup=kb)


async def on_journal_show(callback: CallbackQuery):
    """journal:show:<cat>:session — показать категорию или меню."""
    from core.bot_helpers import check_session, edit_main, make_bot

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    import logging
    logging.info(f"[journal] cb={callback.data!r}")
    parts = callback.data.split(":")
    # journal:show:cat:session
    if len(parts) < 3:
        await callback.answer("Invalid.", show_alert=True)
        return
    cat = parts[2]
    session = player.get("current_session", "")
    s = f":{session}" if session else ""

    if cat == "menu":
        text, kb = _render_menu(lang, session)
    elif cat in CATEGORIES:
        title_key, event_types = CATEGORIES[cat]
        events = get_recent_events(user_id, limit=50, event_types=event_types)
        if not events:
            text = t(title_key, lang) + "\n\n" + t("journal.empty", lang)
        else:
            lines = [f"<b>{t(title_key, lang)}</b>\n"]
            for e in events:
                lines.append(e["text"])
            text = "\n".join(lines)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("journal.btn_back", lang),
                                   callback_data=f"journal:show:menu{s}")],
        ])
    else:
        await callback.answer("Unknown category.", show_alert=True)
        return

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()
