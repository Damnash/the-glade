# db/achievements.py

from db.connection import get_conn


# ============ Звания ============

def has_achievement(user_id: int, key: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM player_achievements
        WHERE user_id = ? AND achievement_key = ?
    """, (user_id, key))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def give_achievement(user_id: int, key: str, season_id: int = None) -> bool:
    """Выдать звание. Возвращает True если новое."""
    if has_achievement(user_id, key):
        return False

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO player_achievements (user_id, achievement_key, season_id)
        VALUES (?, ?, ?)
    """, (user_id, key, season_id))
    conn.commit()
    conn.close()
    return True


def get_player_achievements(user_id: int) -> list[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT achievement_key FROM player_achievements
        WHERE user_id = ?
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


# ============ Очки ============

def add_score(user_id: int, season_id: int, points: int, field: str = None):
    """Добавить очки и увеличить счётчик."""
    conn = get_conn()
    cur = conn.cursor()

    # Проверяем запись
    cur.execute("""
        SELECT * FROM season_scores
        WHERE user_id = ? AND season_id = ?
    """, (user_id, season_id))
    row = cur.fetchone()

    if not row:
        cur.execute("""
            INSERT INTO season_scores (user_id, season_id, score)
            VALUES (?, ?, ?)
        """, (user_id, season_id, points))
        # Инициализируем счётчики
        if field:
            cur.execute(f"""
                UPDATE season_scores SET {field} = 1
                WHERE user_id = ? AND season_id = ?
            """, (user_id, season_id))
    else:
        cur.execute("""
            UPDATE season_scores
            SET score = score + ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND season_id = ?
        """, (points, user_id, season_id))
        if field:
            cur.execute(f"""
                UPDATE season_scores SET {field} = {field} + 1
                WHERE user_id = ? AND season_id = ?
            """, (user_id, season_id))

    conn.commit()
    conn.close()


def get_player_score(user_id: int, season_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM season_scores
        WHERE user_id = ? AND season_id = ?
    """, (user_id, season_id))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_leaderboard(season_id: int, limit: int = 20) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*, p.display_name, p.username
        FROM season_scores s
        LEFT JOIN players p ON p.user_id = s.user_id
        WHERE s.season_id = ?
        ORDER BY s.score DESC
        LIMIT ?
    """, (season_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_by_field(season_id: int, field: str, limit: int = 5) -> list[dict]:
    if field not in ("kills", "griever_kills", "fragments", "deaths"):
        return []

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT s.*, p.display_name, p.username
        FROM season_scores s
        LEFT JOIN players p ON p.user_id = s.user_id
        WHERE s.season_id = ? AND s.{field} > 0
        ORDER BY s.{field} DESC
        LIMIT ?
    """, (season_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============ Зал Славы ============

def add_to_hall(season_id: int, user_id: int, display_name: str, key: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO hall_of_fame (season_id, user_id, display_name, achievement_key)
        VALUES (?, ?, ?, ?)
    """, (season_id, user_id, display_name, key))
    conn.commit()
    conn.close()


def get_hall_of_fame(limit: int = 100) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM hall_of_fame
        ORDER BY season_id DESC, achieved_at ASC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============ Врата ============

def get_gates_state(season_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM gates_state WHERE season_id = ?", (season_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def open_gates(season_id: int, opened_by: int, winner_ids: list[int]):
    import json
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO gates_state (season_id, opened_at, opened_by, winner_ids)
        VALUES (?, CURRENT_TIMESTAMP, ?, ?)
    """, (season_id, opened_by, json.dumps(winner_ids)))
    conn.commit()
    conn.close()


def is_gates_open(season_id: int) -> bool:
    state = get_gates_state(season_id)
    return state is not None and state.get("opened_at") is not None
