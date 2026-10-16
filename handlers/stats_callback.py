# handlers/stats_callback.py

from aiogram.types import CallbackQuery

from core.i18n import t
from db.players import get_player


async def on_stats(callback: CallbackQuery):
    """Статы — popup."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        await callback.answer("No character.", show_alert=True)
        return

    lang = player["language"]
    loc_name = t(f"loc.{player['location']}.name", lang)
    status = t(f"status.{player['status']}", lang)
    name = player["display_name"] or player["username"]

    from core.maze_current import get_current_season, get_season_day
    from core.daycycle import format_time_line
    season = get_current_season()
    day = get_season_day(season)
    time_line = format_time_line(lang)

    # БЕЗ HTML — popup не поддерживает
    text = (
        f"{t('stats.header_name', lang, name=name)}\n\n"
        + t("stats.line_popup", lang,
            hp=player["hp"], energy=player["energy"],
            sanity=player.get("sanity", 100),
            food=player["food"], water=player["water"],
            max_food=player.get("max_food", 10),
            max_water=player.get("max_water", 5),
            tokens=player.get("tokens", 0))
        + "\n\n"
        + t("stats.season_line", lang, season=season, day=day)
        + f"\n{time_line}"
        + f"\n{t('stats.location_line', lang, loc=loc_name)}"
        + f"\n{t('stats.status_line', lang, status=status)}"
    )

    await callback.answer(text, show_alert=True)
