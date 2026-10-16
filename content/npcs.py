# content/npcs.py

NPCS = {
    "frypan": {
        "name_key": "npc.frypan.name",
        "desc_key": "npc.frypan.desc",
        "location": "kitchen",
        "dialog_key": "npc.frypan.dialog",
        "actions": ["trade_food"],
    },
    "clint": {
        "name_key": "npc.clint.name",
        "desc_key": "npc.clint.desc",
        "location": "forge",
        "dialog_key": "npc.clint.dialog",
        "actions": ["craft"],
    },
    "jeff": {
        "name_key": "npc.jeff.name",
        "desc_key": "npc.jeff.desc",
        "location": "medbay",
        "dialog_key": "npc.jeff.dialog",
        "actions": ["heal", "buy_bandage"],
    },
    "minho": {
        "name_key": "npc.minho.name",
        "desc_key": "npc.minho.desc",
        "location": "watchtower",
        "dialog_key": "npc.minho.dialog",
        "actions": ["story", "show_map"],
    },
    "chuck": {
        "name_key": "npc.chuck.name",
        "desc_key": "npc.chuck.desc",
        "location": "center",
        "dialog_key": "npc.chuck.dialog",
        "actions": ["hint"],
    },
    "alby": {
        "name_key": "npc.alby.name",
        "desc_key": "npc.alby.desc",
        "location": "council",
        "dialog_key": "npc.alby.dialog",
        "actions": ["story", "talk"],
    },
    "winston": {
        "name_key": "npc.winston.name",
        "desc_key": "npc.winston.desc",
        "location": "farms",
        "dialog_key": "npc.winston.dialog",
        "actions": ["trade"],
    },
    "newt": {
        "name_key": "npc.newt.name",
        "desc_key": "npc.newt.desc",
        "location": "center",
        "dialog_key": "npc.newt.dialog",
        "actions": ["talk"],
    },
    "gally": {
        "name_key": "npc.gally.name",
        "desc_key": "npc.gally.desc",
        "location": "training",
        "dialog_key": "npc.gally.dialog",
        "actions": ["respond_rude", "respond_silent", "respond_fight"],
    },
    "teresa": {
        "name_key": "npc.teresa.name",
        "desc_key": "npc.teresa.desc",
        "location": "abandoned_hut",
        "dialog_key": "npc.teresa.dialog",
        "actions": ["story", "talk"],
    },
}


def get_npcs_in_location(location: str) -> list[dict]:
    """Все NPC в локации."""
    return [
        {"key": k, **v}
        for k, v in NPCS.items()
        if v["location"] == location
    ]
