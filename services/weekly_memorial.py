# services/weekly_memorial.py
#
# Поминание павших: раз в неделю (воскресенье, 20:00).
# Broadcast всем игрокам со списком погибших за неделю.

import logging
from datetime import datetime, timedelta

from db.connection import get_conn


def get_weekly_deaths() -> list[dict]:
    """Кто умер за последние 7 дней."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, display_name, message, created_at
            FROM memorial
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (cutoff,))
        rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def record_death(user_id: int, display_name: str, message: str):
    """Записать смерть игрока (для поминания)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO memorial (user_id, display_name, message)
            VALUES (?, ?, ?)
        """, (user_id, display_name, message))
        conn.commit()
    finally:
        conn.close()


async def broadcast_memorial(bot):
    """Раз в неделю: поминание павших."""
    from core.i18n import t
    from services.event_log import add_event, cleanup_old_events

    deaths = get_weekly_deaths()

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
                if deaths:
                    names = [d["display_name"] for d in deaths[:20]]
                    names_str = "\\n".join(f"  • {n}" for n in names)
                    text = t("memorial.text", lang or "en", n=len(deaths), names=names_str)
                else:
                    text = t("memorial.text_empty", lang or "en")
                add_event(user_id, "memorial", text, severity="chat")
                cleanup_old_events(user_id)
                return 1
            except Exception as e:
                logging.warning(f"[MEMORIAL] send to {user_id} failed: {e}")
                return 0

    results = await asyncio.gather(*[_one(uid, lang) for uid, lang in players])
    sent = sum(results)

    logging.info(f"[MEMORIAL] sent to {sent}/{len(players)}")
    return sent
