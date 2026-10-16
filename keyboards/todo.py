# keyboards/todo.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t


def todo_keyboard(lang: str, session: str = "") -> InlineKeyboardMarkup:
    """Меню «Что делать?»."""
    s = f":{session}" if session else ""

    rows = [
        [
            InlineKeyboardButton(text=t("btn.actions", lang), callback_data=f"nav:actions{s}"),
            InlineKeyboardButton(text=t("btn.work", lang),    callback_data=f"nav:work{s}"),
            InlineKeyboardButton(text=t("nav.back", lang),    callback_data=f"nav:back{s}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
