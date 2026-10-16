# core/maze_sizes.py

MAZE_SIZES = {
    "tiny":   {"wing_size": 5,  "center_size": 1},   # 4×5 + 1 = 21
    "small":  {"wing_size": 8,  "center_size": 1},   # 4×8 + 1 = 33
    "medium": {"wing_size": 15, "center_size": 1},   # 4×15 + 1 = 61
    "large":  {"wing_size": 30, "center_size": 2},   # 4×30 + 2 = 122
    "epic":   {"wing_size": 40, "center_size": 2},   # 4×40 + 2 = 162
}


def get_maze_size(tier: str) -> dict:
    """Параметры генерации для тира."""
    return MAZE_SIZES.get(tier, MAZE_SIZES["medium"])
