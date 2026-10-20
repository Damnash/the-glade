# handlers/maps.py

from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from services.event_log import add_event, cleanup_old_events
from core.bot_helpers import check_session, edit_main, refresh_main, command_reply, make_bot
from core.maze_current import get_current_season
from db.players import get_player, get_lang, find_by_name
from db.map_items import (
    get_player_maps, get_map, get_personal_map, count_player_maps,
    get_map_limit, get_maps_on_ground, pickup_map,
)
from services.maps import (
    ensure_personal_map, create_new_map, rename_player_map,
    delete_player_map, get_map_view, draw_section, MapError,
    NAME_MIN, NAME_MAX,
)
from keyboards.maps import (
    maps_list_keyboard, map_view_keyboard, cancel_keyboard,
    back_to_list_keyboard,
)


def render_maps_list(lang: str, user_id: int) -> str:
    maps = get_player_maps(user_id)
    limit = get_map_limit(user_id)
    season = get_current_season()

    from db.map_items import count_map_sections

    lines = [
        "🗺️ <b>" + t('map.my_maps', lang) + "</b> (" + str(len(maps)) + "/" + str(limit) + ")",
        "",
    ]

    if not maps:
        lines.append(t("map.no_maps", lang))
    else:
        for m in maps:
            icon = "📜" if m["is_personal"] else "🗺️"
            label = t("map.personal_tag", lang) if m["is_personal"] else ""
            cnt = count_map_sections(m["id"], season, 1)
            lines.append(icon + " <b>" + m['name'] + "</b> " + label + " — " + str(cnt) + " " + t('map.sections_short', lang))

    return "\n".join(lines)


# ============ Команды ============

async def cmd_maps(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    display_name = player["display_name"] or player["username"] or "Runner"
    ensure_personal_map(user_id, display_name)

    text = render_maps_list(lang, user_id)
    maps = get_player_maps(user_id)
    limit = get_map_limit(user_id)
    kb = maps_list_keyboard(lang, maps, limit, player)

    await command_reply(message, text, kb)


async def cmd_map_create(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("map.create_help", lang, min=NAME_MIN, max=NAME_MAX))
        return

    name = parts[1].strip()

    try:
        create_new_map(user_id, name)
    except MapError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(t("map.created_ok", lang, name=name))

    text = render_maps_list(lang, user_id)
    maps = get_player_maps(user_id)
    limit = get_map_limit(user_id)
    kb = maps_list_keyboard(lang, maps, limit, player)
    await message.answer(text, reply_markup=kb)


async def cmd_map_rename(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(t("map.rename_usage", lang))
        return

    try:
        map_id = int(parts[1])
    except ValueError:
        await message.answer(t("map.rename_usage", lang))
        return

    new_name = parts[2].strip()

    try:
        rename_player_map(user_id, map_id, new_name)
    except MapError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(t("map.renamed_ok", lang, name=new_name))

    # Показать карту
    callback_data = "map:open:" + str(map_id) + ":" + (player.get("current_session") or "")
    # Просто показать
    session = player.get("current_session", "")
    m = get_map(map_id)
    if m:
        view = get_map_view(map_id, user_id, layer=1)
        sections = view["sections"]
        icon = "📜" if m["is_personal"] else "🗺️"
        lines = [icon + " <b>" + m['name'] + "</b>", "<i>" + t('map.layer_line', lang, layer=1) + "</i>", ""]
        if not sections:
            lines.append(t("map.empty_map", lang))
        else:
            for s in sections:
                nm = s["custom_name"] or s["section_id"]
                note = "\n   📝 <i>" + s['note'] + "</i>" if s.get("note") else ""
                lines.append("• <b>" + s['section_id'] + "</b> — " + nm + note)
        lines.append("")
        lines.append(t("map.total_sections", lang, n=len(sections)))
        text = "\n".join(lines)
        kb = map_view_keyboard(lang, map_id, bool(m["is_personal"]), player, session)
        await message.answer(text, reply_markup=kb)


async def cmd_draw(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    layer = player.get("maze_layer", 0)
    section_id = player.get("maze_section")

    if layer == 0 or not section_id:
        await message.answer(t("map.not_in_maze", lang))
        return

    personal = get_personal_map(user_id)
    if not personal:
        await message.answer(t("map.err.no_personal", lang))
        return

    try:
        added = draw_section(user_id, personal["id"], section_id, layer)
    except MapError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    if added:
        await message.answer(t("map.drawn_ok", lang, section=section_id))
        try:
            add_event(user_id, "map_drawn", t("log.map_drawn", lang, section=section_id), severity="chat")
            cleanup_old_events(user_id)
        except Exception:
            pass
    else:
        await message.answer(t("map.already_drawn", lang))


async def cmd_pickup_maps(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    layer = player.get("maze_layer", 0)
    section_id = player.get("maze_section")

    if layer == 0 or not section_id:
        await message.answer(t("map.not_in_maze", lang))
        return

    ground = get_maps_on_ground(section_id, layer)
    if not ground:
        await message.answer(t("map.no_maps_here", lang))
        return

    picked = 0
    for m in ground:
        if pickup_map(m["id"], user_id):
            picked += 1

    await message.answer(t("map.picked_up", lang, n=picked))


async def cmd_section_rename(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer(t("map.section_rename_usage", lang))
        return

    try:
        map_id = int(parts[1])
    except ValueError:
        await message.answer(t("map.section_rename_usage", lang))
        return

    section_id = parts[2]
    new_name = parts[3].strip()
    layer = player.get("maze_layer", 1) or 1

    try:
        from services.maps import update_section
        update_section(map_id, user_id, section_id, layer, custom_name=new_name)
    except MapError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(t("map.section_renamed", lang, name=new_name))


async def cmd_section_note(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer(t("map.section_note_usage", lang))
        return

    try:
        map_id = int(parts[1])
    except ValueError:
        await message.answer(t("map.section_note_usage", lang))
        return

    section_id = parts[2]
    note = parts[3].strip()
    layer = player.get("maze_layer", 1) or 1

    try:
        from services.maps import update_section
        update_section(map_id, user_id, section_id, layer, note=note)
    except MapError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(t("map.section_note_saved", lang))


# ============ Callbacks ============

async def on_maps_list(callback: CallbackQuery):
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

    text = render_maps_list(lang, user_id)
    maps = get_player_maps(user_id)
    limit = get_map_limit(user_id)
    kb = maps_list_keyboard(lang, maps, limit, player)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_map_open(callback: CallbackQuery):
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

    # map:open:ID:session
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    map_id = int(parts[2])

    try:
        view = get_map_view(map_id, user_id, layer=1)
    except MapError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    m = view["map"]
    sections = view["sections"]
    icon = "📜" if m["is_personal"] else "🗺️"

    lines = [
        icon + " <b>" + m['name'] + "</b>",
        "<i>" + t('map.layer_line', lang, layer=1) + "</i>",
        "",
    ]

    if not sections:
        lines.append(t("map.empty_map_help", lang))
    else:
        for s in sections:
            nm = s["custom_name"] or s["section_id"]
            note = "\n   📝 <i>" + s['note'] + "</i>" if s.get("note") else ""
            lines.append("• <b>" + s['section_id'] + "</b> — " + nm + note)
    lines.append("")
    lines.append(t("map.total_sections", lang, n=len(sections)))

    text = "\n".join(lines)
    session = player.get("current_session", "")
    kb = map_view_keyboard(lang, map_id, bool(m["is_personal"]), player, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_map_create(callback: CallbackQuery):
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

    # Создаём с именем по умолчанию
    count = count_player_maps(user_id)
    default_name = t("map.default_name", lang) + " " + str(count + 1)

    try:
        create_new_map(user_id, default_name)
    except MapError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    await callback.answer(t("map.created_ok", lang, name=default_name), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def on_map_rename(callback: CallbackQuery):
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

    parts = callback.data.split(":")
    map_id = int(parts[2])
    m = get_map(map_id)
    if not m or m["owner_id"] != user_id:
        await callback.answer("Not yours.", show_alert=True)
        return

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    text = (
        "✏️ <b>" + t('map.rename_title', lang) + "</b>\n\n"
        + t('map.current_name', lang, name=m['name']) + "\n\n"
        + t('map.create_help', lang, min=NAME_MIN, max=NAME_MAX) + "\n\n"
        + "Напиши: <code>/карта-имя " + str(map_id) + " Новое имя</code>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("map.btn_back", lang), callback_data="map:open:" + str(map_id) + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_map_drop(callback: CallbackQuery):
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

    parts = callback.data.split(":")
    map_id = int(parts[2])

    try:
        delete_player_map(user_id, map_id)
    except MapError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    await callback.answer(t("map.dropped_ok", lang), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def on_map_draw(callback: CallbackQuery):
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

    # map:draw:section_id:session
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    section_id = parts[2]
    layer = player.get("maze_layer", 1)

    if layer == 0 or not player.get("maze_section"):
        await callback.answer(t("map.not_in_maze", lang), show_alert=True)
        return

    personal = get_personal_map(user_id)
    if not personal:
        player_maps = get_player_maps(user_id)
        if player_maps:
            personal = player_maps[0]
        else:
            await callback.answer(t("map.err.no_personal", lang), show_alert=True)
            return

    try:
        added = draw_section(user_id, personal["id"], section_id, layer)
    except MapError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    if added:
        await callback.answer(t("map.drawn_ok", lang, section=section_id), show_alert=True)
    else:
        await callback.answer(t("map.already_drawn", lang), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def on_map_sections(callback: CallbackQuery):
    from config import BOT_TOKEN
    from aiogram import Bot
    from keyboards.maps import map_sections_keyboard

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    parts = callback.data.split(":")
    map_id = int(parts[2])

    m = get_map(map_id)
    if not m or m["owner_id"] != user_id:
        await callback.answer(t("map.err.not_yours", lang), show_alert=True)
        return

    from db.map_items import get_map_sections as _get_secs
    season = get_current_season()
    layer = 1
    sections = _get_secs(map_id, season, layer)

    if not sections:
        await callback.answer(t("map.no_sections", lang), show_alert=True)
        return

    session = player.get("current_session", "")
    text = (
        "✏️ <b>" + t('map.edit_sections_title', lang) + "</b>\n"
        + "<i>" + m['name'] + " · " + t('map.layer_line', lang, layer=layer) + "</i>\n\n"
        + t('map.edit_sections_help', lang)
    )

    kb = map_sections_keyboard(lang, map_id, sections, player, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_map_edit_section(callback: CallbackQuery):
    from config import BOT_TOKEN
    from aiogram import Bot
    from keyboards.maps import map_section_edit_keyboard
    from db.map_items import get_section_on_map

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) < 4:
        return
    map_id = int(parts[2])
    section_id = parts[3]

    m = get_map(map_id)
    if not m or m["owner_id"] != user_id:
        await callback.answer(t("map.err.not_yours", lang), show_alert=True)
        return

    season = get_current_season()
    layer = player.get("maze_layer", 1) or 1

    sec = get_section_on_map(map_id, season, layer, section_id)
    if not sec:
        await callback.answer(t("map.err.section_not_found", lang), show_alert=True)
        return

    name = sec["custom_name"] or sec["section_id"]
    note = sec["note"] or t("map.no_note", lang)

    text = (
        "✏️ <b>" + name + "</b>\n"
        + "<i>ID: " + sec['section_id'] + "</i>\n\n"
        + "📝 " + note
    )

    session = player.get("current_session", "")
    kb = map_section_edit_keyboard(lang, map_id, section_id, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()
