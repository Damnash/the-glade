# services/world_events.py
#
# Фоновые события мира: раз в час выбирается одно и пишется всем игрокам
# (severity='important') — игрок увидит в 📋 СОБЫТИЯ при следующем заходе.

import random
from datetime import datetime

from db.connection import get_conn
from content.world_events import WORLD_EVENTS


def _get_last_event_key() -> str | None:
    """Какое событие было последним (чтобы не повторялось)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM system_state WHERE key = 'last_world_event'")
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _set_last_event_key(key: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO system_state (key, value, updated_at)
            VALUES ('last_world_event', ?, ?)
        """, (key, datetime.utcnow()))
        conn.commit()
    finally:
        conn.close()


def pick_event() -> str:
    """Выбрать событие, не повторяя последнее."""
    last = _get_last_event_key()
    choices = [e for e in WORLD_EVENTS if e != last] or WORLD_EVENTS
    return random.choice(choices)


async def broadcast_world_event(bot, event_key: str):
    """Разослать событие всем игрокам (intro_done=1), записать в player_log."""
    from core.i18n import t
    from services.event_log import add_event, cleanup_old_events

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, language FROM players WHERE intro_done = 1")
        players = cur.fetchall()
    finally:
        conn.close()

    import asyncio
    sem = asyncio.Semaphore(20)

    async def _one(user_id, lang):
        async with sem:
            try:
                text = t(f"world_events.{event_key}", lang or "en")
                add_event(user_id, "world_event", text, severity="chat")
                cleanup_old_events(user_id)
                return 1
            except Exception:
                return 0

    results = await asyncio.gather(*[_one(uid, lang) for uid, lang in players])
    sent = sum(results)

    _set_last_event_key(event_key)
    return sent
