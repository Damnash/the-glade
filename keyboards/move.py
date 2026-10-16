# keyboards/move.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from content.locations import LOCATIONS


def move_keyboard(lang: str, location: str, session: str = "") -> InlineKeyboardMarkup:
    """Меню перемещения."""
    rows = []
    s = f":{session}" if session else ""

    exits = LOCATIONS[location]["exits"]
    buttons = [
        InlineKeyboardButton(
            text=t(f"loc.{e}.name", lang),
            callback_data=f"go:{e}{s}",
        )
        for e in exits
    ]

    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i + 2])

    rows.append([
        InlineKeyboardButton(
            text=t("nav.back", lang),
            callback_data=f"nav:back{s}",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
