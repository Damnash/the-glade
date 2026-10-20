# services/event_log.py

from db.connection import get_conn


def add_event(user_id: int, event_type: str, text: str, severity: str = "important"):
    """Добавить событие в лог игрока.

    severity:
      - "important" — показывается в главном меню (находки, бой, смерть, работа)
      - "chat"      — только в /journal (say, радио, шёпот, клан-чат)
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO player_log (user_id, event_type, text, severity)
        VALUES (?, ?, ?, ?)
    """, (user_id, event_type, text, severity))
    conn.commit()
    conn.close()


def get_recent_events(user_id: int, limit: int = 6, severity: str | None = None) -> list[dict]:
    """Последние события игрока.

    severity=None — все события;
    severity="important" — только важные (для главного меню);
    severity="chat" — только чат (для /journal).
    """
    conn = get_conn()
    cur = conn.cursor()
    if severity:
        cur.execute("""
            SELECT event_type, text, created_at, severity FROM player_log
            WHERE user_id = ? AND severity = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, severity, limit))
    else:
        cur.execute("""
            SELECT event_type, text, created_at, severity FROM player_log
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
