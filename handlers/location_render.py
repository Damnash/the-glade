# handlers/location_render.py

from core.i18n import t
from core.daycycle import get_current_phase
from content.locations import LOCATIONS
from content.hints import HINTS
from content.npcs import get_npcs_in_location
from db.players import players_in_location


def render_location_text(lang: str, loc_key: str, viewer_id: int) -> str:
    """Текст локации с учётом времени суток."""
    name = t(f"loc.{loc_key}.name", lang)

    # Описание — по фазе дня, если есть; иначе обычное
    phase = get_current_phase()
    phase_key = f"loc.{loc_key}.desc.{phase}"
    desc = t(phase_key, lang)

    # Если ключа нет — обычное описание
    if desc == phase_key:
        desc = t(f"loc.{loc_key}.desc", lang)

    others = players_in_location(loc_key, exclude_id=viewer_id)
    if others:
        names = ", ".join(p["display_name"] or p["username"] for p in others)
    else:
        names = t("look.empty", lang)

    parts = [
        t("look.header", lang, name=name),
        desc,
    ]

    # Звуковое описание (атмосфера) — по фазе дня
    try:
        import random
        from content.loc_sounds import LOC_SOUNDS, LOC_SOUNDS_NIGHT
        from core.daycycle import is_night
        pool = LOC_SOUNDS_NIGHT if is_night() else LOC_SOUNDS
        sounds = pool.get(loc_key)
        if sounds:
            parts.append(f"<i>{random.choice(sounds)}</i>")
    except Exception:
        pass

    # Погода
    try:
        from services.weather import get_current_weather
        weather_key = get_current_weather()
        weather_line = t(f"weather.{weather_key}.line", lang)
        if weather_line and weather_line != f"weather.{weather_key}.line":
            parts.append(f"<i>{weather_line}</i>")
    except Exception:
        pass

    parts.append(t("look.players", lang, players=names))

    # NPC в локации
    from core.daycycle import is_night
    npcs = get_npcs_in_location(loc_key, is_night=is_night())
    if npcs:
        npc_names = ", ".join(t(n["name_key"], lang) for n in npcs)
        parts.append(t("look.npcs", lang, npcs=npc_names))

    # Подсказка
    hint_key = HINTS.get(loc_key)
    if hint_key:
        hint_text = t(hint_key, lang)
        if hint_text != hint_key:
            parts.append(f"💡 {hint_text}")

    return "\n\n".join(parts)


# ============ Универсальный возврат ============

async def send_current_context(message, user_id: int = None):
    """
    Показать текущий контекст игрока (локация или секция).
    Используется после команд, чтобы игрок не терял меню.
    """
    if user_id is None:
        user_id = message.from_user.id
    from db.players import get_player
    from keyboards.main import main_keyboard

    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    # Если в Лабиринте — показать секцию
    if player.get("maze_layer", 0) > 0 and player.get("maze_section"):
        from handlers.maze_section import show_section
        # show_section ожидает callback, но можем использовать message
        # Упрощённый вариант — отправить через inline
        await _send_maze_section_message(message, player, lang)
    else:
        # Глэйд — показать локацию
        text = render_location_text(lang, player["location"], user_id)
        kb = main_keyboard(lang, {"player": player})
        await message.answer(text, reply_markup=kb)


async def _send_maze_section_message(message, player, lang):
    """Показать секцию Лабиринта через message."""
    from core.maze_current import get_current_season
    from db.maze_map import get_section
    from core.i18n import t
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

    text = "🌀 <b>" + section['name'] + "</b>\n\n" + desc + "\n\n" + stats

    # Простые кнопки — только вернуться в локацию
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t("nav.back", lang),
            callback_data="maze:back",
        )
    ]])

    await message.answer(text, reply_markup=kb)
