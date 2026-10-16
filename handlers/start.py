# handlers/start.py

from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from core.bot_helpers import refresh_main
from db.players import get_player


async def cmd_start(message: Message, bot: Bot):
    user = message.from_user
    player = get_player(user.id)

    # Уже есть персонаж
    if player:
        # Intro не завершён — продолжить
        if not player.get("intro_done"):
            from handlers.intro import start_intro
            await start_intro(bot, user.id, player["language"])
            try:
                await message.delete()
            except Exception:
                pass
            return

        # Intro завершён — показать главный экран
        await refresh_main(bot, user.id)

        try:
            await message.delete()
        except Exception:
            pass
        return

    # Первый раз — выбор языка
    from keyboards.language import language_keyboard

    text = (
        t("lang.choose", "en") + "\n" +
        t("lang.choose", "ru")
    )
    await message.answer(text, reply_markup=language_keyboard())
