# handlers/sleep.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from core.time_utils import humanize_seconds
from core.player_state import update_player_state
from db.players import get_player, get_lang
from services.sleep import sleep, wake, SleepError
from services.work import collect_rewards


async def cmd_sleep(message: Message):
    lang = get_lang(message.from_user.id)

    # Если завершилась работа — соберём награду
    rewards = collect_rewards(message.from_user.id)

    try:
        sleep(message.from_user.id)
    except SleepError as e:
        await message.answer(t(e.key, lang))
        return

    await message.answer(t("sleep.started", lang))


async def cmd_wake(message: Message):
    lang = get_lang(message.from_user.id)
    try:
        player = wake(message.from_user.id)
    except SleepError as e:
        await message.answer(t(e.key, lang))
        return

    await message.answer(
        t("sleep.woke", lang, hp=player["hp"], energy=player["energy"])
    )