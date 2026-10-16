# services/survival.py
#
# Расход ресурсов в Лабиринте.
#
# ВАЖНО: В Глэйде food/water/sanity НЕ тратятся (см. core/player_state.py).
# Здесь — только расход ЗА ПЕРЕХОД в Лабиринте.

from core.time_utils import now
from db.players import get_player, update_player_fields


# ============ Настройки баланса ============

# За один переход из секции в секцию
FOOD_PER_MOVE = 1
WATER_PER_MOVE = 1
ENERGY_PER_MOVE = 2
SANITY_PER_MOVE_DAY = 1
SANITY_PER_MOVE_NIGHT = 2

# Урон при нуле еды/воды (за переход)
STARVE_DAMAGE = 2
THIRST_DAMAGE = 2


class SurvivalError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


def consume_on_move(user_id: int, is_night: bool = False) -> dict:
    """
    Списать ресурсы за один переход в Лабиринте.
    
    Возвращает отчёт:
        {
            "food_lost": 1,
            "water_lost": 1,
            "energy_lost": 2,
            "sanity_lost": 1,
            "hp_lost": 0,
            "starving": False,   # True если еда была 0 и был урон
            "thirsty": False,    # True если вода была 0 и был урон
            "death": False,      # True если hp <= 0
        }
    
    Если death=True — вызывающий код должен вызвать die_in_maze.
    """
    player = get_player(user_id)
    if not player:
        raise SurvivalError("start.need_start")

    if player.get("maze_layer", 0) == 0:
        raise SurvivalError("maze.not_in_maze")

    # ============ Текущие значения ============
    food = player.get("food", 0)
    water = player.get("water", 0)
    energy = player.get("energy", 0)
    sanity = player.get("sanity", 100)
    hp = player.get("hp", 0)

    # ============ Еда ============
    food_lost = min(food, FOOD_PER_MOVE)
    new_food = food - FOOD_PER_MOVE
    starving = False
    if new_food < 0:
        new_food = 0
        starving = True

    # ============ Вода ============
    water_lost = min(water, WATER_PER_MOVE)
    new_water = water - WATER_PER_MOVE
    thirsty = False
    if new_water < 0:
        new_water = 0
        thirsty = True

    # ============ Энергия ============
    energy_lost = min(energy, ENERGY_PER_MOVE)
    new_energy = max(0, energy - ENERGY_PER_MOVE)

    # ============ Sanity ============
    sanity_per_move = SANITY_PER_MOVE_NIGHT if is_night else SANITY_PER_MOVE_DAY
    sanity_lost = min(sanity, sanity_per_move)
    new_sanity = max(0, sanity - sanity_per_move)

    # ============ HP урон от голода/жажды ============
    hp_lost = 0
    if starving:
        hp_lost += STARVE_DAMAGE
    if thirsty:
        hp_lost += THIRST_DAMAGE

    new_hp = max(0, hp - hp_lost)

    # ============ Запись в БД ============
    update_player_fields(user_id, {
        "food": new_food,
        "water": new_water,
        "energy": new_energy,
        "sanity": new_sanity,
        "hp": new_hp,
    })

    return {
        "food_lost": food_lost,
        "water_lost": water_lost,
        "energy_lost": energy_lost,
        "sanity_lost": sanity_lost,
        "hp_lost": hp_lost,
        "starving": starving,
        "thirsty": thirsty,
        "death": new_hp <= 0,
        # Текущие значения после списания
        "food": new_food,
        "water": new_water,
        "energy": new_energy,
        "sanity": new_sanity,
        "hp": new_hp,
    }


def format_status_line(player: dict) -> str:
    """Строка статуса игрока в Лабиринте (для отображения)."""
    from services.bonuses import get_player_bonus
    bonus = get_player_bonus(player)

    hp = player.get("hp", 0)
    energy = player.get("energy", 0)
    sanity = player.get("sanity", 100)
    food = player.get("food", 0)
    water = player.get("water", 0)
    tokens = player.get("tokens", 0)

    max_hp = bonus["max_hp"]
    max_energy = bonus["max_energy"]
    max_food = player.get("max_food", 10)
    max_water = player.get("max_water", 5)

    return (
        f"❤️ {hp}/{max_hp}  ⚡ {energy}/{max_energy}  🧠 {sanity}/100\n"
        f"🍞 {food}/{max_food}  💧 {water}/{max_water}  🪙 {tokens}"
    )
