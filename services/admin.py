# services/admin.py

from datetime import datetime, timedelta

from db.connection import get_conn
from db.players import get_player, find_by_name, update_player_fields
from db.inventory import add_item, get_inventory


def get_all_players(limit: int = 100) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM players ORDER BY last_seen DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_online_players(hours: int = 24) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM players WHERE last_seen >= ? ORDER BY last_seen DESC",
        (cutoff,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_players_in_location(location: str) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM players WHERE location = ?",
        (location,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_server_stats() -> dict:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM players")
    total = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM players WHERE last_seen >= ?",
        (datetime.utcnow() - timedelta(days=7),),
    )
    active_7d = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM players WHERE last_seen >= ?",
        (datetime.utcnow() - timedelta(hours=24),),
    )
    online_24h = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM players WHERE status = 'sleeping'")
    sleeping = cur.fetchone()[0]

    conn.close()
    return {
        "total": total,
        "active_7d": active_7d,
        "online_24h": online_24h,
        "sleeping": sleeping,
    }


def admin_give_item(user_id: int, item_key: str, quantity: int = 1):
    add_item(user_id, item_key, quantity)


def admin_set_field(user_id: int, field: str, value):
    ALLOWED = {"hp", "energy", "food", "water", "tokens", "location", "status"}
    if field not in ALLOWED:
        raise ValueError(f"Field '{field}' not allowed")
    update_player_fields(user_id, {field: value})