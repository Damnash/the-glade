# handlers/clans.py

from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from core.bot_helpers import check_session, edit_main, refresh_main, command_reply, make_bot
from db.players import get_player, get_lang, find_by_name
from keyboards.clans import (
    clan_main_keyboard, clan_no_clan_keyboard,
    clan_invites_keyboard, clan_confirm_leave_keyboard,
)
from services.clans import (
    create, invite, accept_invite, set_role, leave, kick, donate,
    send_clan_message, sync_map_from_player, get_clan_map,
    ClanError, MAX_MEMBERS, CREATE_COST,
)
from db.clans import (
    get_player_clan, get_player_role, get_clan_members,
    get_pending_invites, get_clan, count_clan_members,
)


def render_clan_main(lang: str, clan: dict, role: str, members_count: int) -> str:
    role_key = "clan.role." + role
    return (
        "👥 <b>" + t('clan.title', lang) + " «" + clan['name'] + "»</b>\n\n"
        + t('clan.members_line', lang, n=members_count, max=MAX_MEMBERS) + "\n"
        + t('clan.treasury_line', lang, treasury=clan['treasury']) + "\n"
        + t('clan.role_line', lang, role=t(role_key, lang)) + "\n"
        + ("💬 <i>" + clan['motto'] + "</i>\n" if clan.get('motto') else "")
    )


def _render_main(lang: str, user_id: int):
    clan = get_player_clan(user_id)
    if clan:
        role = get_player_role(user_id) or "recruit"
        count = count_clan_members(clan["clan_id"])
        session = get_player(user_id).get("current_session", "")
        return render_clan_main(lang, clan, role, count), clan_main_keyboard(lang, session)
    else:
        text = (
            "👥 <b>" + t('clan.title', lang) + "</b>\n\n"
            + t('clan.no_clan_text', lang) + "\n\n"
            + t('clan.create_cost_line', lang, cost=CREATE_COST)
        )
        session = get_player(user_id).get("current_session", "")
        return text, clan_no_clan_keyboard(lang, session)


# ============ Команда ============

async def cmd_clan(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    text, kb = _render_main(lang, user_id)
    await command_reply(message, text, kb)


# ============ Команды создания ============

async def cmd_clan_create(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("clan.create_usage", lang))
        return

    name = parts[1].strip()

    try:
        create(user_id, name)
    except ClanError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(t("clan.created", lang, name=name))

    text, kb = _render_main(lang, user_id)
    await message.answer(text, reply_markup=kb)


async def cmd_clan_invite(message: Message, bot: Bot):
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    clan = get_player_clan(user_id)
    if not clan:
        await message.answer(t("clan.err.not_in_clan", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("clan.invite_usage", lang))
        return

    nick = parts[1].strip()
    target = find_by_name(nick)
    if not target:
        await message.answer(t("clan.err.player_not_found", lang))
        return

    try:
        invite(clan["clan_id"], user_id, target["user_id"])
    except ClanError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(t("clan.invite_sent", lang, name=target["display_name"] or target["username"]))

    target_lang = target["language"]
    try:
        await bot.send_message(
            chat_id=target["user_id"],
            text=t("clan.invite_received", target_lang, name=clan["name"]),
        )
    except Exception:
        pass


async def cmd_clan_chat(message: Message, bot: Bot):
    from services.event_log import add_event, cleanup_old_events

    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("clan.chat_usage", lang))
        return

    text = parts[1].strip()
    if len(text) > 300:
        await message.answer(t("clan.chat_too_long", lang))
        return

    try:
        result = send_clan_message(user_id, text)
    except ClanError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    add_event(user_id, "clan", t("log.clan_sent", lang, text=text), severity="chat")
    cleanup_old_events(user_id)

    for uid in result["recipients"]:
        try:
            target_lang = get_lang(uid)
            add_event(uid, "clan", t("log.clan_received", target_lang,
                                      name=result["display_name"], text=text), severity="chat")
            cleanup_old_events(uid)
            await refresh_main(bot, uid)
        except Exception:
            pass

    await refresh_main(bot, user_id)

    try:
        await message.delete()
    except Exception:
        pass


# ============ Callbacks ============

async def on_clan_main(callback: CallbackQuery):
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

    text, kb = _render_main(lang, user_id)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_clan_members(callback: CallbackQuery):
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

    clan = get_player_clan(user_id)
    if not clan:
        await callback.answer(t("clan.err.not_in_clan", lang), show_alert=True)
        return

    members = get_clan_members(clan["clan_id"])
    lines = ["👥 <b>" + t('clan.members_title', lang) + "</b>\n"]
    for m in members:
        name = m["display_name"] or m["username"] or "?"
        role_label = t("clan.role." + m['role'], lang)
        lines.append("  " + role_label + " — " + name)

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="clan:main" + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, "\n".join(lines), kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_clan_chat(callback: CallbackQuery):
    from config import BOT_TOKEN
    from aiogram import Bot
    from db.clans import get_clan_messages

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    clan = get_player_clan(user_id)
    if not clan:
        await callback.answer(t("clan.err.not_in_clan", lang), show_alert=True)
        return

    messages = get_clan_messages(clan["clan_id"], limit=20)

    lines = ["💬 <b>" + t('clan.chat_title', lang) + " «" + clan['name'] + "»</b>\n"]
    if not messages:
        lines.append(t("clan.chat_empty", lang))
    else:
        for m in messages:
            time_short = str(m["sent_at"])[11:16]
            lines.append("[" + time_short + "] " + m['display_name'] + ": " + m['text'])

    lines.append("")
    lines.append(t("clan.chat_hint", lang))

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="clan:main" + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, "\n".join(lines), kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_clan_map(callback: CallbackQuery):
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

    clan = get_player_clan(user_id)
    if not clan:
        await callback.answer(t("clan.err.not_in_clan", lang), show_alert=True)
        return

    try:
        added = sync_map_from_player(user_id)
    except ClanError:
        added = 0

    data = get_clan_map(clan["clan_id"], layer=1)
    sections = data["sections"]

    lines = ["🗺️ <b>" + t('clan.map_title', lang) + " «" + clan['name'] + "»</b>\n"]
    lines.append(t("clan.map_count", lang, n=len(sections)))
    if added:
        lines.append(t("clan.map_added", lang, n=added))
    lines.append("")

    if sections:
        for s in sections[:30]:
            lines.append("  • " + s['section_id'])
    else:
        lines.append(t("clan.map_empty", lang))

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="clan:main" + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, "\n".join(lines), kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_clan_treasury(callback: CallbackQuery):
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

    clan = get_player_clan(user_id)
    if not clan:
        await callback.answer(t("clan.err.not_in_clan", lang), show_alert=True)
        return

    text = (
        "💰 <b>" + t('clan.treasury_title', lang) + "</b>\n\n"
        + t('clan.treasury_amount', lang, treasury=clan['treasury']) + "\n\n"
        + t('clan.treasury_hint', lang)
    )

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="clan:main" + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_clan_invites(callback: CallbackQuery):
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

    invites = get_pending_invites(user_id)

    if not invites:
        await callback.answer(t("clan.no_invites", lang), show_alert=True)
        return

    lines = ["📨 <b>" + t('clan.invites_title', lang) + "</b>\n"]
    for inv in invites:
        lines.append("  • «" + inv['clan_name'] + "»")

    session = player.get("current_session", "")
    kb = clan_invites_keyboard(lang, invites, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, "\n".join(lines), kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_clan_accept(callback: CallbackQuery):
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
    invite_id = int(parts[2])

    try:
        clan_id = accept_invite(user_id, invite_id)
    except ClanError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    clan = get_clan(clan_id)
    await callback.answer(t("clan.joined", lang, name=clan["name"]), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def on_clan_leave(callback: CallbackQuery):
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

    session = player.get("current_session", "")
    kb = clan_confirm_leave_keyboard(lang, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, t("clan.leave_confirm_text", lang), kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_clan_leave_confirm(callback: CallbackQuery):
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
        leave(user_id)
    except ClanError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    await callback.answer(t("clan.left", lang), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def on_clan_invite_help(callback: CallbackQuery):
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

    text = t("clan.invite_help", lang)

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="clan:main" + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_clan_create_help(callback: CallbackQuery):
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

    text = t("clan.create_help", lang, cost=CREATE_COST)

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="clan:main" + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()

# ============ Открытые кланы ============

async def on_clan_open_list(callback):
    """Список открытых кланов."""
    from core.bot_helpers import check_session, edit_main, make_bot
    from db.clans import get_open_clans
    from keyboards.clans import clan_open_list_keyboard

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    clans = get_open_clans(limit=10)
    if not clans:
        await callback.answer(t("clan.open.empty", lang), show_alert=True)
        return

    session = player.get("current_session", "")
    text = f"👥 <b>{t('clan.open.title', lang)}</b>\n\n{t('clan.open.pick', lang)}"
    kb = clan_open_list_keyboard(lang, clans, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_clan_open_detail(callback):
    """Детали открытого клана (clan:open:<id>)."""
    from core.bot_helpers import check_session, edit_main, make_bot
    from db.clans import get_clan, count_clan_members
    from keyboards.clans import clan_open_detail_keyboard
    from services.clans import MAX_MEMBERS

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # clan:open:<id>:session
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    try:
        clan_id = int(parts[2])
    except ValueError:
        return

    clan = get_clan(clan_id)
    if not clan:
        await callback.answer(t("clan.err.clan_not_found", lang), show_alert=True)
        return

    if not clan.get("is_open"):
        await callback.answer(t("clan.err.not_open", lang), show_alert=True)
        return

    members = count_clan_members(clan_id)
    text = (
        f"👥 <b>{clan['name']}</b>\n\n"
        + t("clan.open.members_line", lang, n=members, max=MAX_MEMBERS) + "\n"
        + (f"💬 <i>{clan['motto']}</i>\n" if clan.get("motto") else "")
    )
    session = player.get("current_session", "")
    kb = clan_open_detail_keyboard(lang, clan_id, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_clan_join(callback):
    """Вступить в открытый клан (clan:join:<id>)."""
    from core.bot_helpers import check_session, refresh_main, make_bot
    from services.clans import join_open_clan, ClanError

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
    try:
        clan_id = int(parts[2])
    except ValueError:
        return

    try:
        result = join_open_clan(user_id, clan_id)
    except ClanError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    await callback.answer(t("clan.joined", lang, name=result["clan_name"]), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def on_clan_toggle_open(callback):
    """Лидер открывает/закрывает клан."""
    from core.bot_helpers import check_session, refresh_main, make_bot
    from services.clans import set_open, ClanError

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # clan:toggle_open:on / clan:toggle_open:off
    is_open = "on" in callback.data
    try:
        new_state = set_open(user_id, is_open)
    except ClanError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    if new_state:
        await callback.answer(t("clan.open.opened", lang))
    else:
        await callback.answer(t("clan.open.closed", lang))

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()

