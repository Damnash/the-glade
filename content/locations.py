# content/locations.py

LOCATIONS = {
    # Центр — хаб
    "center": {
        "exits": [
            "farms", "forge", "medbay", "huts",
            "north_gates", "south_gates", "west_gates", "east_gates",
            "kitchen", "dining", "council", "watchtower",
            "storage", "well", "workshop", "graveyard",
            "garden", "training", "abandoned_hut",
        ],
    },

    # Ворота (4)
    "north_gates": {"exits": ["center", "watchtower"]},
    "south_gates": {"exits": ["center", "graveyard"]},
    "west_gates": {"exits": ["center", "training"]},
    "east_gates": {"exits": ["center", "storage"]},

    # Еда и вода
    "farms":     {"exits": ["center", "garden", "well"]},
    "garden":    {"exits": ["farms", "well"]},
    "well":      {"exits": ["farms", "garden", "medbay"]},
    "kitchen":   {"exits": ["center", "dining", "storage"]},
    "dining":    {"exits": ["kitchen", "center"]},

    # Работа
    "forge":     {"exits": ["center", "medbay", "workshop"]},
    "workshop":  {"exits": ["forge", "medbay"]},
    "medbay":    {"exits": ["center", "forge", "well", "workshop", "huts"]},

    # Социальные
    "huts":      {"exits": ["center", "medbay", "graveyard", "south_gates"]},
    "graveyard": {"exits": ["huts", "south_gates"]},
    "council":   {"exits": ["center", "watchtower"]},
    "watchtower":{"exits": ["center", "north_gates", "council"]},
    "training":  {"exits": ["west_gates", "center"]},

    # Ресурсы
    "storage":   {"exits": ["center", "kitchen", "east_gates"]},
    "abandoned_hut": {"exits": ["center", "huts"]},
}

START_LOCATION = "center"
