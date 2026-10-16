# keyboards/npcs.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t


def npc_talk_keyboard(lang: str, npc_key: str, actions: list[str], session: str = "") -> InlineKeyboardMarkup:
    """Меню NPC с session."""
    s = f":{session}" if session else ""
    rows = []

    buttons = [
        InlineKeyboardButton(
            text=t(f"npc.{npc_key}.action.{action}", lang),
            callback_data=f"npc:{npc_key}:{action}{s}",
        )
        for action in actions
    ]

    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i + 2])

    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}")
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
