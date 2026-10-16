# content/monsters.py

MONSTERS = {
    "young": {
        "name_key": "griever.young.name",
        "desc_key": "griever.young.desc",
        "hp": 30,
        "damage": 12,
        "attack_speed": 0.7,
        "rewards": {
            "tokens": 5,
            "meat": 2,
        },
        "fragment_chance": 0.02,
    },
    "adult": {
        "name_key": "griever.adult.name",
        "desc_key": "griever.adult.desc",
        "hp": 60,
        "damage": 20,
        "attack_speed": 0.85,
        "rewards": {
            "tokens": 10,
            "meat": 4,
            "metal": 1,
        },
        "fragment_chance": 0.05,
    },
    "ancient": {
        "name_key": "griever.ancient.name",
        "desc_key": "griever.ancient.desc",
        "hp": 100,
        "damage": 32,
        "attack_speed": 1.0,
        "rewards": {
            "tokens": 20,
            "meat": 6,
            "metal": 3,
        },
        "fragment_chance": 0.12,
    },
}


# Какие Гриверы встречаются в каком кольце
RING_MONSTERS = {
    1: ["young"],
    2: ["young", "young", "adult"],       # weighted
    3: ["adult", "adult", "ancient"],
    4: ["ancient", "ancient"],
    0: ["ancient", "ancient"],             # центр
}


# Шансы встречи
ENCOUNTER_CHANCE_DAY = 0.05
ENCOUNTER_CHANCE_NIGHT = 0.20
ENCOUNTER_CHANCE_CENTER = 0.30


def get_ring_monster(ring: int) -> str:
    """Случайный тип Гривера для кольца."""
    import random
    pool = RING_MONSTERS.get(ring, RING_MONSTERS[1])
    return random.choice(pool)


def get_monster(monster_type: str) -> dict:
    return MONSTERS.get(monster_type, MONSTERS["young"])
