# keyboards/actions.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from content.maze import MAZE_ENTRANCES


def actions_keyboard(lang: str, player: dict, session: str = "") -> InlineKeyboardMarkup:
    """Меню «Действия»."""
    rows = []
    s = f":{session}" if session else ""
    loc = player["location"]
    status = player["status"]

    if status == "sleeping":
        rows.append([
            InlineKeyboardButton(text=t("btn.wake", lang), callback_data=f"act:wake{s}"),
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
        ])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if status == "working":
        rows.append([
            InlineKeyboardButton(text=t("btn.collect", lang), callback_data=f"work:collect{s}"),
            InlineKeyboardButton(text=t("nav.back", lang),    callback_data=f"nav:back{s}"),
        ])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    rows.append([
        InlineKeyboardButton(text=t("btn.look", lang),  callback_data=f"act:look{s}"),
        InlineKeyboardButton(text=t("btn.sleep", lang), callback_data=f"act:sleep{s}"),
    ])

    if loc in MAZE_ENTRANCES:
        rows.append([
            InlineKeyboardButton(text=t("btn.raid", lang), callback_data=f"raid:enter{s}"),
        ])

    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
