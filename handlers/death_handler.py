# handlers/death_handler.py

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from services.death import random_death_message, random_global_death_message
from core.bot_helpers import make_bot


async def show_death_message(callback: CallbackQuery, user_id: int, lang: str):
    """Показать сообщение о смерти."""
    from db.players import get_player
    player = get_player(user_id) or {}
    personal_msg = random_death_message(lang)

    text = (
        f"💀 <b>{t('death.title', lang)}</b>\n\n"
        f"<i>{personal_msg}</i>\n\n"
        f"{t('death.respawn_info', lang)}"
    )

    session = player.get("current_session", "")
    s = f":{session}" if session else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t("death.btn_respawn", lang),
            callback_data=f"nav:back{s}",
        )
    ]])

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)

    # Уведомление всем
    from aiogram import Bot
    from config import BOT_TOKEN
    bot = make_bot()
    try:
        from db.connection import get_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id, language FROM players WHERE user_id != ?", (user_id,))
        all_players = cur.fetchall()
        conn.close()

        for uid, ulang in all_players:
            global_msg = random_global_death_message(ulang)
            try:
                await bot.send_message(chat_id=uid, text=global_msg)
            except Exception:
                pass
    finally:
        await bot.session.close()


async def cmd_death_test(callback: CallbackQuery):
    """Тест смерти (для отладки)."""
    user_id = callback.from_user.id
    from db.players import get_player
    player = get_player(user_id)
    if player:
        await show_death_message(callback, user_id, player["language"])
