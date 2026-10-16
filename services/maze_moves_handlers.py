# services/maze_moves_handlers.py

from aiogram.types import CallbackQuery

from core.i18n import t
from core.maze_current import get_current_season
from core.time_utils import now, parse_dt, humanize_seconds
from db.maze_map import get_section
from db.players import get_player, update_player_fields
from content.maze_transitions import get_transition_text
from services.maze_moves import get_active_move, start_move, complete_move
from core.bot_helpers import make_bot


async def on_go(callback: CallbackQuery):
    """Начать переход."""
    from core.bot_helpers import check_session, edit_main, refresh_main
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from config import BOT_TOKEN
    from aiogram import Bot

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    if get_active_move(user_id):
        await callback.answer("Ты уже в пути.", show_alert=True)
        return

    # maze:go:section_id:session
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    target = parts[2]

    layer = player.get("maze_layer", 1)
    current_section = player.get("maze_section", "")

    if layer == 0:
        await callback.answer(t("maze.not_in_maze", lang), show_alert=True)
        return

    season = get_current_season()
    current = get_section(season, layer, current_section)
    target_section = get_section(season, layer, target)

    if not current or not target_section:
        await callback.answer("Invalid move.", show_alert=True)
        return

    if target not in current["exits"]:
        await callback.answer("You cannot go there.", show_alert=True)
        return

    move = start_move(user_id, current_section, target, layer)
    transition_text = get_transition_text(lang, move["transition_idx"])

    title = t("maze.moving.title", lang)
    time_left = t("maze.moving.time_left", lang, time=humanize_seconds(move["duration"], lang))

    text = "🚶 <b>" + title + "</b>\n\n<i>" + transition_text + "</i>\n\n⏳ " + time_left

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("maze.moving.btn_check", lang),
                              callback_data="maze:check_move:" + target + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_check_move(callback: CallbackQuery):
    """Проверить переход."""
    from core.bot_helpers import check_session, refresh_main
    from config import BOT_TOKEN
    from aiogram import Bot

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # maze:check_move:target:session
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    target = parts[2]

    move = get_active_move(user_id)
    if not move:
        bot = make_bot()
        try:
            await refresh_main(bot, user_id)
        finally:
            await bot.session.close()
        return

    ends = parse_dt(move["ends_at"])
    if ends and now() < ends:
        left = int((ends - now()).total_seconds())
        await callback.answer(t("maze.moving.still", lang, time=humanize_seconds(left, lang)), show_alert=True)
        return

    completed = complete_move(user_id)
    if completed:
        update_player_fields(user_id, {"maze_section": completed["to_section"]})

        # Story tracking
        try:
            from services.story import track_event
            track_event(user_id, "visit_sections")

            # Центр?
            from db.maze_map import get_section
            from core.maze_current import get_current_season
            season = get_current_season()
            new_section = get_section(season, completed["layer"], completed["to_section"])
            if new_section and new_section.get("type") == "center":
                track_event(user_id, "reach_center")
        except Exception:
            pass

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()
    await callback.answer()
