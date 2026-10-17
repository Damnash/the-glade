# handlers/map.py

from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from core.maze_current import get_current_season, get_layers_unlocked
from db.maze_state import get_map_status
from db.players import get_player, get_lang


def render_map(lang: str, season: int, layer: int) -> str:
    """Рендер карты слоя."""
    status = get_map_status(season, layer)

    if not status["sections"]:
        return t("map.empty", lang)

    lines = [
        f"🗺️ <b>{t('map.title', lang)}</b>",
        f"<i>{t('map.subtitle', lang, layer=layer)}</i>",
        "",
        t("map.progress", lang, d=status["discovered"], t=status["total"]),
        "",
    ]

    # Группируем по крыльям
    by_wing = {"N": [], "S": [], "W": [], "E": [], "C": []}
    for sid, data in status["sections"].items():
        by_wing[data["wing"]].append((sid, data["discovered"]))

    # Крылья
    for wing in ["N", "S", "W", "E"]:
        sorted_sections = sorted(by_wing[wing])
        cells = ["🟢" if disc else "⬛" for _, disc in sorted_sections]
        lines.append("  ".join(cells))

    # Центр — отдельной строкой, с отступом
    center_cells = ["🟢" if disc else "⬛" for _, disc in sorted(by_wing["C"])]
    if center_cells:
        lines.append("      " + "  ".join(center_cells))

    lines.append("")
    lines.append(t("map.legend", lang))

    return "\n".join(lines)


async def cmd_map(message: Message):
    """/карта — открыть карту."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    season = get_current_season()
    layers = get_layers_unlocked(season)

    text = render_map(lang, season, 1)

    # Кнопки переключения слоёв (если больше 1)
    if layers > 1:
        buttons = []
        for i in range(1, layers + 1):
            buttons.append(InlineKeyboardButton(
                text=t("map.layer_btn", lang, n=i),
                callback_data=f"map:layer:{i}",
            ))
        kb = InlineKeyboardMarkup(inline_keyboard=[buttons])
        await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text)


async def on_map_open(callback: CallbackQuery):
    """Открыть карту из кнопки."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    season = get_current_season()
    layers = get_layers_unlocked(season)

    text = render_map(lang, season, 1)

    rows = []
    if layers > 1:
        layer_buttons = []
        for i in range(1, layers + 1):
            layer_buttons.append(InlineKeyboardButton(
                text=t("map.layer_btn", lang, n=i),
                callback_data=f"map:layer:{i}",
            ))
        rows.append(layer_buttons)

    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="nav:back")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    from core.bot_helpers import edit_main, make_bot

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_map_layer(callback: CallbackQuery):
    """Переключить слой карты."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    layer = int(callback.data.split(":")[2])
    season = get_current_season()
    layers = get_layers_unlocked(season)

    text = render_map(lang, season, layer)

    rows = []
    if layers > 1:
        layer_buttons = []
        for i in range(1, layers + 1):
            layer_buttons.append(InlineKeyboardButton(
                text=t("map.layer_btn", lang, n=i),
                callback_data=f"map:layer:{i}",
            ))
        rows.append(layer_buttons)

    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="nav:back")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    from core.bot_helpers import edit_main, make_bot

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()
