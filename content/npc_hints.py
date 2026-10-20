# content/npc_hints.py
#
# Подсказки от NPC.
# - Чак: 5 подсказок по очереди (по npc_visits).
# - Остальные: по 1 подсказке (один раз — потом «я уже говорил»).

NPC_HINTS = {
    "chuck": [
        "npc.chuck.hint.1",  # torches
        "npc.chuck.hint.2",  # food/water
        "npc.chuck.hint.3",  # don't fight alone
        "npc.chuck.hint.4",  # sleep
        "npc.chuck.hint.5",  # night dangerous
    ],
    "frypan": [
        "npc.frypan.hint.1",  # farm work
    ],
    "jeff": [
        "npc.jeff.hint.1",    # bandage
    ],
    "minho": [
        "npc.minho.hint.1",   # center / griever
    ],
    "winston": [
        "npc.winston.hint.1", # water / trade
    ],
    "alby": [
        "npc.alby.hint.1",    # council / story
    ],
}
