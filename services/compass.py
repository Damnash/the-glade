# services/compass.py

def get_compass_hint(user_id: int, lang: str) -> str:
    """
    Показывает направление компаса.
    Если в Лабиринте — к ближайшему выходу.
    """
    from db.players import get_player
    from core.i18n import t
    from core.maze_current import get_current_season
    from db.maze_map import load_layer

    player = get_player(user_id)
    if not player:
        return t("compass.no_player", lang)

    if player.get("maze_layer", 0) == 0:
        return t("compass.not_in_maze", lang)

    layer = player["maze_layer"]
    section_id = player.get("maze_section")

    if not section_id:
        return t("compass.not_in_maze", lang)

    season = get_current_season()
    layer_data = load_layer(season, layer)

    if not layer_data:
        return t("compass.no_data", lang)

    sections = layer_data["sections"]

    # Ищем ближайший выход (ring == 1 любой из крыльев)
    exit_sections = {
        "N": layer_data["entrances"].get("N"),
        "S": layer_data["entrances"].get("S"),
        "W": layer_data["entrances"].get("W"),
        "E": layer_data["entrances"].get("E"),
    }

    # BFS до ближайшего выхода
    from collections import deque

    queue = deque([(section_id, 0)])
    visited = {section_id}
    found_exit = None
    found_dist = None

    while queue:
        current, dist = queue.popleft()

        for wing, exit_id in exit_sections.items():
            if current == exit_id:
                found_exit = (wing, exit_id)
                found_dist = dist
                break

        if found_exit:
            break

        if current in sections:
            for nxt in sections[current]["exits"]:
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, dist + 1))

    if not found_exit:
        return t("compass.no_exit", lang)

    wing, _ = found_exit
    wing_name = {
        "N": t("loc.north_gates.name", lang),
        "S": t("loc.south_gates.name", lang),
        "W": t("loc.west_gates.name", lang),
        "E": t("loc.east_gates.name", lang),
    }[wing]

    return t("compass.towards", lang, wing=wing_name, dist=found_dist)
