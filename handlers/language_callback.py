# handlers/language_callback.py

from aiogram import Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from core.bot_helpers import edit_main, refresh_main
from content.locations import START_LOCATION
from db.players import get_player, create_player, update_language, update_player_fields


async def on_language_pick(callback: CallbackQuery, bot: Bot):
    user = callback.from_user
    lang = callback.data.split(":")[1].lower()

    player = get_player(user.id)

    if player:
        # Уже есть — сменить язык
        update_language(user.id, lang)
        await callback.answer(t("lang.changed", lang))
        await refresh_main(bot, user.id)
        return

    # Создаём персонажа
    username = user.username or ""
    display_name = user.first_name or username or "Runner"
    create_player(user.id, username, display_name, lang, START_LOCATION)

    # Личная карта
    from services.maps import create_personal_map
    create_personal_map(user.id, display_name)

    # Ключ 1
    from db.inventory import add_item
    add_item(user.id, "key_1", 1)

    # Щит новичка
    from db.pvp import give_shield
    give_shield(user.id)

    # Сразу первое сообщение intro — редактируем текущее
    text = t("intro.step_dark", lang)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("intro.btn_open_eyes", lang),
                              callback_data="intro:next:step_wake")
    ]])

    # Сохраняем ID текущего сообщения (выбор языка)
    update_player_fields(user.id, {"main_message_id": callback.message.message_id})

    # EDIT существующего сообщения (выбор языка) → Тьма
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        # Fallback — новое
        msg = await callback.message.answer(text, reply_markup=kb)
        update_player_fields(user.id, {"main_message_id": msg.message_id})

    await callback.answer()
