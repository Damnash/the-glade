# handlers/maze_section.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from core.maze_current import get_current_season
from db.maze_map import get_section
from db.players import get_player

def _get_run_info_text(user_id: int, lang: str) -> str:
    """
    Возвращает строку с таймером и глубиной вылазки.
    Пустая строка, если игрок не в вылазке.
    """
    from core.i18n import t
    from core.time_utils import humanize_seconds
    from services.maze_runs import get_run, check_timer

    run = get_run(user_id)
    if not run:
        return ""

    timer = check_timer(user_id)
    seconds_left = timer.get("seconds_left", 0)

    time_str = humanize_seconds(seconds_left, lang)
    timer_line = t("maze.run_timer_line", lang, time=time_str)

    depth = run.get("depth", 0)
    depth_line = t("maze.run_depth_line", lang, depth=depth)

    if depth > 0:
        return_suffix = t("maze.run_depth_return", lang, depth=depth)
        depth_line += return_suffix

    return f"{timer_line}\n{depth_line}"



async def show_section(callback, user_id: int, layer: int, section_id: str):
    """Показать секцию Лабиринта."""
    player = get_player(user_id)
    if not player:
        await callback.answer("No character.", show_alert=True)
        return

    lang = player["language"]

    # Проверка смерти
    from services.death import check_death
    if check_death(user_id):
        from handlers.death_handler import show_death_message
        await show_death_message(callback, user_id, lang)
        return

    player = get_player(user_id)
    lang = player["language"]

    # Проверка активного боя
    from services.combat import get_active_combat, roll_encounter, start_combat
    from handlers.combat_callback import show_combat

    active = get_active_combat(user_id)
    if active:
        await show_combat(callback, user_id, lang)
        return

    season = get_current_season()
    section = get_section(season, layer, section_id)
    if not section:
        await callback.answer("Section not found.", show_alert=True)
        return

    # Проверка встречи с Гривером
    is_center = (section["type"] == "center")
    monster_type = roll_encounter(section["ring"], is_center=is_center)

    if monster_type:
        start_combat(user_id, monster_type, section_id, layer)
        await show_combat(callback, user_id, lang)
        return

    # Отрисовка
    await _render(callback, player, lang, season, section, layer, section_id)


async def _render(callback, player, lang, season, section, layer, section_id):
    from db.connection import get_conn
    from db.map_items import get_maps_on_ground

    desc = t(f"maze.section.{section['type']}", lang)

    stats = t("maze.stats_line", lang,
              hp=player["hp"], energy=player["energy"],
              sanity=player.get("sanity", 100),
              food=player["food"], water=player["water"],
              max_food=player.get("max_food", 10),
              max_water=player.get("max_water", 5),
              tokens=player.get("tokens", 0))

    maps_ground = get_maps_on_ground(section_id, layer)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT item_key, SUM(quantity) as qty FROM items_on_ground
        WHERE section_id = ? AND layer = ?
        GROUP BY item_key
    """, (section_id, layer))
    items_ground = cur.fetchall()
    conn.close()

    ground_lines = []
    if maps_ground:
        ground_lines.append("🗺️ " + t("ground.maps", lang, n=len(maps_ground)))
    for row in items_ground:
        item_key, qty = row
        name = t(f"item.{item_key}.name", lang)
        ground_lines.append("• " + name + " × " + str(qty))

    ground_text = ""
    if ground_lines:
        ground_text = "\n\n📦 <b>" + t("ground.on_floor", lang) + "</b>\n" + "\n".join(ground_lines)

    text = "🌀 <b>" + section["name"] + "</b>\n\n" + desc + "\n\n" + stats

    # Run info (таймер + глубина)
    run_info = _get_run_info_text(callback.from_user.id, lang)
    if run_info:
        text += "\n\n" + run_info

    text += ground_text

    rows = [
        [
            InlineKeyboardButton(
                text=t("maze.btn_look", lang),
                callback_data=f"maze:look:{section_id}",
            ),
            InlineKeyboardButton(
                text=t("btn.inventory", lang),
                callback_data="nav:inv",
            ),
        ],
        [
            InlineKeyboardButton(
                text=t("map.btn_draw", lang),
                callback_data=f"map:draw:{section_id}",
            ),
            InlineKeyboardButton(
                text=t("map.btn_open", lang),
                callback_data="map:list",
            ),
        ],
    ]

    if maps_ground or items_ground:
        rows.append([
            InlineKeyboardButton(
                text=t("ground.btn_pickup", lang),
                callback_data=f"maze:pickup:{section_id}",
            )
        ])

    for exit_id in section["exits"]:
        exit_section = get_section(season, layer, exit_id)
        if not exit_section:
            continue
        rows.append([
            InlineKeyboardButton(
                text=t("maze.btn_go", lang, name=exit_section["name"]),
                callback_data=f"maze:go:{exit_id}",
            )
        ])

    # Кнопка "К воротам" — всегда. Проверка внутри on_exit.
    rows.append([
        InlineKeyboardButton(
            text=t("maze.btn_exit_to_glade", lang),
            callback_data="maze:exit",
        )
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


# ============ Рендер секции для message ============

def render_section_for_message(player: dict, lang: str, session: str = ""):
    """Возвращает (text, kb) для секции."""
    from core.i18n import t
    from core.maze_current import get_current_season
    from db.maze_map import get_section
    from db.map_items import get_maps_on_ground
    from db.connection import get_conn
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    layer = player.get("maze_layer", 1)
    section_id = player.get("maze_section")
    season = get_current_season()

    section = get_section(season, layer, section_id)
    if not section:
        return ("Section not found.", None)

    s = ":" + session if session else ""

    desc = t("maze.section." + section['type'], lang)
    stats = t("maze.stats_line", lang,
              hp=player["hp"], energy=player["energy"],
              sanity=player.get("sanity", 100),
              food=player["food"], water=player["water"],
              max_food=player.get("max_food", 10),
              max_water=player.get("max_water", 5),
              tokens=player.get("tokens", 0))

    maps_ground = get_maps_on_ground(section_id, layer)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT item_key, SUM(quantity) as qty FROM items_on_ground
        WHERE section_id = ? AND layer = ?
        GROUP BY item_key
    """, (section_id, layer))
    items_ground = cur.fetchall()
    conn.close()

    ground_lines = []
    if maps_ground:
        ground_lines.append("🗺️ " + t("ground.maps", lang, n=len(maps_ground)))
    for row in items_ground:
        item_key, qty = row
        name = t("item." + item_key + ".name", lang)
        ground_lines.append("• " + name + " × " + str(qty))

    ground_text = ""
    if ground_lines:
        ground_text = "\n\n📦 <b>" + t("ground.on_floor", lang) + "</b>\n" + "\n".join(ground_lines)

    text = "🌀 <b>" + section["name"] + "</b>\n\n" + desc + "\n\n" + stats

    # Run info (таймер + глубина)
    run_info = _get_run_info_text(player["user_id"], lang)
    if run_info:
        text += "\n\n" + run_info

    text += ground_text

    rows = [
        [
            InlineKeyboardButton(text=t("maze.btn_look", lang), callback_data="maze:look:" + section_id + s),
            InlineKeyboardButton(text=t("btn.inventory", lang), callback_data="nav:inv" + s),
        ],
        [
            InlineKeyboardButton(text=t("map.btn_draw", lang), callback_data="map:draw:" + section_id + s),
            InlineKeyboardButton(text=t("map.btn_open", lang), callback_data="map:list" + s),
        ],
        [
            InlineKeyboardButton(text=t("maze.btn_compass", lang), callback_data="maze:compass:" + section_id + s),
            InlineKeyboardButton(text=t("maze.btn_heal", lang), callback_data="maze:heal:" + section_id + s),
        ],
    ]

    if maps_ground or items_ground:
        rows.append([
            InlineKeyboardButton(text=t("ground.btn_pickup", lang),
                                  callback_data="maze:pickup:" + section_id + s)
        ])

    for exit_id in section["exits"]:
        exit_section = get_section(season, layer, exit_id)
        if not exit_section:
            continue
        rows.append([
            InlineKeyboardButton(
                text=t("maze.btn_go", lang, name=exit_section["name"]),
                callback_data="maze:go:" + exit_id + s,
            )
        ])

    # Кнопка "К воротам" — всегда
    rows.append([
        InlineKeyboardButton(text=t("maze.btn_exit_to_glade", lang),
                              callback_data="maze:exit" + s)
    ])

    return (text, InlineKeyboardMarkup(inline_keyboard=rows))
