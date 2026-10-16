# handlers/maze_callback.py

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from core.maze_current import get_current_season, get_layers_unlocked
from core.maze_generator import generate_layer
from db.maze_map import save_layer, load_layer, get_section
from db.players import get_player, update_player_fields
from services.maze import enter_maze, exit_maze, check_gear, MazeError


# ============ Вход в Лабиринт ============

def format_problems(problems: dict, lang: str) -> str:
    icons = {
        "hp": "❤️", "energy": "⚡", "food": "🍞",
        "water": "💧", "knife": "🔪", "torch": "🔥", "rope": "🪢",
    }
    lines = []
    for key, data in problems.items():
        icon = icons.get(key, "•")
        lines.append(f"  {icon} {data['have']}/{data['need']}")
    return "\n".join(lines)


def enter_anyway_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t("maze.btn_enter_anyway", lang),
            callback_data="raid:enter_force",
        ),
        InlineKeyboardButton(
            text=t("nav.back", lang),
            callback_data="nav:back",
        ),
    ]])


async def on_enter(callback: CallbackQuery):
    """Проверка снаряжения перед входом."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    problems = check_gear(user_id)
    if "error" in problems:
        await callback.answer(t("start.need_start", lang), show_alert=True)
        return

    if problems:
        text = t("maze.warning", lang) + "\n\n"
        text += format_problems(problems, lang)
        text += "\n\n" + t("maze.enter_anyway", lang)

        try:
            await callback.message.edit_text(text, reply_markup=enter_anyway_keyboard(lang))
        except Exception:
            await callback.message.answer(text, reply_markup=enter_anyway_keyboard(lang))
        await callback.answer()
        return

    await _do_enter(callback, user_id, lang)


async def on_enter_force(callback: CallbackQuery):
    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]
    await _do_enter(callback, user_id, lang)


async def _do_enter(callback: CallbackQuery, user_id: int, lang: str):
    """Реальный вход в Лабиринт."""
    player = get_player(user_id)
    season = get_current_season()

    # Слой 1 должен существовать
    layer_data = load_layer(season, 1)
    if not layer_data:
        layer_data = generate_layer(1, seed=season)
        save_layer(season, 1, layer_data)

    # Спавним ключи по дням
    from services.keys import ensure_keys_spawned
    ensure_keys_spawned(season)

    try:
        section_id = enter_maze(user_id, player["location"])
    except MazeError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    update_player_fields(user_id, {
        "maze_layer": 1,
        "maze_section": section_id,
    })

    await _show_section(callback, user_id, 1, section_id)


# ============ Алиас на новую реализацию ============

async def _show_section(callback, user_id: int, layer: int, section_id: str):
    """Алиас на handlers.maze_section."""
    from handlers.maze_section import show_section
    await show_section(callback, user_id, layer, section_id)


# ============ Перемещение ============

# ============ Осмотр ============

async def on_look(callback: CallbackQuery):
    """Осмотреться в секции — фрагмент или событие."""
    from services.maze import roll_event
    from services.maze_fragments import try_find_fragment

    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    parts = callback.data.split(":", 2)
    if len(parts) < 3:
        await callback.answer("Invalid.", show_alert=True)
        return

    section_id = parts[2]
    layer = player.get("maze_layer", 1)

    # 0. Проверка ключа
    from services.keys import try_find_key
    key_num = try_find_key(user_id, section_id, layer)
    if key_num:
        key_name = t(f"key.{key_num}.name", lang)
        # Добавить в инвентарь
        from db.inventory import add_item
        add_item(user_id, f"key_{key_num}", 1)
        await callback.answer(t("key.found", lang, name=key_name), show_alert=True)
        await _show_section(callback, user_id, layer, section_id)
        return

    # 1. Фрагмент карты
    if try_find_fragment(user_id, section_id, layer):
        await callback.answer(t("fragment.found", lang), show_alert=True)
        await _show_section(callback, user_id, layer, section_id)
        return

    # 2. Обычное событие
    event = roll_event(section_id, user_id, lang)

    if event is None:
        await callback.answer(t("maze.look.nothing", lang), show_alert=True)
    else:
        await callback.answer(event, show_alert=True)

    await _show_section(callback, user_id, layer, section_id)


# ============ Возврат ============

async def on_return(callback: CallbackQuery):
    """Вернуться в Глэйд."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    try:
        gate = exit_maze(user_id)
    except MazeError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    update_player_fields(user_id, {
        "location": gate,
        "maze_layer": 0,
        "maze_section": None,
    })

    await callback.answer(t("maze.returned_short", lang))

    from handlers.nav_callback import show_main
    await show_main(callback)


# ============ Возврат в секцию ============

async def on_maze_back(callback):
    """Вернуться в текущую секцию Лабиринта."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        await callback.answer("No character.", show_alert=True)
        return

    layer = player.get("maze_layer", 0)
    section_id = player.get("maze_section")

    if layer == 0 or not section_id:
        from handlers.nav_callback import show_main
        await show_main(callback)
        return

    await _show_section(callback, user_id, layer, section_id)


# ============ Подбор предметов ============

async def on_pickup_ground(callback):
    """Подобрать всё с пола."""
    from services.death import pickup_all_items
    from db.players import get_player

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        await callback.answer("No character.", show_alert=True)
        return

    lang = player["language"]
    layer = player.get("maze_layer", 1)
    section_id = player.get("maze_section")

    if not section_id or layer == 0:
        await callback.answer("Not in maze.", show_alert=True)
        return

    result = pickup_all_items(user_id, section_id, layer)

    if result["items"] == 0 and result["maps"] == 0:
        await callback.answer(t("ground.nothing", lang), show_alert=True)
        return

    msg = t("ground.picked", lang, items=result["items"], maps=result["maps"])
    await callback.answer(msg, show_alert=True)

    await _show_section(callback, user_id, layer, section_id)


# ============ Алиасы на handlers/maze_moves_handlers ============

async def on_go(callback):
    from services.maze_moves_handlers import on_go as _on_go
    await _on_go(callback)


async def on_check_move(callback):
    from services.maze_moves_handlers import on_check_move as _on_check_move
    await _on_check_move(callback)


# ============ Алиасы на handlers/maze_moves_handlers ============

async def on_go(callback):
    from services.maze_moves_handlers import on_go as _on_go
    await _on_go(callback)


async def on_check_move(callback):
    from services.maze_moves_handlers import on_check_move as _on_check_move
    await _on_check_move(callback)


# ============ Компас и лечение ============

async def on_compass(callback):
    """Компас — показать путь."""
    from core.bot_helpers import check_session, edit_main, make_bot
    from services.compass import get_compass_hint
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # Компас только у Инженера
    if player.get("profession") != "engineer":
        await callback.answer(t("compass.only_engineer", lang), show_alert=True)
        return

    hint = get_compass_hint(user_id, lang)

    # Просто popup
    await callback.answer(hint, show_alert=True)


async def on_heal(callback):
    """Лечиться бинтом."""
    from core.bot_helpers import check_session, refresh_main
    from services.medic import heal_self
    from core.bot_helpers import make_bot

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    try:
        result = heal_self(user_id)
    except ValueError as e:
        await callback.answer(t(str(e), lang), show_alert=True)
        return

    await callback.answer(
        t("medic.healed", lang, hp=result["hp"], healed=result["healed"]),
        show_alert=True,
    )

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()
