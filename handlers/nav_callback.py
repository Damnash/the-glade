# handlers/nav_callback.py

from aiogram.types import CallbackQuery

from core.i18n import t
from content.locations import LOCATIONS
from content.hints import HINTS
from db.players import get_player, players_in_location
from keyboards.main import main_keyboard
from keyboards.move import move_keyboard
from keyboards.todo import todo_keyboard
from keyboards.actions import actions_keyboard
from keyboards.work import work_keyboard
from core.bot_helpers import make_bot


def render_location_text(lang: str, loc_key: str, viewer_id: int) -> str:
    """Текст локации."""
    from content.npcs import get_npcs_in_location
    from core.daycycle import get_current_phase

    name = t(f"loc.{loc_key}.name", lang)

    # Описание по фазе дня
    phase = get_current_phase()
    phase_key = f"loc.{loc_key}.desc.{phase}"
    desc = t(phase_key, lang)
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

    # Звуковое описание (атмосфера)
    try:
        import random
        from content.loc_sounds import LOC_SOUNDS
        sounds = LOC_SOUNDS.get(loc_key)
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

    npcs = get_npcs_in_location(loc_key)
    if npcs:
        npc_names = ", ".join(t(n["name_key"], lang) for n in npcs)
        parts.append(t("look.npcs", lang, npcs=npc_names))

    hint_key = HINTS.get(loc_key)
    if hint_key:
        hint_text = t(hint_key, lang)
        if hint_text != hint_key:
            parts.append(f"💡 {hint_text}")

    return "\n\n".join(parts)


async def show_main(callback: CallbackQuery):
    """Показать главный экран."""
    from aiogram import Bot
    from config import BOT_TOKEN
    from core.bot_helpers import refresh_main

    user_id = callback.from_user.id

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_back(callback: CallbackQuery):
    """Назад — главный экран."""
    from core.bot_helpers import check_session
    user_id = callback.from_user.id

    if not check_session(user_id, callback.data):
        player = get_player(user_id)
        lang = player["language"] if player else "ru"
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    await show_main(callback)


async def on_move(callback: CallbackQuery):
    """Меню перемещения."""
    from core.bot_helpers import check_session

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", player["language"]), show_alert=True)
        return

    lang = player["language"]
    session = player.get("current_session", "")

    loc_name = t(f"loc.{player['location']}.name", lang)
    text = f"{t('move.header', lang)}\n\n📍 {loc_name}"

    kb = move_keyboard(lang, player["location"], session)

    from aiogram import Bot
    from config import BOT_TOKEN
    from core.bot_helpers import edit_main

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_todo(callback: CallbackQuery):
    """Меню «Что делать?»."""
    from core.bot_helpers import check_session, edit_main
    from aiogram import Bot
    from config import BOT_TOKEN

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", player["language"]), show_alert=True)
        return

    lang = player["language"]
    session = player.get("current_session", "")

    loc_name = t(f"loc.{player['location']}.name", lang)
    text = f"⚒️ <b>{t('todo.header', lang)}</b>\n\n📍 {loc_name}"

    kb = todo_keyboard(lang, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_actions(callback: CallbackQuery):
    """Меню «Действия»."""
    from core.bot_helpers import check_session, edit_main
    from aiogram import Bot
    from config import BOT_TOKEN

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", player["language"]), show_alert=True)
        return

    lang = player["language"]
    session = player.get("current_session", "")

    loc_name = t(f"loc.{player['location']}.name", lang)
    text = f"👀 <b>{t('actions.header', lang)}</b>\n\n📍 {loc_name}"

    kb = actions_keyboard(lang, player, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_work(callback: CallbackQuery):
    """Меню «Работа»."""
    from core.bot_helpers import check_session, edit_main
    from aiogram import Bot
    from config import BOT_TOKEN

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", player["language"]), show_alert=True)
        return

    lang = player["language"]
    session = player.get("current_session", "")

    loc_name = t(f"loc.{player['location']}.name", lang)
    text = f"🛠️ <b>{t('work.header', lang)}</b>\n\n📍 {loc_name}"

    kb = work_keyboard(lang, player, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_go(callback: CallbackQuery):
    """Переход в локацию."""
    from core.bot_helpers import check_session, refresh_main
    from services.movement import move, MoveError
    from aiogram import Bot
    from config import BOT_TOKEN

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # Парсим: go:center:session
    parts = callback.data.split(":")
    if len(parts) < 2:
        return
    target = parts[1]

    try:
        move(user_id, target)
    except MoveError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_look(callback: CallbackQuery):
    """Осмотреться."""
    from core.bot_helpers import check_session, refresh_main
    from aiogram import Bot
    from config import BOT_TOKEN

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", player["language"]), show_alert=True)
        return

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_noop(callback: CallbackQuery):
    """Пустое действие (noop) — гасим индикатор.

    Если status='sleeping'/'working' — показываем popup с объяснением.
    """
    from core.bot_helpers import check_session
    from db.players import get_player
    from core.i18n import t

    user_id = callback.from_user.id
    if not check_session(user_id, callback.data):
        await callback.answer()
        return

    player = get_player(user_id)
    if not player:
        await callback.answer()
        return

    status = player.get("status")
    if status == "sleeping":
        await callback.answer(t("noop.sleeping", player["language"]), show_alert=True)
        return
    if status == "working":
        from core.time_utils import seconds_until, humanize_seconds
        left = seconds_until(player.get("work_ends_at"))
        if left <= 0:
            # работа закончилась — перерисовываем меню (там будет кнопка "Забрать")
            from core.bot_helpers import refresh_main, make_bot
            bot = make_bot()
            try:
                await refresh_main(bot, user_id)
            finally:
                await bot.session.close()
            await callback.answer(t("noop.work_done", player["language"]))
        else:
            await callback.answer(
                t("noop.working", player["language"], time=humanize_seconds(left, player["language"])),
                show_alert=True,
            )
        return

    await callback.answer()


async def on_inventory(callback):
    """Показать инвентарь."""
    from core.bot_helpers import check_session, edit_main
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from services.inventory import list_inventory
    from content.items import ITEMS
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

    items = list_inventory(user_id)
    session = player.get("current_session", "")
    s = f":{session}" if session else ""

    if not items:
        text = t("inv.empty", lang)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}")
        ]])
    else:
        lines = [t("inv.header", lang), ""]
        rows = []
        for item in items:
            key = item["item_key"]
            name = t(f"item.{key}.name", lang)
            lines.append(f"• {name} × {item['quantity']}")

            spec = ITEMS.get(key, {})
            if spec.get("use"):
                rows.append([
                    InlineKeyboardButton(
                        text=f"{name} × {item['quantity']} — {t('inv.btn_use', lang)}",
                        callback_data=f"use:{key}{s}",
                    )
                ])

        rows.append([
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}")
        ])
        text = "\n".join(lines)
        kb = InlineKeyboardMarkup(inline_keyboard=rows)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_use(callback):
    """Использовать предмет."""
    from core.bot_helpers import check_session, refresh_main
    from services.inventory import use_item, InvError
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

    # use:item_key:session
    parts = callback.data.split(":")
    if len(parts) < 2:
        return
    item_key = parts[1]

    try:
        result = use_item(user_id, item_key)
    except InvError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    if result["action"] == "eat":
        await callback.answer(f"🍞 HP: {result['hp']}/100", show_alert=True)
    elif result["action"] == "drink":
        await callback.answer(f"💧 Water: {result['water']}", show_alert=True)
    elif result["action"] == "heal":
        await callback.answer(
            t("medic.healed", lang, healed=result["healed"], hp=result["hp"]),
            show_alert=True,
        )

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()

async def on_more(callback):
    """nav:more:<session> — подменю «Ещё»."""
    from core.bot_helpers import check_session, edit_main, make_bot
    from keyboards.more import more_keyboard

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    session = player.get("current_session", "")
    text = f"📋 <b>{t('more.title', lang)}</b>"
    kb = more_keyboard(lang, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()

