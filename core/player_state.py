# core/player_state.py
#
# Управление состоянием игрока.
#
# ВАЖНО: Голод, жажда и sanity НЕ тикают по реальному времени в Глэйде.
# Они тратятся ТОЛЬКО в Лабиринте, за переход (см. services/survival.py).
#
# Эта функция оставлена ТОЛЬКО для:
#   1. Сон — регенерация HP/energy/sanity по минутам
#   2. Работа — переход working → active при завершении

from core.time_utils import now, parse_dt, seconds_since
from db.players import update_player_fields


# ============ Константы ============

SANITY_MAX = 100

# Сон
SLEEP_REGEN_PER_MIN = 5
HP_REGEN_PER_MIN_SLEEP = 2
SANITY_REGEN_PER_MIN_SLEEP = 1


# ============ Утилиты ============

def is_in_maze(player: dict) -> bool:
    """Игрок в Лабиринте?"""
    return player.get("maze_layer", 0) > 0


def _get_max_hp(player: dict) -> int:
    """Максимум HP с учётом профессии/перка."""
    from services.bonuses import get_player_bonus
    return get_player_bonus(player)["max_hp"]


def _get_max_energy(player: dict) -> int:
    """Максимум энергии с учётом профессии/перка."""
    from services.bonuses import get_player_bonus
    return get_player_bonus(player)["max_energy"]


# ============ Основная функция ============

def update_player_state(player: dict) -> dict:
    """
    Приводит игрока к актуальному состоянию.
    
    Что делает:
      - Сон: регенерирует HP/energy/sanity по минутам с last_seen
      - Работа: переводит working → active при завершении
    
    Что НЕ делает:
      - НЕ трогает food/water/sanity вне сна
      - НЕ тикает голод/жажду по реальному времени
      - НЕ регенерирует воду в Глэйде
    """
    if not player:
        return player

    changed = {}

    # ============ 1. Сон ============
    if player["status"] == "sleeping":
        elapsed_sleep = seconds_since(player.get("last_seen"))
        minutes = elapsed_sleep // 60

        if minutes > 0:
            max_hp = _get_max_hp(player)
            max_energy = _get_max_energy(player)

            new_energy = min(
                max_energy,
                player["energy"] + minutes * SLEEP_REGEN_PER_MIN,
            )
            new_hp = min(
                max_hp,
                player["hp"] + minutes * HP_REGEN_PER_MIN_SLEEP,
            )
            new_sanity = min(
                SANITY_MAX,
                player.get("sanity", 100) + minutes * SANITY_REGEN_PER_MIN_SLEEP,
            )

            if new_energy != player["energy"]:
                changed["energy"] = new_energy
            if new_hp != player["hp"]:
                changed["hp"] = new_hp
            if new_sanity != player.get("sanity", 100):
                changed["sanity"] = new_sanity

            # Просыпается при полном восстановлении
            if new_energy >= max_energy and new_hp >= max_hp:
                changed["status"] = "active"
                changed["last_action"] = now()

    # ============ 2. Работа ============
    if player["status"] == "working":
        ends_at = parse_dt(player.get("work_ends_at"))
        if ends_at and now() >= ends_at:
            changed["status"] = "active"

    # ============ Запись ============
    if changed:
        update_player_fields(player["user_id"], changed)
        player.update(changed)

    return player
