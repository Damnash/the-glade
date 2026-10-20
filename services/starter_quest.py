# services/starter_quest.py
#
# Первый квест после intro: «Поработай на фермах (5 минут)».

from db.connection import get_conn
from db.players import get_player, update_player_fields


STARTER_REWARD = {
    "tokens": 10,
    "food": 2,
}


def get_starter_quest(user_id: int) -> dict | None:
    """Активный первый квест (если есть)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, status, started_at, completed_at
            FROM starter_quest
            WHERE user_id = ?
        """, (user_id,))
        row = cur.fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def start_starter_quest(user_id: int) -> dict:
    """Запустить первый квест (если нет активного)."""
    existing = get_starter_quest(user_id)
    if existing:
        return existing

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO starter_quest (user_id, status)
            VALUES (?, 'active')
        """, (user_id,))
        conn.commit()
    finally:
        conn.close()

    return get_starter_quest(user_id)


def complete_starter_quest(user_id: int) -> dict | None:
    """Завершить первый квест и выдать награду. Возвращает награду или None."""
    quest = get_starter_quest(user_id)
    if not quest or quest["status"] != "active":
        return None

    # Выдать награду
    player = get_player(user_id)
    if not player:
        return None

    update_player_fields(user_id, {
        "tokens": player.get("tokens", 0) + STARTER_REWARD["tokens"],
        "food": min(player.get("max_food", 10), player.get("food", 0) + STARTER_REWARD["food"]),
    })

    # Отметить выполненным
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE starter_quest SET status = 'complete', completed_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()
    finally:
        conn.close()

    # Записать в журнал (important)
    try:
        from core.i18n import t
        from services.event_log import add_event, cleanup_old_events
        lang = player["language"]
        add_event(user_id, "starter_done",
                  t("starter.done", lang, tokens=STARTER_REWARD["tokens"], food=STARTER_REWARD["food"]),
                  severity="important")
        cleanup_old_events(user_id)
    except Exception:
        pass

    return STARTER_REWARD
