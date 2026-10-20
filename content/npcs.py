# content/npcs.py

NPCS = {
    "frypan": {
        "name_key": "npc.frypan.name",
        "desc_key": "npc.frypan.desc",
        "location": "kitchen",
        "dialog_key": "npc.frypan.dialog",
        "actions": ["trade_food", "bring_meat", "hint"],
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
        "actions": ["heal", "buy_bandage", "hint"],
    },
    "minho": {
        "name_key": "npc.minho.name",
        "desc_key": "npc.minho.desc",
        "location": "watchtower",
        "dialog_key": "npc.minho.dialog",
        "actions": ["story", "show_map", "hint"],
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
        "actions": ["story", "talk", "hint"],
    },
    "winston": {
        "name_key": "npc.winston.name",
        "desc_key": "npc.winston.desc",
        "location": "farms",
        "dialog_key": "npc.winston.dialog",
        "actions": ["trade", "bring_water", "hint"],
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



# ============ Варианты диалога по состоянию игрока ============
#
# state: "low_hp" | "low_food" | "first_visit" | "default"
# Если ключа нет — используется npc["dialog_key"].

NPC_DIALOG_BY_STATE = {
    "frypan": {
        "low_food": "npc.frypan.dialog_hungry",
        "first_visit": "npc.frypan.dialog_first",
    },
    "jeff": {
        "low_hp": "npc.jeff.dialog_hurt",
    },
    "minho": {
        "first_visit": "npc.minho.dialog_first",
    },
    "teresa": {
        "first_visit": "npc.teresa.dialog_first",
        "learned_truth": "npc.teresa.dialog_truth",
    },
    "newt": {
        "first_visit": "npc.newt.dialog_first",
        "low_hp": "npc.newt.dialog_hurt",
        "learned_truth": "npc.newt.dialog_truth",
    },
    "chuck": {
        "first_visit": "npc.chuck.dialog_first",
        "learned_truth": "npc.chuck.dialog_truth",
    },
    "alby": {
        "first_visit": "npc.alby.dialog_first",
        "low_hp": "npc.alby.dialog_hurt",
        "learned_truth": "npc.alby.dialog_truth",
    },
    "winston": {
        "first_visit": "npc.winston.dialog_first",
        "low_food": "npc.winston.dialog_hungry",
    },
    "gally": {
        "first_visit": "npc.gally.dialog_first",
        "low_hp": "npc.gally.dialog_hurt",
    },
}


def get_npc_dialog_key(npc_key: str, player: dict, is_first_visit: bool = False) -> str:
    """Выбрать ключ диалога NPC по состоянию игрока."""
    npc = NPCS.get(npc_key)
    if not npc:
        return "npc.not_implemented"
    variants = NPC_DIALOG_BY_STATE.get(npc_key, {})

    # low_hp
    if player.get("hp", 100) < 30 and "low_hp" in variants:
        return variants["low_hp"]
    # low_food
    if player.get("food", 0) <= 0 and "low_food" in variants:
        return variants["low_food"]
    # learned_truth (по стадии сюжета)
    if "learned_truth" in variants:
        try:
            from db.story import is_stage_unlocked
            if is_stage_unlocked(player["user_id"], "learned_truth"):
                return variants["learned_truth"]
        except Exception:
            pass
    # first_visit
    if is_first_visit and "first_visit" in variants:
        return variants["first_visit"]

    return npc["dialog_key"]

# ============ Ночные локации NPC ============
# Ночью все спят (huts), кроме стражи и Терезы.

NPC_NIGHT_LOCATIONS = {
    "frypan": "huts",
    "clint": "huts",
    "jeff": "huts",
    "chuck": "huts",
    "newt": "huts",
    "gally": "huts",
    "winston": "huts",
    "minho": "watchtower",        # стража
    "alby": "council",            # совет
    "teresa": "abandoned_hut",    # не спит
}


def get_npcs_in_location(location: str, is_night: bool = False) -> list[dict]:
    """Все NPC в локации (учитывая ночные перемещения)."""
    result = []
    for k, v in NPCS.items():
        eff_loc = NPC_NIGHT_LOCATIONS.get(k, v["location"]) if is_night else v["location"]
        if eff_loc == location:
            result.append({"key": k, **v})
    return result

