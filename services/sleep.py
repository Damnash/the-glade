# services/sleep.py

from core.player_state import update_player_state
from core.time_utils import now
from db.players import get_player, update_player_fields


class SleepError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


def _get_max_hp(player: dict) -> int:
    """Максимум HP с учётом профессии/перка."""
    from services.bonuses import get_player_bonus
    return get_player_bonus(player)["max_hp"]


def _get_max_energy(player: dict) -> int:
    """Максимум энергии с учётом профессии/перка."""
    from services.bonuses import get_player_bonus
    return get_player_bonus(player)["max_energy"]


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

    # Проверка «не устал» — с учётом персональных максимумов
    max_hp = _get_max_hp(player)
    max_energy = _get_max_energy(player)

    if player["energy"] >= max_energy and player["hp"] >= max_hp:
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
