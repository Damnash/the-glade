# handlers/achievements.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from core.maze_current import get_current_season, get_season_day
from content.achievements import ACHIEVEMENTS
from db.players import get_player, get_lang
from db.achievements import (
    get_player_achievements, get_player_score,
    get_leaderboard, get_top_by_field,
    get_hall_of_fame,
)
from services.achievements import get_full_leaderboard
from core.bot_helpers import command_reply


async def cmd_achievements(message: Message):
    """/звания — мои звания."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    keys = get_player_achievements(user_id)

    lines = [f"🏆 <b>{t('ach.title', lang)}</b>\n"]

    if not keys:
        lines.append(t("ach.empty", lang))
    else:
        for key in keys:
            spec = ACHIEVEMENTS.get(key, {})
            icon = spec.get("icon", "❓")
            name = t(spec.get("name_key", f"ach.{key}.name"), lang)
            lines.append(f"{icon} <b>{name}</b>")

    await command_reply("\n".join(lines))

    from handlers.location_render import send_current_context
    await send_current_context(message, message.from_user.id)

    # command_reply импортируется в шапке файла

async def cmd_leaderboard(message: Message):
    """/топ — таблица лидеров."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    season = get_current_season()
    day = get_season_day(season)

    data = get_full_leaderboard(season)

    lines = [
        f"🏆 <b>{t('top.title', lang)}</b>",
        f"<i>{t('stats.season_line', lang, season=season, day=day)}</i>",
        "",
    ]

    # Основной топ
    lines.append(f"<b>{t('top.by_score', lang)}</b>")
    if data["score"]:
        for i, entry in enumerate(data["score"][:10], 1):
            name = entry["display_name"] or entry["username"] or "?"
            lines.append(f"  {i}. {name} — {entry['score']}")
    else:
        lines.append(f"  {t('top.empty', lang)}")

    lines.append("")

    # Убийства
    if data["kills"]:
        lines.append(f"<b>{t('top.by_kills', lang)}</b>")
        for i, entry in enumerate(data["kills"], 1):
            name = entry["display_name"] or entry["username"] or "?"
            lines.append(f"  {i}. {name} — {entry['kills']}")
        lines.append("")

    # Гриверы
    if data["griever_kills"]:
        lines.append(f"<b>{t('top.by_grievers', lang)}</b>")
        for i, entry in enumerate(data["griever_kills"], 1):
            name = entry["display_name"] or entry["username"] or "?"
            lines.append(f"  {i}. {name} — {entry['griever_kills']}")
        lines.append("")

    # Фрагменты
    if data["fragments"]:
        lines.append(f"<b>{t('top.by_fragments', lang)}</b>")
        for i, entry in enumerate(data["fragments"], 1):
            name = entry["display_name"] or entry["username"] or "?"
            lines.append(f"  {i}. {name} — {entry['fragments']}")

    await command_reply("\n".join(lines).rstrip())

    # Вернуть контекст
    from handlers.location_render import send_current_context
    await send_current_context(message, message.from_user.id)

    # command_reply импортируется в шапке файла

async def cmd_hall_of_fame(message: Message):
    """/зал_славы — вечный зал."""
    lang = get_lang(message.from_user.id)

    entries = get_hall_of_fame(limit=100)

    if not entries:
        await message.answer(t("hall.empty", lang))
        return

    lines = [f"🏛️ <b>{t('hall.title', lang)}</b>\n"]

    # Группируем по сезону
    by_season = {}
    for e in entries:
        sid = e["season_id"]
        by_season.setdefault(sid, []).append(e)

    for sid in sorted(by_season.keys(), reverse=True):
        lines.append(f"<b>{t('hall.season', lang, n=sid)}</b>")
        for e in by_season[sid]:
            spec = ACHIEVEMENTS.get(e["achievement_key"], {})
            icon = spec.get("icon", "🏆")
            name = e["display_name"]

            # Название звания
            ach_name_key = spec.get("name_key", f"ach.{e['achievement_key']}.name")
            ach_name = t(ach_name_key, lang)

            lines.append(f"  {icon} {name} — {ach_name}")
        lines.append("")

    await command_reply("\n".join(lines).rstrip())

    from handlers.location_render import send_current_context
    await send_current_context(message, message.from_user.id)

    # command_reply импортируется в шапке файла
