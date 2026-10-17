# services/daycycle_events.py
#
# Уведомления о смене фазы дня: утро (06:00) и вечер (22:00).
# Работает как фоновая задача (asyncio).

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from db.connection import get_conn


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


def _today_utc() -> str:
    return datetime.now(UTC).date().isoformat()


def _current_hour_utc() -> int:
    return datetime.now(UTC).hour


async def daycycle_events_task(bot):
    """
    Раз в минуту проверяет время и отправляет уведомления.
    - 06:00 UTC — «ворота открыты»
    - 22:00 UTC — «ворота закрыты»
    """
    import asyncio
    from db.players import get_conn as _pc
    from core.i18n import t

    # Дать боту время запуститься
    await asyncio.sleep(5)

    while True:
        try:
            await asyncio.sleep(60)

            hour = _current_hour_utc()
            today = _today_utc()

            # ============ 06:00 — УТРО ============
            if hour == 6:
                last = _get_state("last_morning_notification")
                if last != today:
                    logging.info("[DAYCYCLE] morning: gates open")
                    await _broadcast(bot, "daycycle.morning")
                    _set_state("last_morning_notification", today)

            # ============ 22:00 — ВЕЧЕР ============
            if hour == 22:
                last = _get_state("last_evening_notification")
                if last != today:
                    logging.info("[DAYCYCLE] evening: gates closed")
                    await _broadcast(bot, "daycycle.evening")
                    _set_state("last_evening_notification", today)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"daycycle_events error: {e}")


async def _broadcast(bot, text_key: str):
    """Отправить сообщение всем активным игрокам."""
    from core.i18n import t
    from db.connection import get_conn

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, language FROM players
            WHERE intro_done = 1
        """)
        players = cur.fetchall()
    finally:
        conn.close()

    sent = 0
    for user_id, lang in players:
        try:
            text = t(text_key, lang or "en")
            await bot.send_message(chat_id=user_id, text=text)
            sent += 1
        except Exception as e:
            logging.debug(f"[DAYCYCLE] send to {user_id} failed: {e}")

    logging.info(f"[DAYCYCLE] broadcast '{text_key}': {sent}/{len(players)}")
