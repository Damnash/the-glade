# services/maze_fragments.py

import random

from core.maze_current import get_current_season
from db.maze_state import (
    can_find_fragment,
    is_discovered,
    log_fragment_find,
    mark_discovered,
)


FRAGMENT_CHANCE = 0.08   # 8% базово


def try_find_fragment(user_id: int, section_id: str, layer: int) -> bool:
    """
    Пытается найти фрагмент карты.
    Возвращает True, если фрагмент найден.
    """
    # Шанс с бонусом профессии/перка
    from db.players import get_player
    from services.bonuses import get_player_bonus

    player = get_player(user_id)
    if not player:
        return False

    bonus = get_player_bonus(player)
    chance = FRAGMENT_CHANCE + bonus["fragment_chance"]

    if random.random() > chance:
        return False

    season = get_current_season()

    # Уже открыта?
    if is_discovered(season, layer, section_id):
        return False

    # Лимит дня?
    if not can_find_fragment(season):
        return False

    # Нашли!
    mark_discovered(season, layer, section_id, user_id)
    log_fragment_find(season, user_id, section_id)

    # Story tracking
    try:
        from services.story import track_event
        track_event(user_id, "find_fragments")
    except Exception:
        pass

    return True
