# core/maze_current.py

from datetime import datetime

from db.connection import get_conn


def get_current_season() -> int:
    """Возвращает ID текущего сезона. Создаёт, если нет."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT season_id FROM maze_state ORDER BY season_id DESC LIMIT 1")
    row = cur.fetchone()

    if row:
        conn.close()
        return row[0]

    cur.execute("""
        INSERT INTO maze_state (season_id, start_date, layers_unlocked)
        VALUES (1, ?, 1)
    """, (datetime.utcnow(),))
    conn.commit()
    conn.close()
    return 1


def get_season_day(season_id: int) -> int:
    """День сезона (1..90)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT start_date FROM maze_state WHERE season_id = ?", (season_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return 1

    start = row[0]
    if isinstance(start, str):
        start = datetime.fromisoformat(start)

    days = (datetime.utcnow() - start).days + 1
    return max(1, min(90, days))


def get_layers_unlocked(season_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT layers_unlocked FROM maze_state WHERE season_id = ?", (season_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 1


def unlock_layer(season_id: int, layer: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE maze_state SET layers_unlocked = ? WHERE season_id = ?",
        (layer, season_id),
    )
    conn.commit()
    conn.close()