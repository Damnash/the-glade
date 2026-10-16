# content/items.py

ITEMS = {
    "knife": {
        "weight": 1,
        "stackable": False,
        "use": None,              # оружие, не используется напрямую
    },
    "ration": {
        "weight": 1,
        "stackable": True,
        "use": "eat",
    },
    "water_flask": {
        "weight": 1,
        "stackable": True,
        "use": "drink",
    },
    "torch": {
        "weight": 1,
        "stackable": True,
        "use": "light",
    },
    "rope": {
        "weight": 2,
        "stackable": True,
        "use": None,              # для Лабиринта
    },
    "map_fragment": {
        "weight": 0,
        "stackable": True,
        "use": None,
    },
    "bandage": {
        "weight": 1,
        "stackable": True,
        "use": "heal",
    },
}