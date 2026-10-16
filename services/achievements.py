# services/achievements.py

from core.i18n import t
from core.maze_current import get_current_season
from content.achievements import ACHIEVEMENTS, SCORE_VALUES
from db.achievements import (
    has_achievement, give_achievement, get_player_achievements,
    add_score, get_player_score, get_leaderboard, get_top_by_field,
    add_to_hall, get_hall_of_fame,
    open_gates, is_gates_open, get_gates_state,
)
from db.players import get_player


# ============ Очки за действия ============

def award_points(user_id: int, action: str, field: str = None):
    """Начислить очки за действие."""
    points = SCORE_VALUES.get(action, 0)
    if points == 0:
        return

    season_id = get_current_season()
    add_score(user_id, season_id, points, field=field)


# ============ Автоматическая выдача званий ============

def check_cartographer(user_id: int):
    """Если 30+ фрагментов — звание."""
    season_id = get_current_season()
    score = get_player_score(user_id, season_id)
    if score and score.get("fragments", 0) >= 30:
        if give_achievement(user_id, "cartographer", season_id):
            return True
    return False


def check_hunter(user_id: int):
    """Если 10+ Гриверов — звание."""
    season_id = get_current_season()
    score = get_player_score(user_id, season_id)
    if score and score.get("griever_kills", 0) >= 10:
        if give_achievement(user_id, "hunter", season_id):
            return True
    return False


# ============ Финал — победа ============

def try_open_gates(user_id: int) -> dict | None:
    """
    Попытка открыть Врата.
    Возвращает dict с деталями или None.
    """
    season_id = get_current_season()

    # Уже открыты?
    if is_gates_open(season_id):
        return None

    # Проверяем: у игрока все 5 ключей
    from db.keys import has_player_key
    for k in [1, 2, 3, 4, 5]:
        if not has_player_key(season_id, user_id, k):
            return None

    # Проверяем: сколько игроков в центре Лабиринта
    player = get_player(user_id)
    if not player:
        return None

    section_id = player.get("maze_section")
    layer = player.get("maze_layer", 1)

    if not section_id or layer == 0:
        return None

    from db.maze_map import get_section
    section = get_section(season_id, layer, section_id)

    if not section or section["type"] != "center":
        return None

    # Все игроки в центре
    from db.players import players_in_location
    others = players_in_location(player["location"], exclude_id=None)

    # Собираем всех, кто в центре
    winners = [user_id]
    for p in others:
        if p.get("maze_section") == section_id and p.get("maze_layer") == layer:
            winners.append(p["user_id"])

    # Порог по тиру
    from core.season import get_tier_config
    tier = get_tier_config()
    needed_players = tier.get("players_at_gates", 1)

    if len(winners) < needed_players:
        return None

    # Открываем
    open_gates(season_id, user_id, winners)

    # Выдаём звания
    from db.players import get_player
    for wid in winners:
        w = get_player(wid)
        if not w:
            continue
        name = w["display_name"] or w["username"]

        # Freed — всем
        give_achievement(wid, "freed", season_id)
        add_to_hall(season_id, wid, name, "freed")

        # Ключник — тому, у кого ключ 5
        if has_player_key(season_id, wid, 5):
            give_achievement(wid, "key_bearer", season_id)
            add_to_hall(season_id, wid, name, "key_bearer")

    # Первопроходец — тот, кто открыл
    first = get_player(user_id)
    if first:
        fname = first["display_name"] or first["username"]
        give_achievement(user_id, "first_runner", season_id)
        add_to_hall(season_id, user_id, fname, "first_runner")

    # Очки
    for wid in winners:
        award_points(wid, "open_gates")

        # Story tracking
        try:
            from services.story import track_event
            track_event(wid, "open_gates")
        except Exception:
            pass

    return {
        "season_id": season_id,
        "winners": winners,
        "opened_by": user_id,
    }


def get_gates_info() -> dict:
    """Информация о Вратах."""
    season_id = get_current_season()
    is_open = is_gates_open(season_id)
    state = get_gates_state(season_id)

    return {
        "is_open": is_open,
        "state": state,
        "season_id": season_id,
    }


# ============ Таблица ============

def get_full_leaderboard(season_id: int) -> dict:
    """Полная таблица лидеров."""
    return {
        "score": get_leaderboard(season_id, limit=20),
        "kills": get_top_by_field(season_id, "kills", limit=5),
        "griever_kills": get_top_by_field(season_id, "griever_kills", limit=5),
        "fragments": get_top_by_field(season_id, "fragments", limit=5),
    }


# ============ Конец сезона ============

def end_season(season_id: int) -> dict:
    """
    Завершить сезон.
    Возвращает статистику.
    """
    # Топ-3 по очкам
    top = get_leaderboard(season_id, limit=3)

    # Утешительные звания
    if top:
        from db.players import get_player
        for i, entry in enumerate(top):
            uid = entry["user_id"]
            p = get_player(uid)
            if not p:
                continue

            name = p["display_name"] or p["username"]

            if i == 0:
                give_achievement(uid, "cartographer", season_id)  # top-1
                add_to_hall(season_id, uid, name, "top1")
            elif i == 1:
                add_to_hall(season_id, uid, name, "top2")
            elif i == 2:
                add_to_hall(season_id, uid, name, "top3")

    return {
        "season_id": season_id,
        "top": top,
    }


def get_player_achievements_list(user_id: int) -> list[dict]:
    """Звания игрока с описанием."""
    keys = get_player_achievements(user_id)
    result = []
    for key in keys:
        spec = ACHIEVEMENTS.get(key, {})
        result.append({
            "key": key,
            "icon": spec.get("icon", "❓"),
        })
    return result
