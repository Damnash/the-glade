# services/maze_moves_handlers.py
#
# Обработчики переходов в Лабиринте (v1).
#
# Игрок делает МГНОВЕННЫЙ переход из секции в секцию.
# Таймер вылазки 10 минут — если истёк, игрок погибает.

from aiogram.types import CallbackQuery

from core.i18n import t
from core.time_utils import humanize_seconds
from db.players import get_player
from core.bot_helpers import make_bot


async def on_go(callback: CallbackQuery):
    """
    Мгновенный переход в новую секцию.
    Формат callback_data: maze:go:section_id:session
    """
    from core.bot_helpers import check_session, refresh_main
    from services.maze_runs import move_in_run, check_timer, end_run
    from services.death import die_in_maze
    from handlers.death_handler import show_death_message

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    target = parts[2]

    # 1. Проверка таймера
    timer = check_timer(user_id)
    if timer["has_run"] and timer["expired"]:
        # Таймер истёк — смерть
        try:
            die_in_maze(user_id, lang=lang)
        except Exception:
            pass
        end_run(user_id)
        await show_death_message(callback, user_id, lang)
        return

    # 2. Переход
    result = move_in_run(user_id, target)

    if not result["ok"]:
        reason = result["reason"]

        # Recovery: если maze_runs нет, а игрок "в Лабиринте" —
        # принудительно вытаскиваем в Глэйд через try_exit_run.
        if reason == "no_run":
            from services.maze_runs import try_exit_run
            exit_result = try_exit_run(user_id)
            if exit_result.get("ok"):
                await callback.answer(t("maze.returned_short", lang))
                from handlers.nav_callback import show_main
                await show_main(callback)
                return
            # если не удалось — общий popup
            await callback.answer(t("maze.no_run", lang), show_alert=True)
            return

        key_map = {
            "no_layer": "maze.no_layer",
            "no_section": "maze.no_section",
            "not_adjacent": "maze.not_adjacent",
            "timer_expired": "maze.timer_expired",
        }
        key = key_map.get(reason, "maze.move_error")
        await callback.answer(t(key, lang), show_alert=True)
        return

    # 3. Смерть от голода/жажды во время перехода?
    if result.get("death"):
        try:
            die_in_maze(user_id, lang=lang)
        except Exception:
            pass
        end_run(user_id)
        await show_death_message(callback, user_id, lang)
        return

    # 4. Рендер новой секции
    from handlers.maze_section import show_section
    await show_section(callback, user_id, player["maze_layer"], result["current_section"])


async def on_exit(callback: CallbackQuery):
    """
    Попытка выхода из Лабиринта.
    Формат: maze:exit:session
    """
    from core.bot_helpers import check_session, refresh_main
    from services.maze_runs import try_exit_run

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    result = try_exit_run(user_id)

    if not result["ok"]:
        reason = result.get("reason")
        if reason == "not_at_entry":
            depth = result.get("depth", "?")
            await callback.answer(
                t("maze.exit_not_at_entry", lang, depth=depth),
                show_alert=True,
            )
        else:
            await callback.answer(t("maze.exit_error", lang), show_alert=True)
        return

    # Успех — вернулись в Глэйд
    await callback.answer(t("maze.returned_short", lang))

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()
