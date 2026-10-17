# content/clan_upgrades.py
#
# Апгрейды Глэййда: клан улучшает локации за общие ресурсы.
# Уровень 0 = не улучшено. Уровни 1-3.

CLAN_UPGRADES = {
    "forge": {
        "name_key": "upgrade.forge.name",
        "desc_key": "upgrade.forge.desc",
        "icon": "⚒️",
        "max_level": 3,
        "costs": {
            1: {"tokens": 50, "metal": 10, "meat": 5, "torch": 3},
            2: {"tokens": 100, "metal": 20, "meat": 10, "torch": 6},
            3: {"tokens": 200, "metal": 40, "meat": 20, "torch": 12},
        },
        "bonus": {
            1: {"craft_discount": 0.10},
            2: {"craft_discount": 0.20},
            3: {"craft_discount": 0.30},
        },
    },
    "farm": {
        "name_key": "upgrade.farm.name",
        "desc_key": "upgrade.farm.desc",
        "icon": "🌾",
        "max_level": 3,
        "costs": {
            1: {"tokens": 40, "metal": 5, "meat": 8},
            2: {"tokens": 80, "metal": 10, "meat": 16},
            3: {"tokens": 160, "metal": 20, "meat": 32},
        },
        "bonus": {
            1: {"food_bonus": 0.10},
            2: {"food_bonus": 0.20},
            3: {"food_bonus": 0.30},
        },
    },
    "medbay": {
        "name_key": "upgrade.medbay.name",
        "desc_key": "upgrade.medbay.desc",
        "icon": "💊",
        "max_level": 3,
        "costs": {
            1: {"tokens": 30, "metal": 5, "water": 3},
            2: {"tokens": 60, "metal": 10, "water": 6},
            3: {"tokens": 120, "metal": 20, "water": 12},
        },
        "bonus": {
            1: {"heal_bonus": 5},
            2: {"heal_bonus": 10},
            3: {"heal_bonus": 15},
        },
    },
}


def get_upgrade(key: str) -> dict | None:
    return CLAN_UPGRADES.get(key)


def get_next_level(key: str, current_level: int) -> int | None:
    """Следующий уровень (или None, если максимум)."""
    up = get_upgrade(key)
    if not up:
        return None
    if current_level >= up["max_level"]:
        return None
    return current_level + 1
