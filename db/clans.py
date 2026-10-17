# db/clans.py

from datetime import datetime, timedelta

from db.connection import get_conn


INVITE_TTL_HOURS = 24


# ============ Кланы ============

def create_clan(leader_id: int, name: str, motto: str = "") -> int:
    """Создать клан. Возвращает clan_id."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO clans (name, leader_id, motto)
        VALUES (?, ?, ?)
    """, (name, leader_id, motto))
    clan_id = cur.lastrowid

    # Добавляем лидера
    cur.execute("""
        INSERT INTO clan_members (clan_id, user_id, role)
        VALUES (?, ?, 'leader')
    """, (clan_id, leader_id))

    conn.commit()
    conn.close()
    return clan_id


def get_clan(clan_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM clans WHERE clan_id = ?", (clan_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_clan_by_name(name: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM clans WHERE LOWER(name) = LOWER(?)", (name,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_player_clan(user_id: int) -> dict | None:
    """Клан игрока."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.* FROM clans c
        JOIN clan_members m ON m.clan_id = c.clan_id
        WHERE m.user_id = ?
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_player_role(user_id: int) -> str | None:
    """Роль игрока в клане."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT role FROM clan_members WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_clan_members(clan_id: int) -> list[dict]:
    """Все члены клана."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.user_id, m.role, m.joined_at,
               p.display_name, p.username
        FROM clan_members m
        LEFT JOIN players p ON p.user_id = m.user_id
        WHERE m.clan_id = ?
        ORDER BY
            CASE m.role
                WHEN 'leader' THEN 1
                WHEN 'advisor' THEN 2
                WHEN 'treasurer' THEN 3
                WHEN 'warrior' THEN 4
                WHEN 'scout' THEN 5
                ELSE 6
            END,
            m.joined_at
    """, (clan_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_clan_members(clan_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM clan_members WHERE clan_id = ?", (clan_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count


def update_clan_role(clan_id: int, user_id: int, role: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE clan_members SET role = ?
        WHERE clan_id = ? AND user_id = ?
    """, (role, clan_id, user_id))
    conn.commit()
    conn.close()


def remove_from_clan(user_id: int):
    """Убрать игрока из клана."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM clan_members WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def set_clan_motto(clan_id: int, motto: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE clans SET motto = ? WHERE clan_id = ?", (motto, clan_id))
    conn.commit()
    conn.close()


def set_clan_treasury(clan_id: int, amount: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE clans SET treasury = ? WHERE clan_id = ?", (amount, clan_id))
    conn.commit()
    conn.close()


def disband_clan(clan_id: int):
    """Распустить клан."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM clan_members WHERE clan_id = ?", (clan_id,))
    cur.execute("DELETE FROM clan_messages WHERE clan_id = ?", (clan_id,))
    cur.execute("DELETE FROM clan_invites WHERE clan_id = ?", (clan_id,))
    cur.execute("DELETE FROM clan_map_sections WHERE clan_id = ?", (clan_id,))
    cur.execute("DELETE FROM clan_storage WHERE clan_id = ?", (clan_id,))
    cur.execute("DELETE FROM clans WHERE clan_id = ?", (clan_id,))
    conn.commit()
    conn.close()


# ============ Приглашения ============

def create_invite(clan_id: int, from_id: int, to_id: int) -> int:
    expires = datetime.utcnow() + timedelta(hours=INVITE_TTL_HOURS)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO clan_invites (clan_id, from_id, to_id, expires_at)
        VALUES (?, ?, ?, ?)
    """, (clan_id, from_id, to_id, expires))
    invite_id = cur.lastrowid
    conn.commit()
    conn.close()
    return invite_id


def get_pending_invites(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.*, c.name as clan_name
        FROM clan_invites i
        JOIN clans c ON c.clan_id = i.clan_id
        WHERE i.to_id = ? AND i.expires_at > ?
        ORDER BY i.created_at DESC
    """, (user_id, datetime.utcnow()))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_invite(invite_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM clan_invites WHERE id = ?", (invite_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_invite(invite_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM clan_invites WHERE id = ?", (invite_id,))
    conn.commit()
    conn.close()


def cleanup_expired_invites():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM clan_invites WHERE expires_at <= ?", (datetime.utcnow(),))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


# ============ Чат клана ============

def add_clan_message(clan_id: int, user_id: int, display_name: str, text: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO clan_messages (clan_id, user_id, display_name, text)
        VALUES (?, ?, ?, ?)
    """, (clan_id, user_id, display_name, text))
    conn.commit()
    conn.close()


def get_clan_messages(clan_id: int, limit: int = 30) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, display_name, text, sent_at
        FROM clan_messages
        WHERE clan_id = ?
        ORDER BY sent_at DESC
        LIMIT ?
    """, (clan_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


# ============ Клановая карта ============

def add_section_to_clan_map(clan_id: int, season_id: int, layer: int,
                             section_id: str, contributed_by: int,
                             custom_name: str = None, note: str = None) -> bool:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1 FROM clan_map_sections
        WHERE clan_id = ? AND season_id = ? AND layer = ? AND section_id = ?
    """, (clan_id, season_id, layer, section_id))
    if cur.fetchone():
        conn.close()
        return False

    cur.execute("""
        INSERT INTO clan_map_sections
        (clan_id, season_id, layer, section_id, contributed_by, custom_name, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (clan_id, season_id, layer, section_id, contributed_by, custom_name, note))
    conn.commit()
    conn.close()
    return True


def get_clan_map_sections(clan_id: int, season_id: int, layer: int) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM clan_map_sections
        WHERE clan_id = ? AND season_id = ? AND layer = ?
        ORDER BY section_id
    """, (clan_id, season_id, layer))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_clan_map_sections(clan_id: int, season_id: int, layer: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM clan_map_sections
        WHERE clan_id = ? AND season_id = ? AND layer = ?
    """, (clan_id, season_id, layer))
    count = cur.fetchone()[0]
    conn.close()
    return count


# ============ Общий склад клана (v1.1) ============

def get_storage(clan_id: int) -> list[dict]:
    """Все предметы на складе клана."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT item_key, quantity FROM clan_storage
        WHERE clan_id = ? AND quantity > 0
        ORDER BY item_key
    """, (clan_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_storage_item(clan_id: int, item_key: str) -> int:
    """Количество конкретного предмета на складе."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT quantity FROM clan_storage
        WHERE clan_id = ? AND item_key = ?
    """, (clan_id, item_key))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def add_to_storage(clan_id: int, item_key: str, quantity: int = 1) -> int:
    """Добавить на склад. Возвращает новое количество."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO clan_storage (clan_id, item_key, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(clan_id, item_key) DO UPDATE SET
            quantity = quantity + excluded.quantity
    """, (clan_id, item_key, quantity))
    conn.commit()

    cur.execute("""
        SELECT quantity FROM clan_storage
        WHERE clan_id = ? AND item_key = ?
    """, (clan_id, item_key))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def remove_from_storage(clan_id: int, item_key: str, quantity: int = 1) -> bool:
    """Убрать со склада. Возвращает True, если удалось."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT quantity FROM clan_storage
        WHERE clan_id = ? AND item_key = ?
    """, (clan_id, item_key))
    row = cur.fetchone()
    if not row or row[0] < quantity:
        conn.close()
        return False

    new_qty = row[0] - quantity
    if new_qty == 0:
        cur.execute("""
            DELETE FROM clan_storage
            WHERE clan_id = ? AND item_key = ?
        """, (clan_id, item_key))
    else:
        cur.execute("""
            UPDATE clan_storage SET quantity = ?
            WHERE clan_id = ? AND item_key = ?
        """, (new_qty, clan_id, item_key))
    conn.commit()
    conn.close()
    return True


def get_storage_total(clan_id: int) -> int:
    """Сумма всех предметов на складе."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(quantity), 0) FROM clan_storage
        WHERE clan_id = ?
    """, (clan_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def cleanup_clan_storage(clan_id: int):
    """Очистить склад при роспуске клана."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM clan_storage WHERE clan_id = ?", (clan_id,))
    conn.commit()
    conn.close()


# ============ Апгрейды Глэййда (v1.1) ============

def get_upgrade_level(clan_id: int, upgrade_key: str) -> int:
    """Уровень апгрейда (0 если нет)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT level FROM clan_upgrades
        WHERE clan_id = ? AND upgrade_key = ?
    """, (clan_id, upgrade_key))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def set_upgrade_level(clan_id: int, upgrade_key: str, level: int):
    """Установить уровень апгрейда."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO clan_upgrades (clan_id, upgrade_key, level)
        VALUES (?, ?, ?)
        ON CONFLICT(clan_id, upgrade_key) DO UPDATE SET level = excluded.level
    """, (clan_id, upgrade_key, level))
    conn.commit()
    conn.close()


def get_all_upgrades(clan_id: int) -> dict[str, int]:
    """Все апгрейды клана: {upgrade_key: level}."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT upgrade_key, level FROM clan_upgrades
        WHERE clan_id = ?
    """, (clan_id,))
    rows = cur.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def cleanup_clan_upgrades(clan_id: int):
    """Очистить апгрейды при роспуске клана."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM clan_upgrades WHERE clan_id = ?", (clan_id,))
    conn.commit()
    conn.close()
