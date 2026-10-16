# handlers/maze.py

from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from content.maze import MAZE_ENTRANCES
from db.players import get_player, get_lang
from services.maze import check_gear, enter_maze, exit_maze, MazeError


def enter_anyway_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=t("maze.btn_enter_anyway", lang),
                callback_data="maze_enter",
            ),
        ]]
    )


def format_problems(problems: dict, lang: str) -> str:
    lines = []
    icons = {
        "hp": "❤️", "energy": "⚡", "food": "🍞",
        "water": "💧", "knife": "🔪", "torch": "🔥", "rope": "🪢",
    }
    labels = {
        "hp": "HP", "energy": "Energy", "food": "Food",
        "water": "Water", "knife": "Knife", "torch": "Torch", "rope": "Rope",
    }
    for key, data in problems.items():
        icon = icons.get(key, "•")
        label = labels.get(key, key)
        lines.append(f"  {icon} {label}: {data['have']}/{data['need']}")
    return "\n".join(lines)


async def cmd_raid(message: Message):
    lang = get_lang(message.from_user.id)
    player = get_player(message.from_user.id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    if player["location"] not in MAZE_ENTRANCES:
        await message.answer(t("maze.no_gate", lang))
        return

    problems = check_gear(message.from_user.id)
    if "error" in problems:
        await message.answer(t("start.need_start", lang))
        return

    if problems:
        text = t("maze.warning", lang) + "\n\n"
        text += format_problems(problems, lang)
        text += "\n\n" + t("maze.enter_anyway", lang)
        await message.answer(text, reply_markup=enter_anyway_keyboard(lang))
        return

    try:
        section = enter_maze(message.from_user.id, player["location"])
    except MazeError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(t("maze.entered", lang, section=section))


async def on_enter_anyway(callback: CallbackQuery):
    """Игрок нажал «Войти всё равно»."""
    lang = get_lang(callback.from_user.id)
    player = get_player(callback.from_user.id)

    if not player:
        await callback.answer(t("start.need_start", lang), show_alert=True)
        return

    if player["location"] not in MAZE_ENTRANCES:
        await callback.answer(t("maze.no_gate", lang), show_alert=True)
        return

    try:
        section = enter_maze(callback.from_user.id, player["location"])
    except MazeError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    # Редактируем сообщение — убираем предупреждение
    await callback.message.edit_text(t("maze.entered", lang, section=section))
    await callback.answer()


async def cmd_return(message: Message):
    lang = get_lang(message.from_user.id)
    try:
        gate = exit_maze(message.from_user.id)
    except MazeError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    gate_name = t(f"loc.{gate}.name", lang)
    await message.answer(t("maze.returned", lang, gate=gate_name))