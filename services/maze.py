# services/maze.py

import random

from content.maze import MAZE_ENTRANCES, MAZE_EXITS, MAZE_SECTIONS
from core.player_state import update_player_state
from core.season import get_tier_config
from db.inventory import has_item, remove_item
from db.players import get_player, update_player_fields


class MazeError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


def check_gear(user_id: int) -> dict:
    """
    Проверка снаряжения. Возвращает dict с проблемами.
    Пустой dict = всё ок.
    """
    player = get_player(user_id)
    if not player:
        return {"error": "no_player"}

    tier = get_tier_config()
    problems = {}

    if player["hp"] < tier["hp"]:
        problems["hp"] = {"have": player["hp"], "need": tier["hp"]}
    if player["energy"] < tier["energy"]:
        problems["energy"] = {"have": player["energy"], "need": tier["energy"]}
    if player["food"] < tier["food"]:
        problems["food"] = {"have": player["food"], "need": tier["food"]}
    if player["water"] < tier["water"]:
        problems["water"] = {"have": player["water"], "need": tier["water"]}
    if not has_item(user_id, "knife"):
        problems["knife"] = {"have": 0, "need": 1}
    if not has_item(user_id, "torch", tier["torches"]):
        from db.inventory import get_inventory
        inv = {i["item_key"]: i["quantity"] for i in get_inventory(user_id)}
        problems["torch"] = {"have": inv.get("torch", 0), "need": tier["torches"]}
    if tier["rope"] > 0 and not has_item(user_id, "rope", tier["rope"]):
        from db.inventory import get_inventory
        inv = {i["item_key"]: i["quantity"] for i in get_inventory(user_id)}
        problems["rope"] = {"have": inv.get("rope", 0), "need": tier["rope"]}

    return problems


def enter_maze(user_id: int, gate: str) -> str:
    """
    Вход в Лабиринт.
    Возвращает ID секции в НОВОМ формате (L1_W1).

    Списание еды/воды здесь больше НЕ происходит.
    Еда/вода тратятся только за переход (см. services/survival.py).
    """
    from core.maze_current import get_current_season
    from db.maze_map import load_layer, save_layer
    from core.maze_generator import generate_layer

    player = update_player_state(get_player(user_id))
    if not player:
        raise MazeError("start.need_start")

    if gate not in MAZE_ENTRANCES:
        raise MazeError("maze.no_gate")

    if player["location"] != gate:
        raise MazeError("maze.wrong_place")

    if player["status"] == "sleeping":
        raise MazeError("maze.sleeping")

    if player["status"] == "working":
        raise MazeError("maze.working")

    # Ворота закрыты ночью (22:00 - 06:00 UTC)
    from core.daycycle import is_night
    if is_night():
        raise MazeError("maze.night_closed")

    tier = get_tier_config()

    # Списываем только расходники из инвентаря (факелы, верёвки).
    # Еда/вода — НЕ списываются (они тратятся за переход).
    for item, need in [
        ("torch", tier["torches"]),
        ("rope", tier["rope"]),
    ]:
        if need > 0:
            from db.inventory import get_inventory
            inv = {i["item_key"]: i["quantity"] for i in get_inventory(user_id)}
            have = inv.get(item, 0)
            to_remove = min(have, need)
            if to_remove > 0:
                remove_item(user_id, item, to_remove)

    # === Секция в НОВОМ формате ===
    season = get_current_season()
    layer_data = load_layer(season, 1)
    if not layer_data:
        layer_data = generate_layer(1, seed=season)
        save_layer(season, 1, layer_data)

    wing_map = {
        "north_gates": "N",
        "south_gates": "S",
        "west_gates": "W",
        "east_gates": "E",
    }
    wing = wing_map[gate]
    section_id = f"L1_{wing}1"

    # Story tracking
    try:
        from services.story import track_event
        track_event(user_id, "enter_maze")
    except Exception:
        pass

    # Автодневник
    try:
        from services.diary import add_diary_auto
        add_diary_auto(user_id, "enter_maze", section=section_id)
    except Exception:
        pass

    return section_id

def exit_maze(user_id: int) -> str:
    """Возврат в Глэйд. Возвращает ключ ворот."""
    player = update_player_state(get_player(user_id))
    if not player:
        raise MazeError("start.need_start")

    layer = player.get("maze_layer", 0)
    section_id = player.get("maze_section")

    if layer == 0 or not section_id:
        raise MazeError("maze.not_in_maze")

    # Парсим: L1_W1 → layer=1, wing=W
    try:
        parts = section_id.split("_")
        wing = parts[1][0]   # "W1" → "W"
    except (IndexError, ValueError):
        raise MazeError("maze.not_in_maze")

    wing_to_gate = {
        "N": "north_gates",
        "S": "south_gates",
        "W": "west_gates",
        "E": "east_gates",
    }
    gate = wing_to_gate.get(wing)
    if not gate:
        raise MazeError("maze.not_in_maze")

    # Автодневник
    try:
        from services.diary import add_diary_auto
        add_diary_auto(user_id, "exit_maze", gate=gate)
    except Exception:
        pass

    return gate

def roll_event(section_id: str, user_id: int, lang: str) -> str | None:
    """Случайное событие при осмотре. 8+ типов."""
    import random as _r
    from content.maze_events import MAZE_EVENTS

    roll = _r.random()

    # 40% — «ничего», но с атмосферным текстом «тишины»
    if roll < 0.40:
        from content.silence_texts import SILENCE_TEXTS
        from core.i18n import t
        import random as _r
        key = _r.choice(SILENCE_TEXTS)
        return t(key, lang)

    # Выбираем событие по весам
    roll2 = _r.random()
    cumulative = 0.0

    for event_key, spec in MAZE_EVENTS.items():
        cumulative += spec["chance"]
        if roll2 < cumulative:
            return _apply_event(event_key, spec, user_id, lang)

    return None


def _apply_event(event_key: str, spec: dict, user_id: int, lang: str) -> str:
    """Применить событие."""
    import random as _r
    from core.i18n import t

    text_key = spec["text_key"]
    event_type = spec["type"]

    if event_type == "reward":
        item = spec.get("item", "food")
        qty = spec.get("qty", 1)

        if item == "random":
            item = _r.choice(["food", "water", "torch", "rope", "metal"])
            qty = _r.randint(1, 2)

        from db.inventory import add_item
        add_item(user_id, item, qty)

        item_name = t(f"item.{item}.name", lang)
        return t(text_key, lang, item=item_name, qty=qty)

    if event_type == "damage":
        from db.players import get_player, update_player_fields
        damage = spec.get("damage", 5)
        player = get_player(user_id)
        new_hp = max(0, player["hp"] - damage)
        update_player_fields(user_id, {"hp": new_hp})
        return t(text_key, lang, dmg=damage)

    if event_type == "teleport":
        from db.players import get_player, update_player_fields
        from db.maze_map import load_layer
        from core.maze_current import get_current_season

        player = get_player(user_id)
        season = get_current_season()
        layer = player.get("maze_layer", 1)
        layer_data = load_layer(season, layer)

        if layer_data:
            new_section = _r.choice(list(layer_data["sections"].keys()))
            update_player_fields(user_id, {"maze_section": new_section})

        return t(text_key, lang)

    # story / riddle / hint — просто текст
    return t(text_key, lang)

# ============ Эхо прошлых рейдов ============

ECHO_CHANCE = 0.30  # 30% при осмотре секции


def roll_echo(section_id: str, user_id: int, lang: str) -> str | None:
    """Иногда при осмотре — след другого игрока (атмосферное эхо)."""
    import random as _r
    from content.echoes import ECHOES
    from core.i18n import t

    if _r.random() > ECHO_CHANCE:
        return None
    key = _r.choice(ECHOES)
    return t(key, lang)

