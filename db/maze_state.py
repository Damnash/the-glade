# db/maze_state.py

from datetime import datetime, timedelta

from db.connection import get_conn


FRAGMENTS_PER_DAY = 2


def count_fragments_today(season_id: int) -> int:
    """Сколько фрагментов нашли сегодня на всём сервере."""
    conn = get_conn()
    cur = conn.cursor()
    today = datetime.utcnow().date().isoformat()
    cur.execute("""
        SELECT COUNT(*) FROM fragment_finds
        WHERE season_id = ? AND DATE(found_at) = ?
    """, (season_id, today))
    count = cur.fetchone()[0]
    conn.close()
    return count


def can_find_fragment(season_id: int) -> bool:
    """Можно ли найти фрагмент сегодня."""
    return count_fragments_today(season_id) < FRAGMENTS_PER_DAY


def log_fragment_find(season_id: int, user_id: int, section_id: str):
    """Записать находку фрагмента."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO fragment_finds (season_id, user_id, section_id)
        VALUES (?, ?, ?)
    """, (season_id, user_id, section_id))
    conn.commit()
    conn.close()


def is_discovered(season_id: int, layer: int, section_id: str) -> bool:
    """Открыта ли секция для всех."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM maze_discovered
        WHERE season_id = ? AND layer = ? AND section_id = ?
    """, (season_id, layer, section_id))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def mark_discovered(season_id: int, layer: int, section_id: str, user_id: int):
    """Открыть секцию для всех."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO maze_discovered
        (season_id, layer, section_id, discovered_by)
        VALUES (?, ?, ?, ?)
    """, (season_id, layer, section_id, user_id))
    conn.commit()
    conn.close()


def get_discovered_count(season_id: int, layer: int) -> int:
    """Сколько секций открыто."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM maze_discovered
        WHERE season_id = ? AND layer = ?
    """, (season_id, layer))
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_map_status(season_id: int, layer: int) -> dict:
    """
    Полный статус карты: какие секции открыты, сколько всего.
    """
    from db.maze_map import load_layer

    layer_data = load_layer(season_id, layer)
    if not layer_data:
        return {"sections": {}, "discovered": 0, "total": 0}

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT section_id FROM maze_discovered
        WHERE season_id = ? AND layer = ?
    """, (season_id, layer))
    discovered_ids = {row[0] for row in cur.fetchall()}
    conn.close()

    sections = {}
    for sid, spec in layer_data["sections"].items():
        sections[sid] = {
            "wing": spec["wing"],
            "ring": spec["ring"],
            "name": spec["name"],
            "discovered": sid in discovered_ids,
        }

    return {
        "sections": sections,
        "discovered": len(discovered_ids),
        "total": len(sections),
    }
