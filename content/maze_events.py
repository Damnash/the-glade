# content/maze_events.py

MAZE_EVENTS = {
    # === Существующие ===
    "find_food": {
        "chance": 0.12,
        "type": "reward",
        "item": "food",
        "qty": 1,
        "text_key": "event.find_food",
    },
    "find_water": {
        "chance": 0.08,
        "type": "reward",
        "item": "water",
        "qty": 1,
        "text_key": "event.find_water",
    },
    "trap_stone": {
        "chance": 0.10,
        "type": "damage",
        "damage": 5,
        "text_key": "event.trap_stone",
    },

    # === НОВЫЕ ===
    "corpse": {
        "chance": 0.05,
        "type": "reward",
        "item": "random",
        "qty": 2,
        "text_key": "event.corpse",
    },
    "walls_shift": {
        "chance": 0.04,
        "type": "teleport",
        "text_key": "event.walls_shift",
    },
    "wicked_voice": {
        "chance": 0.03,
        "type": "story",
        "text_key": "event.wicked_voice",
    },
    "riddle": {
        "chance": 0.03,
        "type": "riddle",
        "text_key": "event.riddle",
    },
    "old_marks": {
        "chance": 0.06,
        "type": "hint",
        "text_key": "event.old_marks",
    },
    "find_metal": {
        "chance": 0.07,
        "type": "reward",
        "item": "metal",
        "qty": 1,
        "text_key": "event.find_metal",
    },
}
