# services/inventory.py

from content.items import ITEMS
from core.i18n import get_all_translations
from core.time_utils import now
from db.inventory import get_inventory, add_item, remove_item, has_item
from db.players import get_player, update_player_fields


class InvError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


def resolve_item_key(user_input: str) -> str | None:
    """Ищет ключ предмета по алиасам из локалей."""
    user_input = user_input.strip().lower()
    for lang_data in get_all_translations().values():
        for key, aliases in lang_data.items():
            if not key.startswith("aliases.item."):
                continue
            item_key = key[len("aliases.item."):]
            if isinstance(aliases, str):
                aliases = [aliases]
            if user_input in [a.lower() for a in aliases]:
                return item_key
    return None


def list_inventory(user_id: int) -> list[dict]:
    return get_inventory(user_id)


def use_item(user_id: int, raw_input: str) -> dict:
    item_key = resolve_item_key(raw_input)
    if not item_key or item_key not in ITEMS:
        raise InvError("inv.unknown")

    if not has_item(user_id, item_key):
        raise InvError("inv.missing")

    spec = ITEMS[item_key]
    action = spec.get("use")

    if action is None:
        raise InvError("inv.not_usable")

    if action == "eat":
        if not remove_item(user_id, item_key):
            raise InvError("inv.missing")
        player = get_player(user_id)
        new_hp = min(100, player["hp"] + 10)
        update_player_fields(user_id, {"hp": new_hp, "last_fed_at": now()})
        return {"action": "eat", "hp": new_hp}

    if action == "drink":
        if not remove_item(user_id, item_key):
            raise InvError("inv.missing")
        player = get_player(user_id)
        new_water = player["water"] + 1
        update_player_fields(user_id, {"water": new_water})
        return {"action": "drink", "water": new_water}

    raise InvError("inv.not_usable")