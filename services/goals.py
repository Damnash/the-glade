# services/goals.py
#
# Среднесрочные цели игрока.
# Первая: «5 фрагментов → карта-путеводитель».

from db.connection import get_conn
from db.players import get_player


FRAGMENT_GOAL = 5


def get_fragment_goal_status(user_id: int) -> dict:
    """Прогресс цели «5 фрагментов»."""
    from core.maze_current import get_current_season
    season = get_current_season()

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT fragments FROM season_scores
            WHERE user_id = ? AND season_id = ?
        """, (user_id, season))
        row = cur.fetchone()
    finally:
        conn.close()

    have = (row[0] if row else 0) or 0
    return {
        "have": have,
        "need": FRAGMENT_GOAL,
        "done": have >= FRAGMENT_GOAL,
    }


def check_fragment_goal(user_id: int) -> bool:
    """Проверить, достигнута ли цель «5 фрагментов».
    Если да и ещё не отмечена — нанести секции на карту и вернуть True.
    """
    status = get_fragment_goal_status(user_id)
    if not status["done"]:
        return False

    # Уже отмечена?
    player = get_player(user_id)
    if not player:
        return False
    if player.get("fragment_goal_done"):
        return False

    # Пометить (добавим колонку в players)
    from db.players import update_player_fields
    update_player_fields(user_id, {"fragment_goal_done": 1})

    # Нанести все секции слоя 1 на личную карту
    try:
        from services.maps import ensure_personal_map, draw_section
        from db.maze_map import load_layer
        from core.maze_current import get_current_season

        season = get_current_season()
        pm = ensure_personal_map(user_id, player.get("display_name") or player.get("username") or "Runner")
        layer_data = load_layer(season, 1)
        if layer_data:
            for sid in layer_data["sections"]:
                try:
                    draw_section(user_id, pm["id"], sid, layer=1)
                except Exception:
                    pass
    except Exception:
        pass

    # Выдать титул cartographer_5
    try:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO player_titles (user_id, title_key)
                VALUES (?, 'cartographer_5')
            """, (user_id,))
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    # Записать в журнал (important) + diary
    try:
        from core.i18n import t
        from services.event_log import add_event, cleanup_old_events
        from services.diary import add_diary_auto
        lang = player["language"]
        add_event(user_id, "fragment_goal_done",
                  t("goal.fragments.done", lang, n=FRAGMENT_GOAL),
                  severity="important")
        cleanup_old_events(user_id)
        add_diary_auto(user_id, "fragment_goal_done", n=FRAGMENT_GOAL)
    except Exception:
        pass

    return True


def get_goal_banner(user_id: int, lang: str) -> str:
    """Строка баннера для главного меню (если цель не достигнута)."""
    status = get_fragment_goal_status(user_id)
    if status["done"]:
        return ""
    from core.i18n import t
    have = status["have"]
    need = status["need"]
    filled = min(need, max(0, int(round(have * 5 / need))))
    bar = "█" * filled + "░" * (5 - filled)
    return t("goal.fragments.banner", lang, have=have, need=need, bar=bar)
