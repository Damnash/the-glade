# handlers/radio.py

from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from core.bot_helpers import check_session, edit_main, refresh_main, command_reply
from db.players import get_player, get_lang, players_in_location
from keyboards.radio import radio_menu_keyboard
from services.radio import (
    get_radio, set_frequency, toggle_radio,
    send_on_frequency, get_freq_history,
    send_radio_center, get_radio_history,
    resolve_encrypted_target, format_frequency, parse_frequency,
    RadioError,
)
from services.event_log import add_event, cleanup_old_events
from core.bot_helpers import make_bot


# ============ Команды ============

async def cmd_walkie(message: Message):
    """/рация."""
    user_id = message.from_user.id
    lang = get_lang(user_id)
    player = get_player(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        freq = parse_frequency(parts[1])
        if freq is None:
            await message.answer(t("radio.manual_invalid", lang, input=parts[1].strip()))
        else:
            set_frequency(user_id, freq)
            await message.answer(t("radio.set_done", lang, freq=format_frequency(freq)))

    radio = get_radio(user_id)
    freq_str = format_frequency(radio["frequency"])
    status = "OK" if radio["is_on"] else "OFF"

    text = (
        "<b>" + t("radio.title", lang) + "</b>\n\n"
        + t("radio.freq_label", lang) + ": <b>" + freq_str + "</b>\n"
        + t("radio.status_label", lang) + ": " + status
    )

    session = player.get("current_session", "")
    kb = radio_menu_keyboard(lang, radio, session)

    await command_reply(message, text, kb)


async def cmd_walkie_talk(message: Message, bot: Bot):
    """/г <текст>."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("radio.enter_text", lang, freq="---"))
        return

    text = parts[1].strip()
    if len(text) > 300:
        await message.answer(t("radio.too_long", lang))
        return

    try:
        result = send_on_frequency(user_id, text)
    except RadioError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    freq_str = format_frequency(result["frequency"])

    add_event(user_id, "radio", t("log.radio_sent", lang, freq=freq_str, text=text))
    cleanup_old_events(user_id)

    # Уведомления
    for listener_id in result["listeners"]:
        listener_lang = get_lang(listener_id)
        try:
            add_event(listener_id, "radio_received",
                      t("log.radio_received", listener_lang, freq=freq_str,
                        name=result["sender_name"], text=text))
            cleanup_old_events(listener_id)
            await refresh_main(bot, listener_id)
        except Exception:
            pass

    await refresh_main(bot, user_id)

    try:
        await message.delete()
    except Exception:
        pass


async def cmd_radio(message: Message, bot: Bot):
    """/радио."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    if player["location"] != "center":
        await message.answer(t("radio.not_center", lang))
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        history = get_radio_history(limit=15)
        lines = ["<b>" + t("radio.center_title", lang) + "</b>\n"]
        lines.append(t("radio.center_freq", lang) + "\n")

        if history:
            for m in history:
                time_short = str(m["sent_at"])[11:16]
                if m["encrypted_for"]:
                    if m["encrypted_for"] == user_id or m["user_id"] == user_id:
                        lines.append("[" + time_short + "] " + m["display_name"] + ": " + m["text"])
                    else:
                        lines.append("[" + time_short + "] " + m["display_name"] + ": [lock]")
                else:
                    lines.append("[" + time_short + "] " + m["display_name"] + ": " + m["text"])
        else:
            lines.append(t("radio.center_empty", lang))

        await command_reply(message, "\n".join(lines))
        return

    text = parts[1].strip()
    if len(text) > 300:
        await message.answer(t("radio.too_long", lang))
        return

    encrypted_for, clean_text = resolve_encrypted_target(text)
    result = send_radio_center(user_id, clean_text, encrypted_for)

    # Лог
    add_event(user_id, "radio_center",
              "📻 " + t("radio.center_sent", lang, text=clean_text))
    cleanup_old_events(user_id)

    # Уведомления всем в центре
    others = players_in_location("center", exclude_id=user_id)
    for p in others:
        target_lang = p["language"]
        if encrypted_for and p["user_id"] == encrypted_for:
            txt = t("radio.center_received_personal", target_lang,
                    name=result["sender_name"], text=clean_text)
        elif encrypted_for:
            txt = t("radio.center_received_encrypted", target_lang, name=result["sender_name"])
        else:
            txt = t("radio.center_received", target_lang, name=result["sender_name"], text=clean_text)

        try:
            add_event(p["user_id"], "radio_center", "📻 " + txt)
            cleanup_old_events(p["user_id"])
            await refresh_main(bot, p["user_id"])
        except Exception:
            pass

    await refresh_main(bot, user_id)

    try:
        await message.delete()
    except Exception:
        pass


# ============ Callbacks ============

async def on_radio_menu(callback: CallbackQuery):
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

    radio = get_radio(user_id)
    freq_str = format_frequency(radio["frequency"])
    status = "OK" if radio["is_on"] else "OFF"

    text = (
        "<b>" + t("radio.title", lang) + "</b>\n\n"
        + t("radio.freq_label", lang) + ": <b>" + freq_str + "</b>\n"
        + t("radio.status_label", lang) + ": " + status
    )

    session = player.get("current_session", "")
    kb = radio_menu_keyboard(lang, radio, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_radio_manual(callback: CallbackQuery):
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

    text = (
        "<b>" + t("radio.manual_title", lang) + "</b>\n\n"
        + t("radio.manual_help", lang)
    )

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="radio:menu" + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_radio_toggle(callback: CallbackQuery):
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

    new_state = toggle_radio(user_id)

    if new_state:
        await callback.answer(t("radio.turned_on", lang))
    else:
        await callback.answer(t("radio.turned_off", lang))

    await on_radio_menu(callback)


async def on_radio_history(callback: CallbackQuery):
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

    radio = get_radio(user_id)
    freq = radio["frequency"]
    messages = get_freq_history(freq, limit=20)
    freq_str = format_frequency(freq)

    if not messages:
        await callback.answer(t("radio.history_empty", lang), show_alert=True)
        return

    lines = ["<b>" + t("radio.history_title", lang) + " " + freq_str + "</b>\n"]
    for m in messages:
        time_short = str(m["sent_at"])[11:16]
        lines.append("[" + time_short + "] " + m["display_name"] + ": " + m["text"])

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="radio:menu" + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, "\n".join(lines), kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_radio_talk(callback: CallbackQuery):
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

    radio = get_radio(user_id)
    if not radio["is_on"]:
        await callback.answer(t("radio.off", lang), show_alert=True)
        return

    freq_str = format_frequency(radio["frequency"])

    text = (
        "<b>" + t("radio.talk_title", lang) + "</b>\n\n"
        + t("radio.enter_text", lang, freq=freq_str)
    )

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data="radio:menu" + s)
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


# ============ FSM: приём текста в рацию ============

async def process_radio_message(message, state, bot):
    """Приём текста в рацию."""
    from handlers.radio_states import RadioTalkState

    user_id = message.from_user.id
    player = get_player(user_id)
    lang = player["language"] if player else "ru"

    await state.clear()

    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return

    if len(text) > 300:
        await message.answer(t("radio.too_long", lang))
        return

    try:
        result = send_on_frequency(user_id, text)
    except RadioError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    freq_str = format_frequency(result["frequency"])

    from services.event_log import add_event, cleanup_old_events
    add_event(user_id, "radio", t("log.radio_sent", lang, freq=freq_str, text=text))
    cleanup_old_events(user_id)

    await refresh_main(bot, user_id)

    for listener_id in result["listeners"]:
        listener_lang = get_lang(listener_id)
        try:
            add_event(listener_id, "radio_received",
                      t("log.radio_received", listener_lang,
                        freq=freq_str, name=result["sender_name"], text=text))
            cleanup_old_events(listener_id)
            await refresh_main(bot, listener_id)
        except Exception:
            pass

    try:
        await message.delete()
    except Exception:
        pass
