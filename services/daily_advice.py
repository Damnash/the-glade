# services/daily_advice.py
#
# Совет дня: раз в сутки выбирается один совет, показывается всем игрокам.
# Хранится в system_state (last_advice_date + last_advice_key).

import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from db.connection import get_conn
from content.daily_advice import get_static_advice, get_context_advice


UTC = ZoneInfo("UTC")


def _get_state(key: str) -> str | None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM system_state WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _set_state(key: str, value: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO system_state (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, datetime.utcnow()))
        conn.commit()
    finally:
        conn.close()


def get_today_advice_key() -> str:
    """
    Возвращает ключ совета дня. Если сегодня ещё не выбирался — выбирает.
    """
    from core.maze_current import get_current_season, get_season_day

    today = datetime.now(UTC).date().isoformat()
    last_date = _get_state("last_advice_date")
    last_key = _get_state("last_advice_key")

    if last_date == today and last_key:
        return last_key

    # Новый день — выбираем
    season = get_current_season()
    day = get_season_day(season)

    # Контекстный совет?
    context = {
        "day": day,
        "keys_found": _count_keys_found_today(season),
        "active_runs": _count_active_runs(),
    }
    context_key = get_context_advice(context)

    if context_key and random.random() < 0.3:
        chosen = context_key
    else:
        chosen = random.choice(get_static_advice())

    _set_state("last_advice_date", today)
    _set_state("last_advice_key", chosen)

    logging.info(f"[ADVICE] new advice for {today}: {chosen}")
    return chosen


def _count_keys_found_today(season_id: int) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        today = datetime.now(UTC).date().isoformat()
        cur.execute("""
            SELECT COUNT(*) FROM season_keys
            WHERE season_id = ? AND DATE(found_at) = ?
        """, (season_id, today))
        row = cur.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


def _count_active_runs() -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM maze_runs")
        row = cur.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()
