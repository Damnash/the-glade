# handlers/work.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from core.time_utils import humanize_seconds
from content.work import WORK_TYPES
from db.players import get_player, get_lang, update_player_fields
from services.work import (
    start_work, collect_rewards, available_works, WorkError,
)


def format_rewards(rewards: dict, lang: str) -> str:
    icons = {"food": "🍞", "tokens": "🪙", "water": "💧"}
    return ", ".join(f"{icons.get(k, k)} +{v}" for k, v in rewards.items())


async def cmd_work(message: Message):
    lang = get_lang(message.from_user.id)
    player = get_player(message.from_user.id)
    if not player:
        await message.answer(t("start.need_start", lang))
        return

    # Если работа уже закончилась — соберём награду
    rewards = collect_rewards(message.from_user.id)
    if rewards:
        await message.answer(t("work.done", lang, rewards=format_rewards(rewards, lang)))
        return

    args = message.text.split(maxsplit=1)

    # Без аргумента — показать доступное
    if len(args) < 2:
        works = available_works(player)
        if not works:
            await message.answer(t("work.no_work_here", lang))
            return

        lines = [t("work.list_header", lang)]
        for key in works:
            spec = WORK_TYPES[key]
            reward = format_rewards(spec["rewards"], lang)
            lines.append(
                t("work.list_line", lang,
                  work_key=key,
                  duration=humanize_seconds(spec["duration_sec"], lang),
                  energy=spec["energy_cost"],
                  reward=reward)
            )
        await message.answer("\n".join(lines))
        return

    work_type = args[1].strip().lower()

    try:
        info = start_work(message.from_user.id, work_type)
    except WorkError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(
        t("work.started", lang,
          work=t(f"work.{work_type}", lang),
          duration=humanize_seconds(info["duration"], lang))
    )