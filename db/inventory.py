# db/inventory.py

from db.connection import get_conn


def get_inventory(user_id: int) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT item_key, quantity FROM inventory WHERE user_id = ? ORDER BY item_key",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_item(user_id: int, item_key: str, quantity: int = 1):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT quantity FROM inventory WHERE user_id = ? AND item_key = ?",
            (user_id, item_key),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_key = ?",
                (quantity, user_id, item_key),
            )
        else:
            cur.execute(
                "INSERT INTO inventory (user_id, item_key, quantity) VALUES (?, ?, ?)",
                (user_id, item_key, quantity),
            )
        conn.commit()
    finally:
        conn.close()


def remove_item(user_id: int, item_key: str, quantity: int = 1) -> bool:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT quantity FROM inventory WHERE user_id = ? AND item_key = ?",
            (user_id, item_key),
        )
        row = cur.fetchone()
        if not row or row["quantity"] < quantity:
            return False

        new_qty = row["quantity"] - quantity
        if new_qty == 0:
            cur.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_key = ?",
                (user_id, item_key),
            )
        else:
            cur.execute(
                "UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_key = ?",
                (new_qty, user_id, item_key),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def has_item(user_id: int, item_key: str, quantity: int = 1) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_key = ?",
        (user_id, item_key),
    )
    row = cur.fetchone()
    conn.close()
    return bool(row and row["quantity"] >= quantity)