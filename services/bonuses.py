# services/bonuses.py

from content.professions import PROFESSIONS, PERKS


def get_player_bonus(player: dict) -> dict:
    """
    Возвращает итоговые бонусы игрока от профессии и перка.
    """
    bonus = {
        "max_hp": 100,
        "max_energy": 100,
        "damage": 0,
        "fragment_chance": 0.0,
        "flee_bonus": 0.0,
        "craft_bonus": 0,
        "has_compass": False,
        "heal_bonus": 0,
    }

    # Профессия
    prof_key = player.get("profession")
    if prof_key and prof_key in PROFESSIONS:
        prof = PROFESSIONS[prof_key]
        for k, v in prof["bonus"].items():
            if k in ("max_hp", "max_energy", "damage", "craft_bonus", "heal_bonus"):
                bonus[k] += v
            elif k in ("fragment_chance", "flee_bonus"):
                bonus[k] += v
            elif k == "has_compass":
                bonus["has_compass"] = True

    # Перк
    perk_key = player.get("perk")
    if perk_key and perk_key in PERKS:
        perk = PERKS[perk_key]
        for k, v in perk["bonus"].items():
            if k in ("max_hp", "max_energy", "damage", "fragment_chance"):
                bonus[k] += v
            elif k in ("flee_bonus", "craft_bonus"):
                bonus[k] += v

    return bonus


def get_max_hp(player: dict) -> int:
    return get_player_bonus(player)["max_hp"]


def get_max_energy(player: dict) -> int:
    return get_player_bonus(player)["max_energy"]
