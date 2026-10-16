# db/map_items.py

from db.connection import get_conn


BASE_MAP_LIMIT = 5


# ============ Создание/получение ============

def create_map(creator_id: int, name: str, is_personal: bool = False, owner_id: int | None = None) -> int:
    """Создать карту. Возвращает map_id."""
    if owner_id is None:
        owner_id = creator_id

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO map_items (name, owner_id, creator_id, is_personal)
        VALUES (?, ?, ?, ?)
    """, (name, owner_id, creator_id, 1 if is_personal else 0))
    map_id = cur.lastrowid
    conn.commit()
    conn.close()
    return map_id


def get_map(map_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM map_items WHERE id = ?", (map_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_player_maps(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM map_items
        WHERE owner_id = ?
        ORDER BY is_personal DESC, id ASC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_personal_map(user_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM map_items
        WHERE owner_id = ? AND is_personal = 1
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ============ Изменения ============

def rename_map(map_id: int, new_name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE map_items SET name = ? WHERE id = ?", (new_name, map_id))
    conn.commit()
    conn.close()


def delete_map(map_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM map_item_sections WHERE map_id = ?", (map_id,))
    cur.execute("DELETE FROM map_items WHERE id = ?", (map_id,))
    conn.commit()
    conn.close()


# ============ Лимиты ============

def count_player_maps(user_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM map_items WHERE owner_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_map_limit(user_id: int) -> int:
    """
    Лимит карт: базовый + бонусы за звания/клан.
    Пока — только базовый.
    """
    limit = BASE_MAP_LIMIT

    # TODO: бонусы за звания и клан — позже
    # from db.achievements import get_player_achievements
    # if "cartographer" in get_player_achievements(user_id): limit += 1

    return limit


def is_map_full(user_id: int) -> bool:
    return count_player_maps(user_id) >= get_map_limit(user_id)


# ============ Секции на карте ============

def get_map_sections(map_id: int, season_id: int, layer: int) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT section_id, custom_name, note, drawn_at
        FROM map_item_sections
        WHERE map_id = ? AND season_id = ? AND layer = ?
        ORDER BY section_id ASC
    """, (map_id, season_id, layer))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_section_to_map(map_id: int, season_id: int, layer: int, section_id: str,
                       custom_name: str | None = None, note: str | None = None) -> bool:
    """Добавить секцию. Возвращает True, если добавлено (не дубликат)."""
    conn = get_conn()
    cur = conn.cursor()

    # Проверяем дубликат
    cur.execute("""
        SELECT 1 FROM map_item_sections
        WHERE map_id = ? AND season_id = ? AND layer = ? AND section_id = ?
    """, (map_id, season_id, layer, section_id))
    if cur.fetchone():
        conn.close()
        return False

    cur.execute("""
        INSERT INTO map_item_sections
        (map_id, season_id, layer, section_id, custom_name, note)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (map_id, season_id, layer, section_id, custom_name, note))
    conn.commit()
    conn.close()
    return True


def remove_section_from_map(map_id: int, season_id: int, layer: int, section_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM map_item_sections
        WHERE map_id = ? AND season_id = ? AND layer = ? AND section_id = ?
    """, (map_id, season_id, layer, section_id))
    conn.commit()
    conn.close()


def count_map_sections(map_id: int, season_id: int, layer: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM map_item_sections
        WHERE map_id = ? AND season_id = ? AND layer = ?
    """, (map_id, season_id, layer))
    count = cur.fetchone()[0]
    conn.close()
    return count


# ============ Смерть и подбор ============

def drop_non_personal_maps(user_id: int, section_id: str, layer: int) -> int:
    """
    Все НЕ-личные карты игрока выпадают в секции.
    Возвращает количество выпавших карт.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE map_items
        SET owner_id = NULL,
            current_location = ?,
            current_layer = ?
        WHERE owner_id = ? AND is_personal = 0
    """, (section_id, layer, user_id))
    dropped = cur.rowcount
    conn.commit()
    conn.close()
    return dropped


def get_maps_on_ground(section_id: str, layer: int) -> list[dict]:
    """Все карты, лежащие в секции."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM map_items
        WHERE owner_id IS NULL
          AND current_location = ?
          AND current_layer = ?
    """, (section_id, layer))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def pickup_map(map_id: int, user_id: int) -> bool:
    """Подобрать конкретную карту с пола."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE map_items
        SET owner_id = ?,
            current_location = NULL,
            current_layer = NULL
        WHERE id = ? AND owner_id IS NULL
    """, (user_id, map_id))
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


# ============ Редактирование секций ============

def update_section_name(map_id: int, season_id: int, layer: int,
                        section_id: str, custom_name: str | None):
    """Обновить имя секции на карте."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE map_item_sections
        SET custom_name = ?
        WHERE map_id = ? AND season_id = ? AND layer = ? AND section_id = ?
    """, (custom_name, map_id, season_id, layer, section_id))
    conn.commit()
    conn.close()


def update_section_note(map_id: int, season_id: int, layer: int,
                        section_id: str, note: str | None):
    """Обновить заметку к секции."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE map_item_sections
        SET note = ?
        WHERE map_id = ? AND season_id = ? AND layer = ? AND section_id = ?
    """, (note, map_id, season_id, layer, section_id))
    conn.commit()
    conn.close()


def get_section_on_map(map_id: int, season_id: int, layer: int,
                       section_id: str) -> dict | None:
    """Получить секцию с карты."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT section_id, custom_name, note, drawn_at
        FROM map_item_sections
        WHERE map_id = ? AND season_id = ? AND layer = ? AND section_id = ?
    """, (map_id, season_id, layer, section_id))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None



# ============ Показ карт другим ============

from datetime import datetime, timedelta


SHARE_HOURS = 24


def create_share(map_id: int, from_id: int, to_id: int) -> int:
    """Создать показ карты другому игроку. Возвращает share_id."""
    expires = datetime.utcnow() + timedelta(hours=SHARE_HOURS)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO map_shares (map_id, from_id, to_id, expires_at)
        VALUES (?, ?, ?, ?)
    """, (map_id, from_id, to_id, expires))
    share_id = cur.lastrowid
    conn.commit()
    conn.close()
    return share_id


def get_active_shares(to_id: int) -> list[dict]:
    """Активные показы для игрока (не истёкшие)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, map_id, from_id, shared_at, expires_at, copied
        FROM map_shares
        WHERE to_id = ? AND expires_at > ?
        ORDER BY shared_at DESC
    """, (to_id, datetime.utcnow()))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_share(share_id: int) -> dict | None:
    """Один показ."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM map_shares WHERE id = ?", (share_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def mark_share_copied(share_id: int):
    """Отметить, что получатель скопировал."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE map_shares SET copied = 1 WHERE id = ?", (share_id,))
    conn.commit()
    conn.close()


def cleanup_expired_shares():
    """Удалить истёкшие показы."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM map_shares WHERE expires_at <= ?", (datetime.utcnow(),))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def delete_share(share_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM map_shares WHERE id = ?", (share_id,))
    conn.commit()
    conn.close()



# ============ Выпадение карт при смерти ============

from datetime import datetime, timedelta


DROP_LIFETIME_HOURS = 2


def drop_all_non_personal_maps(user_id: int, section_id: str, layer: int) -> int:
    """Все НЕ-личные карты игрока выпадают в секции."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE map_items
        SET owner_id = NULL,
            current_location = ?,
            current_layer = ?,
            dropped_at = ?
        WHERE owner_id = ? AND is_personal = 0
    """, (section_id, layer, datetime.utcnow(), user_id))
    dropped = cur.rowcount
    conn.commit()
    conn.close()
    return dropped


def get_maps_on_ground(section_id: str, layer: int) -> list[dict]:
    """Все активные карты на полу (не старше 2 часов)."""
    cutoff = datetime.utcnow() - timedelta(hours=DROP_LIFETIME_HOURS)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM map_items
        WHERE owner_id IS NULL
          AND current_location = ?
          AND current_layer = ?
          AND (dropped_at IS NULL OR dropped_at > ?)
    """, (section_id, layer, cutoff))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cleanup_expired_drops():
    """Удалить истёкшие карты с пола."""
    cutoff = datetime.utcnow() - timedelta(hours=DROP_LIFETIME_HOURS)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM map_items
        WHERE owner_id IS NULL
          AND dropped_at IS NOT NULL
          AND dropped_at <= ?
    """, (cutoff,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


