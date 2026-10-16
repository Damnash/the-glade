# db/maze_map.py

import json

from core.maze_generator import assign_names
from db.connection import get_conn


def save_layer(season_id: int, layer_number: int, layer_data: dict):
    """Сохраняет карту слоя с именами."""
    conn = get_conn()
    cur = conn.cursor()

    # Генерируем имена
    names = assign_names(layer_data["sections"])

    for sid, spec in layer_data["sections"].items():
        cur.execute("""
            INSERT OR REPLACE INTO maze_map
            (season_id, layer, section_id, name, wing, ring, section_type, exits)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            season_id,
            layer_number,
            sid,
            names.get(sid, sid),
            spec["wing"],
            spec["ring"],
            spec["type"],
            json.dumps(spec["exits"]),
        ))

    # Мета
    cur.execute("""
        INSERT OR REPLACE INTO maze_meta
        (season_id, layer, key, value) VALUES (?, ?, 'center', ?)
    """, (season_id, layer_number, layer_data["center"]))

    for wing, sid in layer_data["entrances"].items():
        cur.execute("""
            INSERT OR REPLACE INTO maze_meta
            (season_id, layer, key, value) VALUES (?, ?, ?, ?)
        """, (season_id, layer_number, f"entrance_{wing}", sid))

    conn.commit()
    conn.close()


def load_layer(season_id: int, layer_number: int) -> dict | None:
    """Загружает карту слоя."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT section_id, name, wing, ring, section_type, exits
        FROM maze_map WHERE season_id = ? AND layer = ?
    """, (season_id, layer_number))

    rows = cur.fetchall()
    if not rows:
        conn.close()
        return None

    sections = {}
    for row in rows:
        sid, name, wing, ring, stype, exits_json = row
        sections[sid] = {
            "name": name or sid,
            "wing": wing,
            "ring": ring,
            "type": stype,
            "exits": json.loads(exits_json),
        }

    cur.execute("""
        SELECT key, value FROM maze_meta
        WHERE season_id = ? AND layer = ?
    """, (season_id, layer_number))
    meta = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()

    return {
        "sections": sections,
        "center": meta.get("center"),
        "entrances": {
            "N": meta.get("entrance_N"),
            "S": meta.get("entrance_S"),
            "W": meta.get("entrance_W"),
            "E": meta.get("entrance_E"),
        },
    }


def get_section(season_id: int, layer_number: int, section_id: str) -> dict | None:
    """Получить одну секцию."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT section_id, name, wing, ring, section_type, exits
        FROM maze_map WHERE season_id = ? AND layer = ? AND section_id = ?
    """, (season_id, layer_number, section_id))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    sid, name, wing, ring, stype, exits_json = row
    return {
        "section_id": sid,
        "name": name or sid,
        "wing": wing,
        "ring": ring,
        "type": stype,
        "exits": json.loads(exits_json),
    }