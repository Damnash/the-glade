# content/rumors.py
#
# Слухи от NPC — добавляются к диалогу с шансом 20%.
# Длинные тексты (2-3 предложения).

RUMORS = {
    "frypan": [
        "rumor.frypan_key",
        "rumor.frypan_griever",
        "rumor.frypan_night",
    ],
    "chuck": [
        "rumor.chuck_teresa",
        "rumor.chuck_maze",
        "rumor.chuck_light",
    ],
    "minho": [
        "rumor.minho_center",
        "rumor.minho_west",
        "rumor.minho_keys",
    ],
    "jeff": [
        "rumor.jeff_scratches",
        "rumor.jeff_dead",
    ],
    "winston": [
        "rumor.winston_water",
        "rumor.winston_north",
    ],
}

RUMOR_CHANCE = 0.20
