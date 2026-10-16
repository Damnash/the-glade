# services/event_log.py

from db.connection import get_conn


def add_event(user_id: int, event_type: str, text: str):
    """Добавить событие в лог игрока."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO player_log (user_id, event_type, text)
        VALUES (?, ?, ?)
    """, (user_id, event_type, text))
    conn.commit()
    conn.close()


def get_recent_events(user_id: int, limit: int = 6) -> list[dict]:
    """Последние события игрока."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT event_type, text, created_at FROM player_log
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def cleanup_old_events(user_id: int, keep: int = 30):
    """Оставить только N последних событий."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM player_log
        WHERE user_id = ? AND id NOT IN (
            SELECT id FROM player_log
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        )
    """, (user_id, user_id, keep))
    conn.commit()
    conn.close()
