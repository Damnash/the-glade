# services/eat.py

from core.time_utils import now
from db.players import get_player, update_player_fields
from core.player_state import update_player_state
from db.inventory import has_item, remove_item

class EatError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs

def eat(user_id: int) -> dict:
    player = update_player_state(get_player(user_id))
    if not player:
        raise EatError("start.need_start")

    # Проверяем наличие пайка (ration) в инвентаре
    if not has_item(user_id, "ration"):
        raise EatError("eat.no_food")

    # Съедаем 1 паёк
    if not remove_item(user_id, "ration", 1):
        raise EatError("eat.no_food")

    # Начисляем эффект: +5 HP, и +1 к счетчику food (для Лабиринта)
    new_hp = min(100, player["hp"] + 5)
    new_food = player.get("food", 0) + 1
    max_food = player.get("max_food", 10)
    if new_food > max_food:
        new_food = max_food

    update_player_fields(user_id, {
        "hp": new_hp,
        "food": new_food,
        "last_fed_at": now(),
    })

    return {"hp": new_hp, "food": new_food}
