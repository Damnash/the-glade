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

    # 1) NPC (если есть) — сверху, по 2 в ряд
    from core.daycycle import is_night
    npcs = get_npcs_in_location(location, is_night=is_night())
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

    # 2) Действия (или статус, если занят)
    if status in ("sleeping", "working"):
        from core.time_utils import seconds_until
        work_done = False
        if status == "working":
            left = seconds_until(player.get("work_ends_at"))
            if left <= 0:
                work_done = True

        if work_done:
            rows.append([
                InlineKeyboardButton(text=t("btn.collect", lang),
                                      callback_data=f"work:collect{s}"),
            ])
        else:
            rows.append([
                InlineKeyboardButton(text=t("btn.status_busy", lang),
                                      callback_data=f"noop{s}"),
            ])
    else:
        rows.append([
            InlineKeyboardButton(text=t("nav.move", lang), callback_data=f"nav:move{s}"),
            InlineKeyboardButton(text=t("nav.todo", lang), callback_data=f"nav:todo{s}"),
        ])

    # 2.5) Инвентарь / Статы
    rows.append([
        InlineKeyboardButton(text=t("btn.inventory", lang), callback_data=f"nav:inv{s}"),
        InlineKeyboardButton(text=t("btn.stats", lang),     callback_data=f"nav:stats{s}"),
    ])

    # 3) Информация
    rows.append([
        InlineKeyboardButton(text=t("map.btn_open", lang),   callback_data=f"map:list{s}"),
        InlineKeyboardButton(text=t("radio.btn_open", lang), callback_data=f"radio:menu{s}"),
    ])

    # 4) Сервис (Ещё + Помощь)
    rows.append([
        InlineKeyboardButton(text=t("more.btn", lang),  callback_data=f"nav:more{s}"),
        InlineKeyboardButton(text=t("nav.help", lang), callback_data=f"help:main{s}"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
