# services/movement.py

from content.locations import LOCATIONS
from core.player_state import update_player_state
from core.time_utils import parse_dt, seconds_until, humanize_seconds, now
from db.players import get_player, update_location


class MoveError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


def move(user_id: int, target: str):
    player = update_player_state(get_player(user_id))
    if not player:
        raise MoveError("start.need_start")

    if player.get("maze_layer", 0) > 0:
        raise MoveError("move.in_maze")

    if player["status"] == "sleeping":
        raise MoveError("move.sleeping")

    if player["status"] == "working":
        ends_at = parse_dt(player.get("work_ends_at"))
        if ends_at and now() >= ends_at:
            # Работа готова — надо забрать
            raise MoveError("move.working_done")
        else:
            # Работа ещё идёт
            left = seconds_until(ends_at)
            raise MoveError("move.working_busy",
                            time=humanize_seconds(left, player["language"]))

    target = target.strip().lower().replace(" ", "_").replace("-", "_")

    if target not in LOCATIONS:
        raise MoveError("move.not_found")

    current = player["location"]
    if target not in LOCATIONS[current]["exits"]:
        raise MoveError("move.no_exit", target=target)

    update_location(user_id, target)
    return target