# db/keys.py

from datetime import datetime, timedelta

from db.connection import get_conn


# День появления ключа
KEY_DAY = {
    1: 1,    # авто при старте
    2: 15,
    3: 30,
    4: 50,
    5: 70,
}

# Через сколько дней дубликат
KEY_DUPLICATE_DAYS = {
    2: 10,
    3: 14,
    4: 14,
    5: 7,
}


def has_player_key(season_id: int, user_id: int, key_number: int) -> bool:
    """Есть ли у игрока ключ."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM season_keys
        WHERE season_id = ? AND found_by = ? AND key_number = ?
        LIMIT 1
    """, (season_id, user_id, key_number))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def get_player_keys(season_id: int, user_id: int) -> list[int]:
    """Все ключи игрока."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT key_number FROM season_keys
        WHERE season_id = ? AND found_by = ?
        ORDER BY key_number
    """, (season_id, user_id))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def key_exists_unfound(season_id: int, key_number: int) -> bool:
    """Есть ли нераскрытый ключ в мире."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM season_keys
        WHERE season_id = ? AND key_number = ? AND found_by IS NULL
        LIMIT 1
    """, (season_id, key_number))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def key_spawned(season_id: int, key_number: int) -> bool:
    """Появился ли ключ вообще."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM season_keys
        WHERE season_id = ? AND key_number = ?
        LIMIT 1
    """, (season_id, key_number))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def spawn_key(season_id: int, key_number: int, section_id: str, wing: str,
              layer: int, duplicate_of: int | None = None) -> int:
    """Разместить ключ в секции."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO season_keys
        (season_id, key_number, layer, section_id, wing, duplicate_of)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (season_id, key_number, layer, section_id, wing, duplicate_of))
    key_id = cur.lastrowid
    conn.commit()
    conn.close()
    return key_id


def find_key_in_section(season_id: int, layer: int, section_id: str) -> dict | None:
    """Найти нераскрытый ключ в секции."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM season_keys
        WHERE season_id = ? AND layer = ? AND section_id = ? AND found_by IS NULL
        LIMIT 1
    """, (season_id, layer, section_id))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def mark_key_found(key_id: int, user_id: int):
    """Отметить, что ключ найден."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE season_keys SET found_by = ?, found_at = ?
        WHERE id = ?
    """, (user_id, datetime.utcnow(), key_id))
    conn.commit()
    conn.close()


def get_all_spawned_keys(season_id: int) -> list[dict]:
    """Все ключи сезона."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM season_keys
        WHERE season_id = ?
        ORDER BY key_number, id
    """, (season_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_key_by_number(season_id: int, key_number: int) -> list[dict]:
    """Все экземпляры ключа."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM season_keys
        WHERE season_id = ? AND key_number = ?
        ORDER BY id
    """, (season_id, key_number))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def drop_player_key(season_id: int, user_id: int, key_number: int,
                    section_id: str, layer: int, wing: str) -> bool:
    """Ключ выпал при смерти — вернуть в мир."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE season_keys
        SET found_by = NULL,
            found_at = NULL,
            section_id = ?,
            layer = ?,
            wing = ?
        WHERE season_id = ? AND found_by = ? AND key_number = ?
    """, (section_id, layer, wing, season_id, user_id, key_number))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0
