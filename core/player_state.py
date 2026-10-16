# core/player_state.py

from core.time_utils import now, parse_dt, seconds_since
from db.players import update_player_fields


# Константы
ENERGY_MAX = 100
HP_MAX = 100
SANITY_MAX = 100

SLEEP_REGEN_PER_MIN = 5
HP_REGEN_PER_MIN_SLEEP = 2
SANITY_REGEN_PER_MIN_SLEEP = 1

HUNGER_INTERVAL_SEC = 3600
STARVE_DAMAGE_PER_HOUR = 2

# Sanity
SANITY_REGEN_GLADE_PER_HOUR = 5
SANITY_DRAIN_MAZE_PER_30MIN = 1
SANITY_DRAIN_NIGHT_PER_HOUR = 2

# Water
WATER_REGEN_GLADE_PER_HOUR = 1
WATER_DRAIN_MAZE_PER_HOUR = 1


def is_in_maze(player: dict) -> bool:
    """Игрок в Лабиринте?"""
    return player.get("maze_layer", 0) > 0


def is_night() -> bool:
    """Сейчас ночь по UTC?"""
    hour = now().hour
    return hour >= 22 or hour < 6


def update_player_state(player: dict) -> dict:
    """Приводит игрока к актуальному состоянию по реальному времени."""
    if not player:
        return player

    changed = {}

    # ============ 1. Голод ============
    last_fed = parse_dt(player.get("last_fed_at")) or now()
    elapsed = int((now() - last_fed).total_seconds())

    if elapsed >= HUNGER_INTERVAL_SEC:
        hours = elapsed // HUNGER_INTERVAL_SEC
        food_left = player["food"] - hours

        if food_left >= 0:
            changed["food"] = food_left
        else:
            hours_starving = -food_left
            dmg = hours_starving * STARVE_DAMAGE_PER_HOUR
            new_hp = max(0, player["hp"] - dmg)
            changed["food"] = 0
            changed["hp"] = new_hp

        changed["last_fed_at"] = now()

    # ============ 2. Жажда ============
    last_drank = parse_dt(player.get("last_drank_at")) or now()
    elapsed_water = int((now() - last_drank).total_seconds())

    if elapsed_water >= HUNGER_INTERVAL_SEC:
        hours = elapsed_water // HUNGER_INTERVAL_SEC

        if is_in_maze(player):
            # В Лабиринте — вода тратится
            water_drain = hours * WATER_DRAIN_MAZE_PER_HOUR
        else:
            # В Глэйде — вода восстанавливается
            water_drain = -hours * WATER_REGEN_GLADE_PER_HOUR

        new_water = player["water"] - water_drain
        max_w = player.get("max_water", 5)

        if new_water < 0:
            # Жажда — урон
            hours_thirsty = -new_water
            dmg = hours_thirsty * STARVE_DAMAGE_PER_HOUR
            current_hp = changed.get("hp", player["hp"])
            changed["hp"] = max(0, current_hp - dmg)
            changed["water"] = 0
        elif new_water > max_w:
            changed["water"] = max_w
        else:
            changed["water"] = new_water

        changed["last_drank_at"] = now()

    # ============ 3. Sanity ============
    last_sanity = parse_dt(player.get("last_sanity_at")) or now()
    elapsed_sanity = int((now() - last_sanity).total_seconds())

    if elapsed_sanity >= 1800:  # 30 минут
        half_hours = elapsed_sanity // 1800
        sanity_change = 0

        if is_in_maze(player):
            # В Лабиринте — рассудок падает
            sanity_change = -half_hours * SANITY_DRAIN_MAZE_PER_30MIN
            if is_night():
                sanity_change -= (elapsed_sanity // 3600) * SANITY_DRAIN_NIGHT_PER_HOUR
        else:
            # В Глэйде — рассудок восстанавливается
            sanity_change = (elapsed_sanity // 3600) * SANITY_REGEN_GLADE_PER_HOUR

        current_sanity = player.get("sanity", 100)
        new_sanity = current_sanity + sanity_change

        if new_sanity < 0:
            new_sanity = 0
        elif new_sanity > SANITY_MAX:
            new_sanity = SANITY_MAX

        if new_sanity != current_sanity:
            changed["sanity"] = new_sanity

        changed["last_sanity_at"] = now()

    # ============ 4. Сон ============
    if player["status"] == "sleeping":
        elapsed_sleep = seconds_since(player.get("last_seen"))
        minutes = elapsed_sleep // 60

        if minutes > 0:
            new_energy = min(ENERGY_MAX, player["energy"] + minutes * SLEEP_REGEN_PER_MIN)
            new_hp = min(HP_MAX, changed.get("hp", player["hp"]) + minutes * HP_REGEN_PER_MIN_SLEEP)
            new_sanity = min(SANITY_MAX, changed.get("sanity", player.get("sanity", 100)) + minutes * SANITY_REGEN_PER_MIN_SLEEP)

            if new_energy != player["energy"]:
                changed["energy"] = new_energy
            if new_hp != player["hp"]:
                changed["hp"] = new_hp
            if new_sanity != player.get("sanity", 100):
                changed["sanity"] = new_sanity

            # Просыпается при полном восстановлении
            if new_energy >= ENERGY_MAX and new_hp >= HP_MAX:
                changed["status"] = "active"
                changed["last_action"] = now()

    # ============ 5. Работа ============
    if player["status"] == "working":
        ends_at = parse_dt(player.get("work_ends_at"))
        if ends_at and now() >= ends_at:
            changed["status"] = "active"

    if changed:
        update_player_fields(player["user_id"], changed)
        player.update(changed)

    return player
