# db/story.py

from db.connection import get_conn


# ============ Этапы ============

def unlock_stage(user_id: int, stage_key: str):
    from datetime import datetime
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO story_stages (user_id, stage_key, status, unlocked_at)
        VALUES (?, ?, 'unlocked', ?)
    """, (user_id, stage_key, datetime.utcnow()))
    conn.commit()
    conn.close()


def is_stage_unlocked(user_id: int, stage_key: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM story_stages
        WHERE user_id = ? AND stage_key = ? AND status = 'unlocked'
    """, (user_id, stage_key))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def get_player_stages(user_id: int) -> list[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT stage_key FROM story_stages
        WHERE user_id = ? AND status = 'unlocked'
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


# ============ Квесты ============

def get_quest_status(user_id: int, quest_key: str) -> str:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT status FROM story_quests
        WHERE user_id = ? AND quest_key = ?
    """, (user_id, quest_key))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else "available"


def set_quest_status(user_id: int, quest_key: str, status: str):
    from datetime import datetime
    conn = get_conn()
    cur = conn.cursor()

    if status == "active":
        cur.execute("""
            INSERT OR REPLACE INTO story_quests (user_id, quest_key, status, progress, started_at)
            VALUES (?, ?, 'active', 0, ?)
        """, (user_id, quest_key, datetime.utcnow()))
    elif status == "complete":
        cur.execute("""
            UPDATE story_quests SET status = 'complete', completed_at = ?
            WHERE user_id = ? AND quest_key = ?
        """, (datetime.utcnow(), user_id, quest_key))

    conn.commit()
    conn.close()


def add_progress(user_id: int, quest_key: str, amount: int = 1) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE story_quests SET progress = progress + ?
        WHERE user_id = ? AND quest_key = ? AND status = 'active'
    """, (amount, user_id, quest_key))
    conn.commit()

    cur.execute("""
        SELECT progress FROM story_quests
        WHERE user_id = ? AND quest_key = ?
    """, (user_id, quest_key))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def get_active_quests(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT quest_key, status, progress FROM story_quests
        WHERE user_id = ?
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
