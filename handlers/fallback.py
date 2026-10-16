# handlers/fallback.py

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from db.players import get_player, get_lang


# Популярные команды без слэша → слэш
AUTOCOMMANDS = {
    "помощь": "/помощь",
    "help": "/help",
    "статы": "/статы",
    "stats": "/stats",
    "инвентарь": "/инвентарь",
    "inventory": "/inventory",
    "карты": "/карты",
    "maps": "/maps",
    "ключи": "/ключи",
    "keys": "/keys",
    "клан": "/клан",
    "clan": "/clan",
    "топ": "/топ",
    "top": "/top",
    "звания": "/звания",
    "achievements": "/achievements",
    "сезон": "/сезон",
    "season": "/season",
    "время": "/время",
    "time": "/time",
    "рация": "/рация",
    "walkie": "/walkie",
}


async def on_unknown_text(message: Message):
    """Если текст не команда и не FSM — подсказать."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        # Игрок не в игре — показать /start
        await message.answer(t("fallback.need_start", lang))
        return

    text = (message.text or "").strip().lower()

    # Autocommand — если текст похож на команду без слэша
    if text in AUTOCOMMANDS:
        cmd = AUTOCOMMANDS[text]
        await message.answer(
            t("fallback.autocommand", lang, cmd=cmd)
        )
        return

    # Иначе — общая подсказка
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t("fallback.btn_help", lang),
            callback_data="help:main",
        ),
        InlineKeyboardButton(
            text=t("nav.back", lang),
            callback_data="nav:back",
        ),
    ]])

    await message.answer(
        t("fallback.unknown", lang),
        reply_markup=kb,
    )
