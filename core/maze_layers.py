# core/maze_layers.py

from core.maze_current import get_season_day


LAYER_UNLOCK_DAY = {
    1: 1,
    2: 30,
    3: 60,
}


def get_max_layer(season_id: int) -> int:
    """Сколько слоёв открыто сейчас."""
    from core.season import get_active_players_count

    day = get_season_day(season_id)
    active = get_active_players_count()

    if day < LAYER_UNLOCK_DAY[2]:
        return 1

    if day < LAYER_UNLOCK_DAY[3]:
        return 2 if active >= 15 else 1

    if active >= 30:
        return 3
    if active >= 15:
        return 2
    return 1


def is_layer_available(season_id: int, layer: int) -> bool:
    return layer <= get_max_layer(season_id)


def get_layer_info(season_id: int) -> dict:
    from core.season import get_active_players_count

    day = get_season_day(season_id)
    max_layer = get_max_layer(season_id)
    active = get_active_players_count()

    return {
        "day": day,
        "max_layer": max_layer,
        "active_players": active,
        "layer_unlock_days": LAYER_UNLOCK_DAY,
    }
