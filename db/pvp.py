# db/pvp.py

from datetime import datetime, timedelta

from db.connection import get_conn


SHIELD_HOURS = 24
STEAL_COOLDOWN_SEC = 3600
DUEL_TTL_HOURS = 2


# ============ Щит новичка ============

def give_shield(user_id: int, hours: int = SHIELD_HOURS):
    """Выдать щит новичка."""
    expires = datetime.utcnow() + timedelta(hours=hours)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO player_shields (user_id, expires_at)
        VALUES (?, ?)
    """, (user_id, expires))
    conn.commit()
    conn.close()


def has_shield(user_id: int) -> bool:
    """Есть ли активный щит."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT expires_at FROM player_shields
        WHERE user_id = ? AND expires_at > ?
    """, (user_id, datetime.utcnow()))
    row = cur.fetchone()
    conn.close()
    return bool(row)


# ============ Кража ============

def get_steal_cooldown(user_id: int) -> int:
    """Секунд до следующей кражи. 0 если можно."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT last_steal FROM steal_cooldowns WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return 0

    last = row[0]
    if isinstance(last, str):
        last = datetime.fromisoformat(last)

    elapsed = (datetime.utcnow() - last).total_seconds()
    left = STEAL_COOLDOWN_SEC - elapsed
    return max(0, int(left))


def set_steal_cooldown(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO steal_cooldowns (user_id, last_steal)
        VALUES (?, ?)
    """, (user_id, datetime.utcnow()))
    conn.commit()
    conn.close()


# ============ Дуэли ============

def create_duel(challenger_id: int, opponent_id: int, stake: int) -> int:
    expires = datetime.utcnow() + timedelta(hours=DUEL_TTL_HOURS)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO duels (challenger_id, opponent_id, stake_tokens, expires_at)
        VALUES (?, ?, ?, ?)
    """, (challenger_id, opponent_id, stake, expires))
    duel_id = cur.lastrowid
    conn.commit()
    conn.close()
    return duel_id


def get_duel(duel_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM duels WHERE id = ?", (duel_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_pending_duel_for(user_id: int) -> dict | None:
    """Ожидающая дуэль для игрока (его вызвали)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM duels
        WHERE opponent_id = ? AND status = 'pending' AND expires_at > ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id, datetime.utcnow()))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def set_duel_status(duel_id: int, status: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE duels SET status = ? WHERE id = ?", (status, duel_id))
    conn.commit()
    conn.close()


def cleanup_expired_duels():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM duels WHERE expires_at <= ? AND status = 'pending'",
                (datetime.utcnow(),))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


# ============ PvP-лог ============

def log_pvp(killer_id: int, victim_id: int, action: str,
            section_id: str = None, layer: int = None,
            tokens_gained: int = 0, items_gained: int = 0):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pvp_log
        (killer_id, victim_id, action, section_id, layer, tokens_gained, items_gained)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (killer_id, victim_id, action, section_id, layer, tokens_gained, items_gained))
    conn.commit()
    conn.close()


def get_player_kills(user_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pvp_log WHERE killer_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_player_deaths(user_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pvp_log WHERE victim_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count


# ============ PvP флаг (v1.1) ============

PVP_FLAG_HOURS = 24


def set_pvp_flag(user_id: int, hours: int = PVP_FLAG_HOURS):
    """Включить PvP флаг на N часов."""
    expires = datetime.utcnow() + timedelta(hours=hours)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO pvp_flags (user_id, expires_at)
        VALUES (?, ?)
    """, (user_id, expires))
    conn.commit()
    conn.close()


def clear_pvp_flag(user_id: int):
    """Выключить PvP флаг."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM pvp_flags WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def has_pvp_flag(user_id: int) -> bool:
    """Есть ли активный PvP флаг."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM pvp_flags
        WHERE user_id = ? AND expires_at > ?
    """, (user_id, datetime.utcnow()))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def get_pvp_flag_time_left(user_id: int) -> int:
    """Секунд до истечения флага (0 если нет)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT expires_at FROM pvp_flags WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return 0

    expires = row[0]
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)

    delta = (expires - datetime.utcnow()).total_seconds()
    return max(0, int(delta))
