# db/players.py

from datetime import datetime

from db.connection import get_conn


def get_player(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_player(user_id: int, username: str, display_name: str, language: str, location: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR IGNORE INTO players
           (user_id, username, display_name, language, location)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, username, display_name, language, location),
    )
    conn.commit()
    conn.close()


def update_location(user_id: int, location: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE players SET location = ?, last_seen = ? WHERE user_id = ?",
        (location, datetime.utcnow(), user_id),
    )
    conn.commit()
    conn.close()


def update_language(user_id: int, language: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE players SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()
    conn.close()


def update_player_fields(user_id: int, fields: dict):
    if not fields:
        return
    import logging
    keys = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(f"UPDATE players SET {keys} WHERE user_id = ?", values)
        conn.commit()
        logging.info(f"[update_player_fields] user={user_id} fields={fields}")
    except Exception as e:
        logging.error(f"[update_player_fields] ERROR: {e}")
    finally:
        conn.close()


def players_in_location(location: str, exclude_id: int | None = None):
    conn = get_conn()
    cur = conn.cursor()
    if exclude_id:
        cur.execute(
            "SELECT * FROM players WHERE location = ? AND user_id != ?",
            (location, exclude_id),
        )
    else:
        cur.execute("SELECT * FROM players WHERE location = ?", (location,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_by_name(name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM players WHERE LOWER(username) = LOWER(?) OR LOWER(display_name) = LOWER(?)",
        (name, name),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_lang(user_id: int) -> str:
    player = get_player(user_id)
    return player["language"] if player else "en"

def die_and_respawn(user_id: int):
    """Убить игрока и респавнить в центре Глэййда."""
    from core.time_utils import now
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE players SET
            hp = 10,
            energy = 0,
            sanity = 100,
            food = 0,
            water = 0,
            location = 'center',
            maze_layer = 0,
            maze_section = NULL,
            status = 'active',
            work_type = NULL,
            work_ends_at = NULL,
            last_seen = ?,
            last_fed_at = ?,
            last_drank_at = ?,
            last_sanity_at = ?
        WHERE user_id = ?
    """, (now(), now(), now(), now(), user_id))
    conn.commit()
    conn.close()

