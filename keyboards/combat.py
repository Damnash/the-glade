# keyboards/combat.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t


def combat_keyboard(lang: str, session: str = "") -> InlineKeyboardMarkup:
    """Кнопки боя."""
    s = f":{session}" if session else ""

    rows = [
        [
            InlineKeyboardButton(text=t("combat.btn_attack", lang), callback_data=f"combat:attack{s}"),
            InlineKeyboardButton(text=t("combat.btn_defend", lang), callback_data=f"combat:defend{s}"),
        ],
        [
            InlineKeyboardButton(text=t("combat.btn_flee", lang), callback_data=f"combat:flee{s}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
