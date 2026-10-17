# keyboards/maps.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t


def maps_list_keyboard(lang: str, maps: list, limit: int, player: dict = None) -> InlineKeyboardMarkup:
    """Список карт игрока."""
    session = ""
    if player:
        session = player.get("current_session", "")
    s = f":{session}" if session else ""

    rows = []
    for m in maps:
        icon = "📜" if m["is_personal"] else "🗺️"
        rows.append([
            InlineKeyboardButton(
                text=f"{icon} {m['name']}",
                callback_data=f"map:open:{m['id']}{s}",
            )
        ])

    if len(maps) < limit:
        rows.append([
            InlineKeyboardButton(
                text=t("map.btn_create", lang),
                callback_data=f"map:create{s}",
            )
        ])

    if player and player.get("maze_layer", 0) > 0:
        rows.append([
            InlineKeyboardButton(
                text=t("map.btn_back_to_maze", lang),
                callback_data=f"maze:back{s}",
            )
        ])
    else:
        rows.append([
            InlineKeyboardButton(
                text=t("nav.back", lang),
                callback_data=f"nav:back{s}",
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def map_view_keyboard(lang: str, map_id: int, is_personal: bool,
                       player: dict = None, session: str = "") -> InlineKeyboardMarkup:
    s = f":{session}" if session else ""

    rows = [
        [
            InlineKeyboardButton(text=t("map.btn_rename", lang),
                                  callback_data=f"map:rename:{map_id}{s}"),
            InlineKeyboardButton(text=t("map.btn_edit_sections", lang),
                                  callback_data=f"map:sections:{map_id}{s}"),
        ],
    ]

    if is_personal:
        if player and player.get("maze_layer", 0) > 0:
            back_btn = InlineKeyboardButton(text=t("map.btn_back_to_maze", lang),
                                             callback_data=f"maze:back{s}")
        else:
            back_btn = InlineKeyboardButton(text=t("map.btn_back_to_list", lang),
                                             callback_data=f"map:list{s}")
        rows.append([
            back_btn,
        ])
    else:
        rows.append([
            InlineKeyboardButton(text=t("map.btn_drop", lang),
                                  callback_data=f"map:drop:{map_id}{s}"),
        ])
        if player and player.get("maze_layer", 0) > 0:
            rows.append([
                InlineKeyboardButton(text=t("map.btn_back_to_maze", lang),
                                      callback_data=f"maze:back{s}")
            ])
        else:
            rows.append([
                InlineKeyboardButton(text=t("map.btn_back_to_list", lang),
                                      callback_data=f"map:list{s}")
            ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def map_sections_keyboard(lang: str, map_id: int, sections: list,
                           player: dict = None, session: str = "") -> InlineKeyboardMarkup:
    s = f":{session}" if session else ""
    rows = []

    buttons = []
    for sec in sections:
        sec_id = sec["section_id"]
        name = sec["custom_name"] or sec_id
        has_note = "📝 " if sec.get("note") else ""
        if len(name) > 15:
            name = name[:14] + "…"
        buttons.append(
            InlineKeyboardButton(
                text=f"{has_note}{name}",
                callback_data=f"map:edit:{map_id}:{sec_id}{s}",
            )
        )

    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i + 2])

    if player and player.get("maze_layer", 0) > 0:
        rows.append([
            InlineKeyboardButton(text=t("map.btn_back_to_maze", lang),
                                  callback_data=f"maze:back{s}")
        ])
    else:
        rows.append([
            InlineKeyboardButton(text=t("map.btn_back_to_map", lang),
                                  callback_data=f"map:open:{map_id}{s}")
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def map_section_edit_keyboard(lang: str, map_id: int, section_id: str,
                                session: str = "") -> InlineKeyboardMarkup:
    """Клавиатура редактирования секции.

    Кнопки rename/note/delete убраны: для них пока нет обработчиков.
    Вернуть, когда появятся on_map_rename_sec / on_map_note / on_map_delete_sec.
    """
    s = f":{session}" if session else ""

    rows = [
        [
            InlineKeyboardButton(text=t("map.btn_back_to_sections", lang),
                                  callback_data=f"map:sections:{map_id}{s}"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="map:list")
    ]])


def back_to_list_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("map.btn_back_to_list", lang), callback_data="map:list")
    ]])
