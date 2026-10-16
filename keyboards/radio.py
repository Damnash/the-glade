# keyboards/radio.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t


def radio_menu_keyboard(lang: str, radio: dict, session: str = "") -> InlineKeyboardMarkup:
    """Меню рации."""
    s = f":{session}" if session else ""
    status_icon = "✅" if radio["is_on"] else "❌"

    rows = [
        [
            InlineKeyboardButton(text=t("radio.btn_talk", lang),    callback_data=f"radio:talk{s}"),
            InlineKeyboardButton(text=t("radio.btn_history", lang), callback_data=f"radio:history{s}"),
        ],
        [
            InlineKeyboardButton(text=t("radio.btn_manual", lang),  callback_data=f"radio:manual{s}"),
            InlineKeyboardButton(text=f"{status_icon} {t('radio.btn_toggle', lang)}", callback_data=f"radio:toggle{s}"),
        ],
        [
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
