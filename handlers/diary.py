# handlers/diary.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from db.players import get_player, get_lang
from db.connection import get_conn


async def cmd_diary(message: Message):
    """/diary — показать дневник. /diary <текст> — добавить запись."""
    user_id = message.from_user.id
    lang = get_lang(user_id)
    player = get_player(user_id)
    if not player:
        await message.answer(t("start.need_start", lang))
        return

    parts = message.text.split(maxsplit=1)

    # Добавить запись
    if len(parts) >= 2:
        text = parts[1].strip()
        if len(text) > 500:
            await message.answer(t("diary.too_long", lang))
            return
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO player_diary (user_id, text) VALUES (?, ?)", (user_id, text))
            conn.commit()
        finally:
            conn.close()
        await message.answer(t("diary.added", lang))
        return

    # Показать
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT text, created_at FROM player_diary
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 30
        """, (user_id,))
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        await message.answer(t("diary.empty", lang))
        return

    lines = [f"📖 <b>{t('diary.header', lang)}</b>\n"]
    for text, created_at in reversed(rows):
        d = str(created_at)[:16]
        lines.append(f"<i>{d}</i>\n{text}\n")
    await message.answer("\n".join(lines))

async def on_diary_show(callback):
    """diary:show:<session> — показать личный дневник из кнопки."""
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

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT text, created_at FROM player_diary
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 30
        """, (user_id,))
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        text = t("diary.empty", lang)
    else:
        lines = [f"📖 <b>{t('diary.header', lang)}</b>\n"]
        for row_text, created_at in reversed(rows):
            d = str(created_at)[:16]
            lines.append(f"<i>{d}</i>\n{row_text}\n")
        text = "\n".join(lines)

    session = player.get("current_session", "")
    s = f":{session}" if session else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()

