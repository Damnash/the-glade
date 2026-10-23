# bot.py — основной файл запуска бота

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter

from handlers.radio_states import RadioTalkState
from config import BOT_TOKEN
from services import maze_moves_handlers as maze_mv
from core.i18n import load_locales
from core.commands import command_aliases
from db.connection import init_db

from handlers import (
    start,
    help as help_h,
    movement,
    info,
    language,
    language_callback,
    sleep as sleep_h,
    work as work_h,
    stats as stats_h,
    eat as eat_h,
    inventory as inv_h,
    admin as admin_h,
    maze as maze_h,
    nav_callback as nav_cb,
    stats_callback as stats_cb,
    action_callback as act_cb,
    maze_callback as maze_cb,
    whisper as whisper_h,
    say as say_h,
    radio as radio_h,
    fallback as fallback_h,
    # RadioTalkState импортируется отдельно ниже
    map as map_h,
    maps as maps_h,
    combat_callback as combat_cb,
    keys as keys_h,
    npcs as npcs_h,
    clans as clans_h,
    clan_upgrades as cu_h,
    intro as intro_h,
    story as story_h,
    time_cmd as time_h,
    pvp as pvp_h,
    achievements as ach_h,
    season_cmd as season_h,
    gates as gates_h,
    daily_quest as dq_h,
    journal,
    diary,
)




async def maze_cleanup_task():
    """Раз в минуту: убивать игроков с истёкшим таймером вылазки."""
    import asyncio
    import logging
    from services.maze_runs import get_expired_runs, end_run
    from services.death import die_in_maze

    while True:
        try:
            await asyncio.sleep(60)  # раз в минуту

            expired = get_expired_runs()
            for run in expired:
                uid = run["user_id"]
                try:
                    die_in_maze(uid)
                    logging.info(f"[MAZE] killed {uid} (timer expired)")
                except Exception as e:
                    logging.error(f"[MAZE] kill {uid} failed: {e}")
                finally:
                    try:
                        end_run(uid)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"maze_cleanup error: {e}")


async def world_events_task(bot):
    """Раз в час: случайное фоновое событие мира → всем игрокам."""
    import asyncio
    import logging
    from services.world_events import pick_event, broadcast_world_event

    # Дать боту время запуститься
    await asyncio.sleep(30)

    while True:
        try:
            await asyncio.sleep(3600)  # раз в час
            event_key = pick_event()
            sent = await broadcast_world_event(bot, event_key)
            logging.info(f"[WORLD] event={event_key} sent={sent}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"world_events error: {e}")


async def weather_task(bot):
    """Раз в час: смена погоды + broadcast."""
    import asyncio
    import logging
    from services.weather import change_weather

    await asyncio.sleep(60)  # дать боту стартовать

    while True:
        try:
            await asyncio.sleep(3600)  # раз в час
            new = await change_weather(bot)
            logging.info(f"[WEATHER] changed to {new}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"weather_task error: {e}")


async def work_reminder_task(bot):
    """Раз в 5 минут: push «работа готова» тем, кто оффлайн."""
    import asyncio
    import logging
    from core.time_utils import now
    from db.connection import get_conn
    from services.push import send_push

    await asyncio.sleep(120)

    while True:
        try:
            await asyncio.sleep(300)  # раз в 5 минут
            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT user_id, work_type, work_ends_at, language
                    FROM players
                    WHERE status = 'working'
                      AND work_ends_at <= ?
                      AND work_type IS NOT NULL
                """, (now(),))
                rows = cur.fetchall()
            finally:
                conn.close()

            for row in rows:
                uid = row["user_id"]
                lang = row["language"] or "en"
                try:
                    from core.i18n import t
                    text = t("push.work_done", lang)
                    await send_push(bot, uid, text)
                except Exception as e:
                    logging.warning(f"[WORK REMINDER] {uid}: {e}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"work_reminder_task error: {e}")


async def title_push_task(bot):
    """Раз в 10 минут: push о новых титулах оффлайн-игрокам."""
    import asyncio
    import logging
    from db.connection import get_conn
    from services.push import send_push, is_online
    from core.i18n import t

    await asyncio.sleep(180)

    while True:
        try:
            await asyncio.sleep(600)  # раз в 10 минут
            conn = get_conn()
            try:
                cur = conn.cursor()
                # Титулы, полученные за последние 15 минут
                cur.execute("""
                    SELECT pt.user_id, pt.title_key, p.language
                    FROM player_titles pt
                    JOIN players p ON p.user_id = pt.user_id
                    WHERE pt.awarded_at >= datetime('now', '-15 minutes')
                """)
                rows = cur.fetchall()
            finally:
                conn.close()

            for row in rows:
                uid = row["user_id"]
                title_key = row["title_key"]
                lang = row["language"] or "en"
                try:
                    from content.titles import TITLES
                    spec = TITLES.get(title_key)
                    if not spec:
                        continue
                    text = t("push.new_title", lang, title=f"{spec['icon']} {t(spec['name_key'], lang)}")
                    await send_push(bot, uid, text)
                except Exception as e:
                    logging.warning(f"[TITLE PUSH] {uid}: {e}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"title_push_task error: {e}")


async def cleanup_task():
    """Фоновая задача: очистка и проверка сезона."""
    import asyncio
    from db.map_items import cleanup_expired_drops
    from db.pvp import cleanup_expired_duels
    from db.clans import cleanup_expired_invites
    from services.season_manager import start_new_season_if_needed

    while True:
        try:
            await asyncio.sleep(3600)  # раз в час

            n1 = cleanup_expired_drops()
            n2 = cleanup_expired_duels()
            n3 = cleanup_expired_invites()

            if n1 or n2 or n3:
                logging.info(f"[CLEANUP] drops={n1}, duels={n2}, invites={n3}")

            result = start_new_season_if_needed()
            if result:
                logging.info(f"[SEASON] Ended season {result['old_season']}, started {result['new_season']}")

        except Exception as e:
            logging.error(f"Cleanup error: {e}")




# ============ Middleware: логирование необработанных callback'ов ============

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message



async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    load_locales()
    init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # ============ Обычные команды ============
    dp.message.register(start.cmd_start,       Command(*command_aliases("commands.start")))
    dp.message.register(help_h.cmd_help,       Command(*command_aliases("commands.help")))
    dp.message.register(movement.cmd_look,     Command(*command_aliases("commands.look")))
    dp.message.register(movement.cmd_go,       Command(*command_aliases("commands.go")))
    dp.message.register(info.cmd_who,          Command(*command_aliases("commands.who")))
    dp.message.register(info.cmd_where,        Command(*command_aliases("commands.where")))
    dp.message.register(language.cmd_language, Command(*command_aliases("commands.language")))
    dp.message.register(sleep_h.cmd_sleep,     Command(*command_aliases("commands.sleep")))
    dp.message.register(sleep_h.cmd_wake,      Command(*command_aliases("commands.wake")))
    dp.message.register(work_h.cmd_work,       Command(*command_aliases("commands.work")))
    dp.message.register(stats_h.cmd_stats,     Command(*command_aliases("commands.stats")))
    dp.message.register(eat_h.cmd_eat,         Command(*command_aliases("commands.eat")))
    dp.message.register(inv_h.cmd_inventory,   Command(*command_aliases("commands.inventory")))
    dp.message.register(inv_h.cmd_use,         Command(*command_aliases("commands.use")))
    dp.message.register(maze_h.cmd_raid,       Command(*command_aliases("commands.raid")))
    dp.message.register(maze_h.cmd_return,     Command(*command_aliases("commands.return")))
    dp.message.register(whisper_h.cmd_whisper, Command(*command_aliases("commands.whisper")))
    dp.message.register(radio_h.cmd_walkie, Command(*command_aliases("commands.walkie")))

    dp.message.register(time_h.cmd_time, Command(*command_aliases("commands.time")))
    dp.message.register(season_h.cmd_season, Command(*command_aliases("commands.season")))
    dp.message.register(ach_h.cmd_achievements, Command(*command_aliases("commands.achievements")))
    dp.message.register(ach_h.cmd_leaderboard, Command(*command_aliases("commands.top")))
    dp.message.register(ach_h.cmd_hall_of_fame, Command(*command_aliases("commands.hall")))
    dp.message.register(gates_h.cmd_gates, Command(*command_aliases("commands.gates")))
    dp.message.register(pvp_h.cmd_steal, Command(*command_aliases("commands.steal")))
    dp.message.register(pvp_h.cmd_attack, Command(*command_aliases("commands.attack")))
    dp.message.register(pvp_h.cmd_duel, Command(*command_aliases("commands.duel")))
    dp.message.register(pvp_h.cmd_pvp_flag, Command(*command_aliases("commands.pvp_flag")))
    dp.message.register(clans_h.cmd_clan, Command(*command_aliases("commands.clan")))
    dp.message.register(clans_h.cmd_clan_create, Command(*command_aliases("commands.clan_create")))
    dp.message.register(clans_h.cmd_clan_invite, Command(*command_aliases("commands.clan_invite")))
    dp.message.register(clans_h.cmd_clan_chat, Command(*command_aliases("commands.clan_chat")))
    dp.message.register(keys_h.cmd_keys, Command(*command_aliases("commands.keys")))
    dp.message.register(maps_h.cmd_maps, Command(*command_aliases("commands.maps")))
    dp.message.register(maps_h.cmd_map_create, Command(*command_aliases("commands.map_create")))
    dp.message.register(maps_h.cmd_draw, Command(*command_aliases("commands.draw")))
    dp.message.register(maps_h.cmd_pickup_maps, Command(*command_aliases("commands.pickup_maps")))
    dp.message.register(maps_h.cmd_section_rename, Command(*command_aliases("commands.section_rename")))
    dp.message.register(maps_h.cmd_section_note, Command(*command_aliases("commands.section_note")))
    dp.message.register(map_h.cmd_map, Command(*command_aliases("commands.map")))
    dp.message.register(radio_h.cmd_radio,  Command(*command_aliases("commands.radio")))
    dp.message.register(radio_h.cmd_walkie_talk, Command(*command_aliases("commands.talk")))
    dp.message.register(journal.cmd_journal, Command(*command_aliases("commands.journal")))
    dp.message.register(diary.cmd_diary, Command(*command_aliases("commands.diary")))
    dp.callback_query.register(maps_h.on_maps_list, F.data.startswith("maps:list"))
    dp.callback_query.register(maps_h.on_maps_list, F.data.startswith("map:list"))
    dp.callback_query.register(maps_h.on_map_open, F.data.startswith("map:open:"))
    dp.callback_query.register(maps_h.on_map_create, F.data.startswith("map:create"))
    dp.callback_query.register(maps_h.on_map_rename, F.data.startswith("map:rename:"))
    dp.callback_query.register(maps_h.on_map_drop, F.data.startswith("map:drop:"))
    dp.callback_query.register(maps_h.on_map_sections, F.data.startswith("map:sections:"))
    dp.callback_query.register(maps_h.on_map_edit_section, F.data.startswith("map:edit:"))
    dp.callback_query.register(maps_h.on_map_draw, F.data.startswith("map:draw:"))
    dp.callback_query.register(map_h.on_map_open,  F.data.startswith("map:open"))
    dp.callback_query.register(map_h.on_map_layer, F.data.startswith("map:layer:"))
    dp.callback_query.register(radio_h.on_radio_menu,     F.data.startswith("radio:menu"))
    dp.callback_query.register(radio_h.on_radio_toggle,   F.data.startswith("radio:toggle"))
    dp.callback_query.register(radio_h.on_radio_history,  F.data.startswith("radio:history"))
    dp.callback_query.register(radio_h.on_radio_manual, F.data.startswith("radio:manual"))
    dp.callback_query.register(radio_h.on_radio_talk,     F.data.startswith("radio:talk"))

    # Админка — один роутер
    dp.message.register(admin_h.cmd_admin_router, Command(*command_aliases("commands.admin")))

    # ============ Callback'и ============

    # Язык (один раз)
    # Onboarding
    dp.callback_query.register(story_h.on_story_menu,     F.data.startswith("story:menu:"))
    dp.callback_query.register(story_h.on_story_start,    F.data.startswith("story:start:"))
    dp.callback_query.register(story_h.on_story_check,    F.data.startswith("story:check:"))
    dp.callback_query.register(story_h.on_story_complete, F.data.startswith("story:complete:"))
    dp.callback_query.register(intro_h.on_intro_next,   F.data.startswith("intro:next:"))
    dp.callback_query.register(intro_h.on_intro_perk,   F.data.startswith("intro:perk:"))
    dp.callback_query.register(intro_h.on_intro_prof,   F.data.startswith("intro:prof:"))
    dp.callback_query.register(intro_h.on_intro_finish, F.data.startswith("intro:finish"))

    dp.callback_query.register(
        language_callback.on_language_pick,
        F.data.startswith("lang:"),
    )

    # Главный экран и навигация
    dp.callback_query.register(nav_cb.on_move,      F.data.startswith("nav:move"))
    dp.callback_query.register(nav_cb.on_todo,      F.data.startswith("nav:todo"))
    dp.callback_query.register(nav_cb.on_actions,   F.data.startswith("nav:actions"))
    dp.callback_query.register(nav_cb.on_work,      F.data.startswith("nav:work"))
    dp.callback_query.register(nav_cb.on_back,      F.data.startswith("nav:back"))
    dp.callback_query.register(nav_cb.on_more,      F.data.startswith("nav:more"))

    # Daily quest
    dp.callback_query.register(dq_h.show_daily_quest, F.data.startswith("daily_quest:show"))
    dp.callback_query.register(dq_h.on_daily_quest_complete, F.data.startswith("daily_quest:complete"))

    # Перемещение и осмотр
    dp.callback_query.register(nav_cb.on_go,        F.data.startswith("go:"))
    dp.callback_query.register(nav_cb.on_look,      F.data.startswith("act:look"))

    # Статы
    dp.callback_query.register(stats_cb.on_stats,   F.data.startswith("nav:stats"))

    # Инвентарь
    dp.callback_query.register(nav_cb.on_inventory, F.data.startswith("nav:inv"))
    dp.callback_query.register(nav_cb.on_use,       F.data.startswith("use:"))

    # Действия: сон, пробуждение
    dp.callback_query.register(act_cb.on_sleep,     F.data.startswith("act:sleep"))
    dp.callback_query.register(act_cb.on_wake,      F.data.startswith("act:wake"))

    # ⚠️ ВАЖЕН ПОРЯДОК: work:collect ДО work:*
    dp.callback_query.register(act_cb.on_work_collect, F.data.startswith("work:collect"))
    dp.callback_query.register(act_cb.on_work_start,   F.data.startswith("work:"))

    # Лабиринт
    dp.callback_query.register(maze_cb.on_enter_force, F.data.startswith("raid:enter_force"))
    dp.callback_query.register(maze_cb.on_enter,       F.data.startswith("raid:enter:"))
    dp.callback_query.register(maze_cb.on_maze_back, F.data.startswith("maze:back"))
    dp.callback_query.register(maze_cb.on_return, F.data == "raid:return")
    dp.callback_query.register(maze_mv.on_exit,   F.data.startswith("maze:exit"))

    # Заглушка (noop)
    dp.callback_query.register(nav_cb.on_noop,      F.data.startswith("noop"))
    dp.callback_query.register(maze_mv.on_go,       F.data.startswith("maze:go:"))
    dp.callback_query.register(keys_h.on_keys_show, F.data.startswith("keys:show"))
    dp.callback_query.register(maze_cb.on_pickup_ground, F.data.startswith("maze:pickup:"))
    dp.callback_query.register(pvp_h.show_pvp_flag, F.data.startswith("pvp:flag:"))
    dp.callback_query.register(pvp_h.on_pvp_flag_toggle, F.data.startswith("pvp:flag_on"))
    dp.callback_query.register(pvp_h.on_pvp_flag_toggle, F.data.startswith("pvp:flag_off"))
    dp.callback_query.register(pvp_h.on_duel_accept, F.data.startswith("duel:accept:"))
    dp.callback_query.register(pvp_h.on_duel_decline, F.data.startswith("duel:decline:"))
    dp.callback_query.register(clans_h.on_clan_main, F.data.startswith("clan:main"))
    dp.callback_query.register(clans_h.on_clan_open_list, F.data.startswith("clan:open_list"))
    dp.callback_query.register(clans_h.on_clan_open_detail, F.data.startswith("clan:open:"))
    dp.callback_query.register(clans_h.on_clan_join, F.data.startswith("clan:join:"))
    dp.callback_query.register(clans_h.on_clan_toggle_open, F.data.startswith("clan:toggle_open"))

    # Clan upgrades + storage
    dp.callback_query.register(cu_h.show_clan_upgrades, F.data.startswith("clan_upgrades:show"))
    dp.callback_query.register(cu_h.on_upgrade_click,    F.data.startswith("clan_upgrade:do:"))
    dp.callback_query.register(cu_h.show_clan_storage,   F.data.startswith("clan_storage:show"))
    dp.callback_query.register(clans_h.on_clan_members, F.data.startswith("clan:members"))
    dp.callback_query.register(clans_h.on_clan_chat, F.data.startswith("clan:chat"))
    dp.callback_query.register(clans_h.on_clan_map, F.data.startswith("clan:map"))
    dp.callback_query.register(clans_h.on_clan_treasury, F.data.startswith("clan:treasury"))
    dp.callback_query.register(clans_h.on_clan_invites, F.data.startswith("clan:invites"))
    dp.callback_query.register(clans_h.on_clan_invite_help, F.data.startswith("clan:invite_help"))
    dp.callback_query.register(clans_h.on_clan_create_help, F.data.startswith("clan:create_help"))
    dp.callback_query.register(clans_h.on_clan_accept, F.data.startswith("clan:accept:"))
    dp.callback_query.register(clans_h.on_clan_leave, F.data.startswith("clan:leave"))
    dp.callback_query.register(clans_h.on_clan_leave_confirm, F.data.startswith("clan:leave_confirm"))
    dp.callback_query.register(help_h.on_help_main, F.data.startswith("help:main"))
    dp.callback_query.register(journal.on_journal_show, F.data.startswith("journal:show"))
    dp.callback_query.register(diary.on_diary_show, F.data.startswith("diary:show"))
    dp.callback_query.register(help_h.on_help_category, F.data.startswith("help:cat:"))
    dp.callback_query.register(npcs_h.on_talk_to_npc, F.data.startswith("npc:talk:"))
    dp.callback_query.register(npcs_h.on_npc_action, F.data.startswith("npc:"))
    dp.callback_query.register(combat_cb.on_attack, F.data.startswith("combat:attack"))
    dp.callback_query.register(combat_cb.on_defend, F.data.startswith("combat:defend"))
    dp.callback_query.register(combat_cb.on_flee, F.data.startswith("combat:flee"))
    dp.callback_query.register(maze_cb.on_compass,  F.data.startswith("maze:compass:"))
    dp.callback_query.register(maze_cb.on_heal,     F.data.startswith("maze:heal:"))
    dp.callback_query.register(maze_cb.on_look,     F.data.startswith("maze:look:"))
    dp.callback_query.register(maze_cb.on_diary_read, F.data.startswith("maze:diary:"))

    background_tasks = []

    background_tasks.append(asyncio.create_task(cleanup_task()))
    background_tasks.append(asyncio.create_task(title_push_task(bot)))
    background_tasks.append(asyncio.create_task(work_reminder_task(bot)))
    background_tasks.append(asyncio.create_task(weather_task(bot)))
    background_tasks.append(asyncio.create_task(world_events_task(bot)))
    background_tasks.append(asyncio.create_task(maze_cleanup_task()))
    # Уведомления утро/вечер
    from services.daycycle_events import daycycle_events_task
    background_tasks.append(asyncio.create_task(daycycle_events_task(bot)))
    # FSM: приём текста в рацию (в самом конце, чтобы не перехватить команды)
    dp.message.register(
        radio_h.process_radio_message,
        StateFilter(RadioTalkState.waiting_for_message),
    )

    # Fallback — если текст не команда и не FSM (в САМОМ конце)
    dp.message.register(fallback_h.on_unknown_text)

    logging.info("The Glade is running...")

    # Глобальный логгер
    @dp.callback_query.middleware()
    async def log_callback(handler, event, data):
        logging.info(f"[CB] {event.data!r} user={event.from_user.id}")
        try:
            return await handler(event, data)
        except Exception as e:
            logging.error(f"[CB ERROR] {type(e).__name__}: {e}", exc_info=True)
            raise

    @dp.message.middleware()
    async def log_message(handler, event, data):
        if event.text:
            logging.info(f"[MSG] {event.text!r} user={event.from_user.id}")
        try:
            return await handler(event, data)
        except Exception as e:
            logging.error(f"[MSG ERROR] {type(e).__name__}: {e}", exc_info=True)
            raise

    try:
        await dp.start_polling(bot)
    finally:
        logging.info("Stopping background tasks...")
        for task in background_tasks:
            task.cancel()
        try:
            await asyncio.wait_for(
                asyncio.gather(*background_tasks, return_exceptions=True),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            logging.warning("Some background tasks did not stop in 5s")
        try:
            await bot.session.close()
        except Exception:
            pass
        logging.info("The Glade stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass