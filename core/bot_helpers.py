# core/bot_helpers.py

import logging
import uuid

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from db.players import get_player, update_player_fields


def new_session() -> str:
    """Сгенерировать новую сессию (8 символов)."""
    return str(uuid.uuid4())[:8]


def check_session(user_id: int, callback_data: str) -> bool:
    """
    Проверить session в callback_data.
    Если у игрока нет session (None) — пропускаем (первый запуск).
    """
    if not callback_data:
        return False

    parts = callback_data.split(":")

    if len(parts) < 2:
        return True

    cb_session = parts[-1]

    player = get_player(user_id)
    if not player:
        return False

    db_session = player.get("current_session")

    # Если в БД нет session — пропускаем
    if not db_session:
        return True

    # Старая кнопка без session
    if cb_session in ("None", "", "none"):
        return True

    return db_session == cb_session


async def edit_main(bot: Bot, user_id: int, text: str, kb=None):
    """
    Всегда удаляет старое сообщение и создаёт новое внизу.
    Гарантирует, что в чате одно главное сообщение.
    """
    player = get_player(user_id)
    msg_id = player.get("main_message_id") if player else None

    # Удаляем старое, если есть
    if msg_id:
        try:
            await bot.delete_message(chat_id=user_id, message_id=msg_id)
            logging.info(f"[edit_main] deleted old msg={msg_id}")
        except Exception as e:
            logging.debug(f"[edit_main] delete failed (ok): {e}")

    # Создаём новое
    try:
        msg = await bot.send_message(user_id, text, reply_markup=kb)
        update_player_fields(user_id, {"main_message_id": msg.message_id})
        logging.info(f"[edit_main] NEW message id={msg.message_id}")
        return msg
    except Exception as e:
        logging.error(f"[edit_main] send failed: {e}")
        return None


async def refresh_main(bot: Bot, user_id: int, new_session_flag: bool = True):
    """
    Обновить главное сообщение.
    Всегда генерирует новый session — старые кнопки инвалидируются.
    """
    from db.players import get_player, update_player_fields
    from keyboards.main import main_keyboard
    from handlers.location_render import render_location_text
    from handlers.maze_section import render_section_for_message
    from services.event_log import get_recent_events
    from core.i18n import t

    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    # Авто-выдача ежедневного квеста (если игрок уже прошёл intro)
    if player.get("intro_done"):
        try:
            from services.daily_quests import ensure_today_quest
            ensure_today_quest(user_id)
        except Exception as e:
            import logging
            logging.error(f"[refresh_main] daily quest error: {e}")

    # Новый session
    session = new_session()
    update_player_fields(user_id, {"current_session": session})
    player["current_session"] = session

    import logging
    logging.info(f"[refresh_main] user={user_id} session={session}")

    # Контекст
    if player.get("maze_layer", 0) > 0 and player.get("maze_section"):
        base_text, kb = render_section_for_message(player, lang, session)
    else:
        base_text = render_location_text(lang, player["location"], user_id)
        kb = main_keyboard(lang, {"player": player}, session)

    # Лог
    events = get_recent_events(user_id, limit=5)
    if events:
        log_lines = []
        for e in events:
            log_lines.append(e["text"])
        header = "\n\n📋 <b>" + t("log.header", lang) + "</b>\n"
        base_text += header + "\n".join(log_lines)

    await edit_main(bot, user_id, base_text, kb)


async def command_reply(message, text: str, kb=None):
    """
    Ответ на команду через edit главного сообщения.
    
    Не генерирует новую session — использует существующую.
    Это значит, что кнопки в kb должны быть созданы с актуальной session.
    """
    from aiogram import Bot
    from config import BOT_TOKEN

    user_id = message.from_user.id
    player = get_player(user_id)
    if not player:
        await message.answer(text, reply_markup=kb)
        return

    # НЕ генерируем новую session — используем существующую
    # (kb была создана с session из БД)

    bot = Bot(token=BOT_TOKEN)
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()

    try:
        await message.delete()
    except Exception:
        pass


def with_session(func):
    """Декоратор: проверяет session в callback_data."""
    from functools import wraps

    @wraps(func)
    async def wrapper(callback, *args, **kwargs):
        from core.i18n import t

        user_id = callback.from_user.id

        if not check_session(user_id, callback.data):
            player = get_player(user_id)
            lang = player["language"] if player else "ru"
            await callback.answer(t("log.stale", lang), show_alert=True)
            return

        return await func(callback, *args, **kwargs)

    return wrapper



def make_bot():
    """Bot с HTML-парсингом по умолчанию."""
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from config import BOT_TOKEN

    return Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
