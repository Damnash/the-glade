# content/work.py

WORK_TYPES = {
    "farm": {
        "locations": ["farms", "garden"],
        "duration_sec": 300,
        "energy_cost": 20,
        "rewards": {"food": 5},
        "needs_energy": 20,
    },
    "forge": {
        "locations": ["forge", "workshop"],
        "duration_sec": 600,
        "energy_cost": 30,
        "rewards": {"tokens": 3},
        "needs_energy": 30,
    },
    "medbay": {
        "locations": ["medbay"],
        "duration_sec": 600,
        "energy_cost": 25,
        "rewards": {"tokens": 3},
        "needs_energy": 25,
    },
    "guard": {
        "locations": ["north_gates", "south_gates", "west_gates", "east_gates"],
        "duration_sec": 900,
        "energy_cost": 30,
        "rewards": {"tokens": 4},
        "needs_energy": 30,
    },
    "kitchen": {
        "locations": ["kitchen"],
        "duration_sec": 300,
        "energy_cost": 15,
        "rewards": {"food": 3, "tokens": 1},
        "needs_energy": 15,
    },
    "watch": {
        "locations": ["watchtower"],
        "duration_sec": 600,
        "energy_cost": 20,
        "rewards": {"tokens": 3},
        "needs_energy": 20,
    },
    "water": {
        "locations": ["well"],
        "duration_sec": 300,
        "energy_cost": 15,
        "rewards": {"water": 3},
        "needs_energy": 15,
    },
    "training": {
        "locations": ["training"],
        "duration_sec": 600,
        "energy_cost": 25,
        "rewards": {"tokens": 2},
        "needs_energy": 25,
    },
}
