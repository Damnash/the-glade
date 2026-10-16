# content/maze.py

# Карта Лабиринта (заглушка для v0.2)
# В v0.3 будет полноценная генерация

# Стартовые секции 4 крыльев
MAZE_ENTRANCES = {
    "north_gates": "N1",
    "south_gates": "S1",
    "west_gates": "W1",
    "east_gates": "E1",
}

# Обратное соответствие: секция → выход
MAZE_EXITS = {
    "N1": "north_gates",
    "S1": "south_gates",
    "W1": "west_gates",
    "E1": "east_gates",
}

# Пока все секции — просто входы/выходы
MAZE_SECTIONS = {
    "N1": {
        "wing": "north",
        "ring": 1,
        "exits": [],  # пока нет внутренних связей
        "exits_to_glade": "north_gates",
    },
    "S1": {
        "wing": "south",
        "ring": 1,
        "exits": [],
        "exits_to_glade": "south_gates",
    },
    "W1": {
        "wing": "west",
        "ring": 1,
        "exits": [],
        "exits_to_glade": "west_gates",
    },
    "E1": {
        "wing": "east",
        "ring": 1,
        "exits": [],
        "exits_to_glade": "east_gates",
    },
}