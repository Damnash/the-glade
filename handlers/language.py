# handlers/language.py

from aiogram.filters import Command
from aiogram.types import Message

from config import SUPPORTED_LANGS
from core.i18n import t
from db.players import get_player, get_lang, update_language


async def cmd_language(message: Message):
    """/язык — показать текущий. /язык <en|ru> — сменить."""
    user_id = message.from_user.id
    current = get_lang(user_id)

    args = message.text.split(maxsplit=1)

    # Без аргумента — показать текущий и вернуть локацию
    if len(args) < 2:
        await message.answer(t("lang.current", current))
        await _show_current_context(message, user_id, current)
        return

    code = args[1].strip().lower()[:2]
    if code not in SUPPORTED_LANGS:
        await message.answer(t("lang.invalid", current))
        await _show_current_context(message, user_id, current)
        return

    # Меняем язык
    update_language(user_id, code)
    await message.answer(t("lang.changed", code))

    # Показываем локацию на новом языке
    await _show_current_context(message, user_id, code)


async def _show_current_context(message: Message, user_id: int, lang: str):
    """Показать текущий контекст: локацию или секцию Лабиринта."""
    player = get_player(user_id)
    if not player:
        return

    if player.get("maze_layer", 0) > 0 and player.get("maze_section"):
        await _show_maze_section_message(message, player, lang)
    else:
        await _show_glade_location(message, player, lang)


async def _show_glade_location(message: Message, player: dict, lang: str):
    """Показать текущую локацию Глэййда."""
    from handlers.nav_callback import render_location_text
    from keyboards.main import main_keyboard

    text = render_location_text(lang, player["location"], message.from_user.id)
    kb = main_keyboard(lang, {"player": player})
    await message.answer(text, reply_markup=kb)


async def _show_maze_section_message(message: Message, player: dict, lang: str):
    """Показать текущую секцию Лабиринта (для message, не callback)."""
    from core.maze_current import get_current_season
    from db.maze_map import get_section
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    layer = player.get("maze_layer", 1)
    section_id = player.get("maze_section")
    season = get_current_season()

    section = get_section(season, layer, section_id)
    if not section:
        return

    desc = t(f"maze.section.{section['type']}", lang)
    stats = t("maze.stats_line", lang,
              hp=player["hp"], energy=player["energy"],
              sanity=player.get("sanity", 100),
              food=player["food"], water=player["water"],
              max_food=player.get("max_food", 10),
              max_water=player.get("max_water", 5),
              tokens=player.get("tokens", 0))

    text = f"🌀 <b>{section['name']}</b>\n\n{desc}\n\n{stats}"

    # Кнопки
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

    # Выходы
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

    # Выход в Глэйд — только в 1-м кольце
    if section["ring"] == 1:
        rows.append([
            InlineKeyboardButton(
                text=t("maze.btn_exit_to_glade", lang),
                callback_data="maze:exit",
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer(text, reply_markup=kb)
