# services/eat.py

from core.time_utils import now
from db.players import get_player, update_player_fields
from core.player_state import update_player_state


class EatError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


def eat(user_id: int) -> dict:
    player = update_player_state(get_player(user_id))
    if not player:
        raise EatError("start.need_start")

    if player["food"] <= 0:
        raise EatError("eat.no_food")

    update_player_fields(user_id, {
        "food": player["food"] - 1,
        "last_fed_at": now(),
        "hp": min(100, player["hp"] + 5),  # +5 HP за еду
    })

    return {"hp": min(100, player["hp"] + 5), "food": player["food"] - 1}