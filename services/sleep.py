# services/sleep.py

from core.player_state import update_player_state, ENERGY_MAX, HP_MAX
from core.time_utils import now
from db.players import get_player, update_player_fields


class SleepError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


def sleep(user_id: int) -> dict:
    player = update_player_state(get_player(user_id))
    if not player:
        raise SleepError("start.need_start")

    # Нельзя спать в Лабиринте
    if player.get("maze_layer", 0) > 0:
        raise SleepError("sleep.in_maze")

    if player["status"] == "sleeping":
        raise SleepError("sleep.already")

    if player["status"] == "working":
        raise SleepError("sleep.busy")

    if player["energy"] >= ENERGY_MAX and player["hp"] >= HP_MAX:
        raise SleepError("sleep.not_tired")

    update_player_fields(user_id, {
        "status": "sleeping",
        "last_seen": now(),
    })

    return {"energy": player["energy"], "hp": player["hp"]}


def wake(user_id: int) -> dict:
    player = update_player_state(get_player(user_id))
    if not player:
        raise SleepError("start.need_start")

    if player["status"] != "sleeping":
        raise SleepError("wake.not_sleeping")

    update_player_fields(user_id, {
        "status": "active",
        "last_seen": now(),
    })
    return player