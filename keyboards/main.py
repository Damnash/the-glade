# keyboards/main.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from content.npcs import get_npcs_in_location


def main_keyboard(lang: str, context: dict, session: str = "") -> InlineKeyboardMarkup:
    """Главный экран локации с session."""
    player = context.get("player", {})
    location = player.get("location", "center")
    status = player.get("status", "active")

    s = f":{session}" if session else ""

    rows = []

    # NPC
    npcs = get_npcs_in_location(location)
    if npcs:
        npc_buttons = []
        for npc in npcs:
            npc_buttons.append(
                InlineKeyboardButton(
                    text=t("nav.talk_to", lang, npc=t(npc["name_key"], lang)),
                    callback_data=f"npc:talk:{npc['key']}{s}",
                )
            )
        for i in range(0, len(npc_buttons), 2):
            rows.append(npc_buttons[i:i + 2])

    # Основные действия
    if status in ("sleeping", "working"):
        # Если работа закончилась — кнопка "Забрать", иначе "Занят" (popup)
        from core.time_utils import seconds_until
        work_done = False
        if status == "working":
            left = seconds_until(player.get("work_ends_at"))
            if left <= 0:
                work_done = True

        if work_done:
            rows.append([
                InlineKeyboardButton(
                    text=t("btn.collect", lang),
                    callback_data=f"work:collect{s}",
                ),
            ])
        else:
            rows.append([
                InlineKeyboardButton(
                    text=t("btn.status_busy", lang),
                    callback_data=f"noop{s}",
                ),
            ])
    else:
        rows.append([
            InlineKeyboardButton(text=t("nav.move", lang), callback_data=f"nav:move{s}"),
            InlineKeyboardButton(text=t("nav.todo", lang), callback_data=f"nav:todo{s}"),
        ])

    rows.append([
        InlineKeyboardButton(text=t("btn.stats", lang),     callback_data=f"nav:stats{s}"),
        InlineKeyboardButton(text=t("btn.inventory", lang), callback_data=f"nav:inv{s}"),
    ])

    rows.append([
        InlineKeyboardButton(text=t("map.btn_open", lang),   callback_data=f"map:list{s}"),
        InlineKeyboardButton(text=t("radio.btn_open", lang), callback_data=f"radio:menu{s}"),
    ])

    rows.append([
        InlineKeyboardButton(text="⚔️ PvP", callback_data=f"pvp:flag{s}"),
    ])

    rows.append([
        InlineKeyboardButton(text=t("nav.help", lang), callback_data=f"help:main{s}"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
