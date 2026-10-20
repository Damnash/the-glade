# handlers/action_callback.py

from aiogram.types import CallbackQuery

from core.i18n import t
from db.players import get_player
from services.sleep import sleep, wake, SleepError
from services.work import start_work, collect_rewards, WorkError
from core.bot_helpers import make_bot


async def on_sleep(callback: CallbackQuery):
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

    collect_rewards(user_id)

    try:
        sleep(user_id)
    except SleepError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    await callback.answer(t("sleep.started_short", lang))

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def on_wake(callback: CallbackQuery):
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

    try:
        wake(user_id)
    except SleepError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    await callback.answer(t("wake.done", lang))

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def on_work_start(callback: CallbackQuery):
    from core.bot_helpers import check_session, refresh_main
    from core.time_utils import humanize_seconds
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

    # work:farm:session
    parts = callback.data.split(":")
    if len(parts) < 2:
        return
    work_type = parts[1]

    try:
        info = start_work(user_id, work_type)
    except WorkError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    await callback.answer(t("work.started_short", lang))

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def on_work_collect(callback: CallbackQuery):
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

    rewards = collect_rewards(user_id)
    if rewards:
        # Если это первый квест — завершить и выдать бонус
        try:
            from services.starter_quest import get_starter_quest, complete_starter_quest
            if get_starter_quest(user_id) and get_starter_quest(user_id)["status"] == "active":
                bonus = complete_starter_quest(user_id)
                if bonus:
                    await callback.answer(
                        t("starter.complete_popup", lang, tokens=bonus["tokens"], food=bonus["food"]),
                        show_alert=True,
                    )
        except Exception:
            pass
    if not rewards:
        await callback.answer(t("work.not_done", lang), show_alert=True)
        return

    icons = {"food": "🍞", "tokens": "🪙", "water": "💧"}
    text = ", ".join(f"{icons.get(k, k)} +{v}" for k, v in rewards.items())
    await callback.answer(t("work.done", lang, rewards=text), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()
