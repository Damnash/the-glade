# content/professions.py

PROFESSIONS = {
    "fighter": {
        "name_key": "prof.fighter.name",
        "desc_key": "prof.fighter.desc",
        "icon": "⚔️",
        "bonus": {"max_hp": 10, "damage": 2},
    },
    "engineer": {
        "name_key": "prof.engineer.name",
        "desc_key": "prof.engineer.desc",
        "icon": "⚙️",
        "bonus": {"craft": 2, "has_compass": True},
    },
    "medic": {
        "name_key": "prof.medic.name",
        "desc_key": "prof.medic.desc",
        "icon": "💊",
        "bonus": {"max_hp": 10, "heal_bonus": 1},
    },
    "scout": {
        "name_key": "prof.scout.name",
        "desc_key": "prof.scout.desc",
        "icon": "🏃",
        "bonus": {"max_energy": 10, "flee_bonus": 0.05},
    },
}

PERKS = {
    "revenge": {
        "name_key": "perk.revenge.name",
        "desc_key": "perk.revenge.desc",
        "icon": "🗡️",
        "bonus": {"damage": 0.10},  # +10% урона (было 5%)
    },
    "freedom": {
        "name_key": "perk.freedom.name",
        "desc_key": "perk.freedom.desc",
        "icon": "🕊️",
        "bonus": {"max_energy": 5},
    },
    "truth": {
        "name_key": "perk.truth.name",
        "desc_key": "perk.truth.desc",
        "icon": "📖",
        "bonus": {"fragment_chance": 0.05},
    },
    "home": {
        "name_key": "perk.home.name",
        "desc_key": "perk.home.desc",
        "icon": "🏠",
        "bonus": {"max_hp": 5},
    },
}
