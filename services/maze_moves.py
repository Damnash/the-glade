# services/maze_moves.py

import random
from datetime import datetime, timedelta

from core.time_utils import now, parse_dt, seconds_until
from db.connection import get_conn
from content.maze_transitions import get_transition_text


MOVE_DURATION_SEC = 120  # 2 минуты


def start_move(user_id: int, from_section: str, to_section: str, layer: int) -> dict:
    """Начать переход."""
    ends_at = now() + timedelta(seconds=MOVE_DURATION_SEC)

    # Случайный индекс перехода
    transition_idx = random.randint(0, 19)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO maze_moves
        (user_id, from_section, to_section, layer, started_at, ends_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, from_section, to_section, layer, now(), ends_at))
    conn.commit()
    conn.close()

    return {
        "from": from_section,
        "to": to_section,
        "ends_at": ends_at,
        "transition_idx": transition_idx,
        "duration": MOVE_DURATION_SEC,
    }


def get_active_move(user_id: int) -> dict | None:
    """Активный переход."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM maze_moves WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def complete_move(user_id: int) -> dict | None:
    """Завершить переход. Возвращает to_section или None."""
    move = get_active_move(user_id)
    if not move:
        return None

    ends_at = parse_dt(move["ends_at"])
    if not ends_at or now() < ends_at:
        return None  # ещё не время

    # Удаляем и возвращаем
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM maze_moves WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return move


def cancel_move(user_id: int):
    """Отменить переход (если умер)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM maze_moves WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
