# handlers/stats.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from core.player_state import update_player_state
from core.time_utils import seconds_until, humanize_seconds
from db.players import get_player, get_lang


async def cmd_stats(message: Message):
    lang = get_lang(message.from_user.id)
    player = update_player_state(get_player(message.from_user.id))

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    name = player["display_name"] or player["username"] or "Runner"
    loc = t(f"loc.{player['location']}.name", lang)
    status = t(f"status.{player['status']}", lang)

    from core.maze_current import get_current_season, get_season_day
    from core.daycycle import format_time_line
    season = get_current_season()
    day = get_season_day(season)
    time_line = format_time_line(lang)

    # Баффы
    buffs_line = ""
    try:
        from services.buffs import format_buffs_for_display
        b_disp = format_buffs_for_display(message.from_user.id, lang)
        if b_disp:
            buffs_line = b_disp
    except Exception:
        pass

    # Профессия и перк
    prof_key = player.get("profession")
    perk_key = player.get("perk")

    prof_line = ""
    if prof_key:
        from content.professions import PROFESSIONS
        prof = PROFESSIONS.get(prof_key)
        if prof:
            prof_name = t(prof["name_key"], lang)
            prof_line = t("stats.profession_line", lang, name=prof_name)

    perk_line = ""
    if perk_key:
        from content.professions import PERKS
        perk = PERKS.get(perk_key)
        if perk:
            perk_name = t(perk["name_key"], lang)
            perk_line = t("stats.perk_line", lang, name=perk_name)

    from services.bonuses import get_player_bonus
    bonus = get_player_bonus(player)

    # Титул (если есть)
    title_line = ""
    try:
        from services.titles import get_player_title_display
        t_disp = get_player_title_display(user_id, lang)
        if t_disp:
            title_line = t_disp
    except Exception:
        pass

    lines = [
        f"{t('stats.header_name', lang, name=name)}",
    ]
    if title_line:
        lines.append(f"<i>{title_line}</i>")
    lines.append("")

    if prof_line:
        lines.append(prof_line)
    if perk_line:
        lines.append(perk_line)

    if prof_line or perk_line:
        lines.append("")

    lines.extend([
        t("stats.line_bonus", lang,
          hp=player["hp"], max_hp=bonus["max_hp"],
          energy=player["energy"], max_energy=bonus["max_energy"],
          sanity=player.get("sanity", 100),
          food=player["food"], water=player["water"],
          max_food=player.get("max_food", 10),
          max_water=player.get("max_water", 5),
          tokens=player.get("tokens", 0)),
        "",
        t("stats.season_line", lang, season=season, day=day),
        time_line,
    ] + ([buffs_line] if buffs_line else []) + [
        t("stats.location_line", lang, loc=loc),
        t("stats.status_line", lang, status=status),
    ])

    if player["status"] == "working" and player.get("work_ends_at"):
        left = seconds_until(player["work_ends_at"])
        lines.append(t("stats.work_left", lang, time=humanize_seconds(left, lang)))

    await message.answer("\n".join(lines))
