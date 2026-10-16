# handlers/say.py

from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from core.bot_helpers import refresh_main
from db.players import get_player, get_lang, players_in_location
from services.event_log import add_event, cleanup_old_events


async def cmd_say(message: Message, bot: Bot):
    """/с <текст> — сказать в локации."""
    user_id = message.from_user.id
    sender = get_player(user_id)
    lang = get_lang(user_id)

    if not sender:
        await message.answer(t("start.need_start", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("say.no_args", lang))
        return

    text = parts[1].strip()
    if len(text) > 300:
        await message.answer(t("say.too_long", lang))
        return

    sender_name = sender["display_name"] or sender["username"]
    location = sender["location"]
    maze_layer = sender.get("maze_layer", 0)

    # Лог
    add_event(user_id, "say", t("log.say_sent", lang, text=text))
    cleanup_old_events(user_id)

    # Уведомления другим
    message_text = t("say.format", lang, name=sender_name, text=text)
    others = players_in_location(location, exclude_id=user_id)

    for p in others:
        if maze_layer > 0:
            if p.get("maze_layer", 0) != maze_layer:
                continue
            if p.get("maze_section") != sender.get("maze_section"):
                continue

        try:
            # Лог получателю
            target_lang = p.get("language", "ru")
            add_event(p["user_id"], "say_received",
                      t("log.say_received", target_lang, name=sender_name, text=text))
            # Обновить его главное
            await refresh_main(bot, p["user_id"])
        except Exception:
            pass

    # Обновить свой
    await refresh_main(bot, user_id)

    # Удалить сообщение игрока
    try:
        await message.delete()
    except Exception:
        pass
