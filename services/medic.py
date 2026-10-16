# services/medic.py

def can_heal(player: dict) -> tuple[bool, str]:
    """
    Может ли игрок лечиться.
    Возвращает (можно, ошибка).
    """
    from db.inventory import has_item

    if player.get("hp", 0) >= 100:
        return False, "medic.already_full"

    if not has_item(player["user_id"], "bandage"):
        return False, "medic.no_bandage"

    return True, ""


def heal_self(user_id: int) -> dict:
    """Вылечиться бинтом."""
    from db.players import get_player, update_player_fields
    from db.inventory import remove_item
    from services.bonuses import get_player_bonus

    player = get_player(user_id)
    if not player:
        raise ValueError("No player")

    can, error = can_heal(player)
    if not can:
        raise ValueError(error)

    bonus = get_player_bonus(player)
    heal_amount = 20 + bonus["heal_bonus"] * 5  # медик лечит на +5

    if not remove_item(user_id, "bandage", 1):
        raise ValueError("medic.no_bandage")

    new_hp = min(100, player["hp"] + heal_amount)
    update_player_fields(user_id, {"hp": new_hp})

    return {
        "healed": heal_amount,
        "hp": new_hp,
    }
