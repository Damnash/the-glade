# handlers/whisper.py

from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from core.bot_helpers import refresh_main
from db.players import get_player, get_lang
from services.event_log import add_event, cleanup_old_events
from services.whisper import send_whisper, WhisperError


async def cmd_whisper(message: Message, bot: Bot):
    """/ш <ник> <текст>."""
    user_id = message.from_user.id
    lang = get_lang(user_id)

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(t("whisper.no_args", lang))
        return

    nick = parts[1]
    text = parts[2]

    if len(text) > 300:
        await message.answer(t("whisper.too_long", lang))
        return

    try:
        result = send_whisper(user_id, nick, text)
    except WhisperError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    sender = get_player(user_id)
    sender_name = sender["display_name"] or sender["username"]

    # Лог отправителю
    add_event(user_id, "whisper", t("log.whisper_sent", lang,
                                     name=result["to_name"], text=text))
    cleanup_old_events(user_id)

    # Лог получателю
    target_lang = get_lang(result["to_id"])
    add_event(result["to_id"], "whisper",
              t("log.whisper_received", target_lang, name=sender_name, text=text))
    cleanup_old_events(result["to_id"])

    # Обновить обоим
    try:
        await refresh_main(bot, result["to_id"])
    except Exception:
        pass

    await refresh_main(bot, user_id)

    try:
        await message.delete()
    except Exception:
        pass
