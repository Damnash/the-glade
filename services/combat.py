# services/combat.py

import random

from content.monsters import (
    get_monster, get_ring_monster,
    ENCOUNTER_CHANCE_DAY, ENCOUNTER_CHANCE_NIGHT, ENCOUNTER_CHANCE_CENTER,
)
from core.time_utils import now
from services.event_log import add_event, cleanup_old_events
from db.connection import get_conn
from db.players import get_player, update_player_fields


class CombatError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


# ============ Встреча ============

def is_night() -> bool:
    hour = now().hour
    return hour >= 22 or hour < 6


def roll_encounter(ring: int, is_center: bool = False, user_id: int = 0) -> str | None:
    """
    Проверить, встретится ли Гривер.
    Возвращает monster_type или None.
    Погода умножает шанс (туман/гроза — чаще).
    """
    if is_center or ring == 0:
        chance = ENCOUNTER_CHANCE_CENTER
    elif is_night():
        chance = ENCOUNTER_CHANCE_NIGHT
    else:
        chance = ENCOUNTER_CHANCE_DAY

    # Погода
    try:
        from services.weather import get_weather_modifiers
        mult, _ = get_weather_modifiers()
        chance = min(1.0, chance * mult)
    except Exception:
        pass

    # Баффы (проклятие/благословение)
    try:
        from services.buffs import get_buff_modifiers
        b = get_buff_modifiers(user_id)
        chance = min(1.0, chance * b["monster_mult"])
    except Exception:
        pass

    if random.random() > chance:
        return None

    return get_ring_monster(ring)


# ============ Управление боем ============

def get_active_combat(user_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM active_combats WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def start_combat(user_id: int, monster_type: str, section_id: str, layer: int) -> dict:
    """Начать бой."""
    monster = get_monster(monster_type)
    hp = monster["hp"]

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO active_combats
        (user_id, monster_type, monster_hp, monster_max_hp, section_id, layer, started_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, monster_type, hp, hp, section_id, layer, now()))
    conn.commit()
    conn.close()

    return {
        "monster_type": monster_type,
        "monster_hp": hp,
        "monster_max_hp": hp,
        "monster": monster,
    }


def end_combat(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM active_combats WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ============ Действия ============

def player_attack(user_id: int) -> dict:
    """Игрок атакует Гривера."""
    combat = get_active_combat(user_id)
    if not combat:
        raise CombatError("combat.no_combat")

    player = get_player(user_id)
    monster = get_monster(combat["monster_type"])

    # Урон игрока — базовый 8 + бонусы профессии/перка
    base_damage = 8
    if player["hp"] > 70:
        base_damage += 3
    if player["hp"] > 90:
        base_damage += 2

    # Бонусы профессии и перка
    from services.bonuses import get_player_bonus
    bonus = get_player_bonus(player)
    base_damage += bonus["damage"]

    # Sanity влияет на урон
    sanity = player.get("sanity", 100)
    if sanity < 25:
        base_damage = int(base_damage * 0.75)
    elif sanity < 50:
        base_damage = int(base_damage * 0.90)

    # Разброс ±30%
    damage = int(base_damage * random.uniform(0.7, 1.3))
    damage = max(1, damage)

    new_monster_hp = max(0, combat["monster_hp"] - damage)

    # Обновляем монстра
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE active_combats SET monster_hp = ? WHERE user_id = ?",
                (new_monster_hp, user_id))
    conn.commit()
    conn.close()

    result = {
        "player_damage": damage,
        "monster_hp": new_monster_hp,
        "monster_max_hp": combat["monster_max_hp"],
    }

    # Гривер побеждён
    if new_monster_hp <= 0:
        end_combat(user_id)
        result["victory"] = True
        result["monster_type"] = combat["monster_type"]  # для give_victory_rewards
        result["rewards"] = monster["rewards"]
        result["fragment_chance"] = monster["fragment_chance"]
    else:
        # Гривер атакует в ответ
        counter = _monster_attack(user_id, monster)
        result["counter"] = counter
        result["player_hp"] = counter["player_hp"]
        if counter.get("player_dead"):
            result["player_dead"] = True

    return result


def player_defend(user_id: int) -> dict:
    """Игрок защищается — меньше урона."""
    combat = get_active_combat(user_id)
    if not combat:
        raise CombatError("combat.no_combat")

    player = get_player(user_id)
    monster = get_monster(combat["monster_type"])

    # Урон Гривера снижен на 50%
    damage = int(monster["damage"] * 0.5 * random.uniform(0.7, 1.0))
    damage = max(1, damage)

    new_hp = max(0, player["hp"] - damage)
    update_player_fields(user_id, {"hp": new_hp})

    return {
        "monster_damage": damage,
        "player_hp": new_hp,
        "player_dead": new_hp <= 0,
    }


def player_flee(user_id: int) -> dict:
    """Попытка бегства."""
    combat = get_active_combat(user_id)
    if not combat:
        raise CombatError("combat.no_combat")

    player = get_player(user_id)

    # Шанс бегства: 50% базово, +10% если energy > 50, +10% если HP > 70
    chance = 0.5
    if player["energy"] > 50:
        chance += 0.1
    if player["hp"] > 70:
        chance += 0.1

    # Бонус профессии
    from services.bonuses import get_player_bonus
    bonus = get_player_bonus(player)
    chance += bonus["flee_bonus"]

    # Sanity влияет
    sanity = player.get("sanity", 100)
    if sanity < 25:
        chance -= 0.2

    chance = max(0.1, min(0.9, chance))

    # Расход энергии
    new_energy = max(0, player["energy"] - 10)
    update_player_fields(user_id, {"energy": new_energy})

    if random.random() <= chance:
        # Успех
        end_combat(user_id)
        return {
            "success": True,
            "energy_lost": 10,
            "new_energy": new_energy,
        }
    else:
        # Провал — Гривер атакует
        monster = get_monster(combat["monster_type"])
        counter = _monster_attack(user_id, monster)
        return {
            "success": False,
            "energy_lost": 10,
            "new_energy": new_energy,
            "counter": counter,
            "player_hp": counter["player_hp"],
            "player_dead": counter.get("player_dead", False),
        }


def _monster_attack(user_id: int, monster: dict) -> dict:
    """Атака Гривера по игроку. Ночью — +50%."""
    from core.daycycle import is_night
    player = get_player(user_id)

    damage = int(monster["damage"] * random.uniform(0.7, 1.3))
    if is_night():
        damage = int(damage * 1.5)
    damage = max(1, damage)

    new_hp = max(0, player["hp"] - damage)
    update_player_fields(user_id, {"hp": new_hp})

    # Sanity падает при атаке
    sanity = player.get("sanity", 100)
    new_sanity = max(0, sanity - 3)
    update_player_fields(user_id, {"sanity": new_sanity})

    return {
        "damage": damage,
        "player_hp": new_hp,
        "player_dead": new_hp <= 0,
    }


# ============ Награды ============

def give_victory_rewards(user_id: int, monster_type: str) -> dict:
    """Выдать награды за победу."""
    from services.achievements import award_points, check_hunter
    award_points(user_id, "kill_griever", field="griever_kills")
    check_hunter(user_id)

    # Daily quest progress
    try:
        from services.daily_quests import add_progress
        add_progress(user_id, "kill_griever", 1)
    except Exception:
        pass

    # Story tracking
    try:
        from services.story import track_event
        track_event(user_id, "kill_grievers")
    except Exception:
        pass
    monster = get_monster(monster_type)
    rewards = monster["rewards"].copy()

    # Лог для главного меню (с типом Гривера и наградой) — ПОСЛЕ rewards
    try:
        from core.i18n import t
        from db.players import get_player
        _p = get_player(user_id)
        if _p:
            lang = _p["language"]
            icons = {"tokens": "🪙", "meat": "🥩", "metal": "⚙️", "fragment": "🗺️"}
            rewards_str = ", ".join(f"{icons.get(k, k)} +{v}" for k, v in rewards.items())
            add_event(
                user_id, "kill_griever",
                t("log.kill_griever", lang, monster=t(monster["name_key"], lang), rewards=rewards_str),
                severity="important",
            )
            cleanup_old_events(user_id)

            # Автодневник
            try:
                from services.diary import add_diary_auto
                add_diary_auto(user_id, "kill_griever",
                               monster=t(monster["name_key"], lang),
                               rewards=rewards_str)
            except Exception:
                pass
    except Exception:
        pass

    # Возможен фрагмент карты
    if random.random() < monster["fragment_chance"]:
        rewards["fragment"] = 1

    from db.inventory import add_item
    from db.players import get_player
    from db.connection import get_conn

    player = get_player(user_id)
    updates = {}

    for key, value in rewards.items():
        if key == "tokens":
            updates["tokens"] = player.get("tokens", 0) + value
        elif key == "fragment":
            # Фрагмент — предмет
            add_item(user_id, "map_fragment", value)
        elif key in ("meat", "metal"):
            add_item(user_id, key, value)
        else:
            # На случай других
            add_item(user_id, key, value)

    if updates:
        update_player_fields(user_id, updates)

    return rewards
