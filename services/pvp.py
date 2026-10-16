# services/pvp.py

import random

from core.i18n import t
from core.maze_current import get_current_season
from core.time_utils import now
from db.connection import get_conn
from db.players import get_player, find_by_name, players_in_location, update_player_fields, die_and_respawn
from db.pvp import (
    has_shield, get_steal_cooldown, set_steal_cooldown,
    create_duel, get_duel, set_duel_status,
    log_pvp,
)


class PvPError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


# ============ Проверка зон ============

def is_pvp_zone(player: dict) -> bool:
    """Можно ли здесь PvP."""
    # Глэйд — никогда
    if player.get("maze_layer", 0) == 0:
        return False

    # В Лабиринте — проверяем секцию
    season = get_current_season()
    section_id = player.get("maze_section")
    layer = player.get("maze_layer", 1)

    from db.maze_map import get_section
    section = get_section(season, layer, section_id)
    if not section:
        return False

    # Центр — всегда PvP
    if section["type"] == "center":
        return True

    # Финал сезона (день 70+)
    from core.maze_current import get_season_day
    day = get_season_day(season)
    if day >= 70:
        return True

    # Носитель ключа 5 — всегда PvP
    from db.keys import has_player_key
    if has_player_key(season, player["user_id"], 5):
        return True

    return False


def check_pvp_possible(attacker_id: int, victim_id: int) -> None:
    """Проверить можно ли PvP."""
    if attacker_id == victim_id:
        raise PvPError("pvp.err.self")

    attacker = get_player(attacker_id)
    victim = get_player(victim_id)

    if not attacker or not victim:
        raise PvPError("pvp.err.player_not_found")

    # Не в PvP-зоне
    if not is_pvp_zone(attacker) or not is_pvp_zone(victim):
        raise PvPError("pvp.err.not_pvp_zone")

    # Не в одной локации
    if attacker["location"] != victim["location"] or \
       attacker.get("maze_section") != victim.get("maze_section"):
        raise PvPError("pvp.err.not_nearby")

    # Щит новичка
    if has_shield(victim_id):
        raise PvPError("pvp.err.victim_shielded")

    # Свой клан
    from db.clans import get_player_clan
    a_clan = get_player_clan(attacker_id)
    v_clan = get_player_clan(victim_id)
    if a_clan and v_clan and a_clan["clan_id"] == v_clan["clan_id"]:
        raise PvPError("pvp.err.same_clan")


# ============ Кража ============

def attempt_steal(attacker_id: int, victim_nick: str) -> dict:
    """Попытка кражи."""
    victim = find_by_name(victim_nick)
    if not victim:
        raise PvPError("pvp.err.player_not_found")

    check_pvp_possible(attacker_id, victim["user_id"])

    # Кулдаун
    cd = get_steal_cooldown(attacker_id)
    if cd > 0:
        raise PvPError("pvp.err.steal_cd", time=cd)

    attacker = get_player(attacker_id)

    # Шанс: 30% + бонус за энергию
    chance = 0.30
    if attacker["energy"] > 70:
        chance += 0.20
    elif attacker["energy"] > 40:
        chance += 0.10

    # Sanity влияет
    sanity = attacker.get("sanity", 100)
    if sanity < 25:
        chance -= 0.20

    chance = max(0.1, min(0.9, chance))

    # Расход энергии
    update_player_fields(attacker_id, {
        "energy": max(0, attacker["energy"] - 10),
    })
    set_steal_cooldown(attacker_id)

    success = random.random() < chance

    if not success:
        log_pvp(attacker_id, victim["user_id"], "steal_fail")
        return {"success": False, "chance": chance}

    # Успех — крадём случайный предмет
    from db.inventory import get_inventory, remove_item, add_item

    items = get_inventory(victim["user_id"])
    if not items:
        # Нечего красть
        log_pvp(attacker_id, victim["user_id"], "steal_empty")
        return {"success": True, "stolen": None, "empty": True}

    # Приоритет: жетоны → ключи → фрагменты → остальное
    victim_player = get_player(victim["user_id"])

    stolen_item = None
    stolen_qty = 0

    # Попытка украсть жетоны (если есть)
    if victim_player.get("tokens", 0) > 0:
        amount = min(victim_player["tokens"], random.randint(1, 5))
        update_player_fields(victim["user_id"], {
            "tokens": victim_player["tokens"] - amount,
        })
        update_player_fields(attacker_id, {
            "tokens": attacker["tokens"] + amount,
        })
        stolen_item = "tokens"
        stolen_qty = amount
    else:
        # Крадём предмет
        item = random.choice(items)
        item_key = item["item_key"]
        if remove_item(victim["user_id"], item_key, 1):
            add_item(attacker_id, item_key, 1)
            stolen_item = item_key
            stolen_qty = 1

    log_pvp(attacker_id, victim["user_id"], "steal_success",
            tokens_gained=stolen_qty if stolen_item == "tokens" else 0,
            items_gained=1 if stolen_item != "tokens" else 0)

    return {
        "success": True,
        "stolen": stolen_item,
        "qty": stolen_qty,
    }


# ============ Атака ============

def attack_player(attacker_id: int, victim_nick: str) -> dict:
    """Атака на игрока."""
    victim = find_by_name(victim_nick)
    if not victim:
        raise PvPError("pvp.err.player_not_found")

    check_pvp_possible(attacker_id, victim["user_id"])

    attacker = get_player(attacker_id)
    victim_player = get_player(victim["user_id"])

    # Урон атакующего
    base_damage = 8
    if attacker["hp"] > 70:
        base_damage += 3
    if attacker.get("sanity", 100) < 25:
        base_damage = int(base_damage * 0.75)

    # Бонус профессии и перка
    from services.bonuses import get_player_bonus
    bonus = get_player_bonus(attacker)
    base_damage += bonus["damage"]

    damage = max(1, int(base_damage * random.uniform(0.7, 1.3)))

    new_victim_hp = max(0, victim_player["hp"] - damage)

    update_player_fields(victim["user_id"], {"hp": new_victim_hp})

    return {
        "damage": damage,
        "victim_hp": new_victim_hp,
        "victim_dead": new_victim_hp <= 0,
        "victim_id": victim["user_id"],
        "victim_name": victim["display_name"] or victim["username"],
    }


def kill_player(killer_id: int, victim_id: int, section_id: str, layer: int) -> dict:
    """Убийство — забрать всё."""
    victim = get_player(victim_id)
    killer = get_player(killer_id)

    if not victim or not killer:
        raise PvPError("pvp.err.player_not_found")

    # Собираем всё с жертвы
    tokens = victim.get("tokens", 0)

    # Предметы
    from db.inventory import get_inventory, remove_item, add_item
    items = get_inventory(victim_id)
    items_moved = 0

    for item in items:
        if remove_item(victim_id, item["item_key"], item["quantity"]):
            add_item(killer_id, item["item_key"], item["quantity"])
            items_moved += 1

    # Жетоны
    if tokens > 0:
        update_player_fields(victim_id, {"tokens": 0})
        update_player_fields(killer_id, {"tokens": killer.get("tokens", 0) + tokens})

    # Карты
    from db.map_items import drop_all_non_personal_maps, get_maps_on_ground
    maps_dropped = drop_all_non_personal_maps(victim_id, section_id, layer)

    # Ключи
    from services.keys import drop_all_keys_on_death
    keys_dropped = drop_all_keys_on_death(victim_id, section_id, layer)

    # Очки
    from services.achievements import award_points
    award_points(killer_id, "kill_player", field="kills")

    # Лог
    log_pvp(killer_id, victim_id, "kill", section_id, layer,
            tokens_gained=tokens, items_gained=items_moved)

    # Респавн жертвы
    die_and_respawn(victim_id)

    return {
        "tokens": tokens,
        "items": items_moved,
        "maps_dropped": maps_dropped,
        "keys_dropped": keys_dropped,
    }


# ============ Дуэли ============

def challenge_duel(challenger_id: int, opponent_nick: str, stake: int) -> dict:
    """Вызвать на дуэль."""
    opponent = find_by_name(opponent_nick)
    if not opponent:
        raise PvPError("pvp.err.player_not_found")

    if opponent["user_id"] == challenger_id:
        raise PvPError("pvp.err.self")

    if stake < 0:
        raise PvPError("pvp.err.invalid_stake")

    challenger = get_player(challenger_id)
    if challenger.get("tokens", 0) < stake:
        raise PvPError("pvp.err.not_enough_tokens", need=stake)

    # Создать
    duel_id = create_duel(challenger_id, opponent["user_id"], stake)

    return {
        "duel_id": duel_id,
        "opponent_id": opponent["user_id"],
        "opponent_name": opponent["display_name"] or opponent["username"],
        "stake": stake,
        "challenger_name": challenger["display_name"] or challenger["username"],
    }


def resolve_duel(duel_id: int, winner_id: int) -> dict:
    """Разрешить дуэль."""
    duel = get_duel(duel_id)
    if not duel or duel["status"] != "pending":
        raise PvPError("pvp.err.duel_not_found")

    # Ставки
    stake = duel["stake_tokens"]
    loser_id = duel["opponent_id"] if winner_id == duel["challenger_id"] else duel["challenger_id"]

    winner = get_player(winner_id)
    loser = get_player(loser_id)

    if not winner or not loser:
        raise PvPError("pvp.err.player_not_found")

    # Проверка, что у обоих хватает
    if loser.get("tokens", 0) < stake:
        raise PvPError("pvp.err.loser_no_tokens", need=stake)

    # Перевод
    update_player_fields(loser_id, {"tokens": loser["tokens"] - stake})
    update_player_fields(winner_id, {"tokens": winner.get("tokens", 0) + stake})

    set_duel_status(duel_id, "resolved")

    log_pvp(winner_id, loser_id, "duel", tokens_gained=stake)

    return {
        "winner_name": winner["display_name"] or winner["username"],
        "loser_name": loser["display_name"] or loser["username"],
        "stake": stake,
    }
