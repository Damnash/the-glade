# services/evening_fire.py
#
# Вечерний костёр: в 22:00 broadcast всем + «все NPC в центре» на 10 минут.

import logging
from datetime import datetime, timedelta

from db.connection import get_conn



async def start_evening_fire_async(bot):
    """Async: broadcast всем игрокам."""
    from core.i18n import t
    from services.event_log import add_event, cleanup_old_events

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, language FROM players WHERE intro_done = 1")
        players = cur.fetchall()
    finally:
        conn.close()

    sent = 0
    for user_id, lang in players:
        try:
            text = t("evening_fire.text", lang or "en")
            add_event(user_id, "evening_fire", text, severity="chat")
            cleanup_old_events(user_id)
            sent += 1
        except Exception:
            pass

        # Push оффлайн-игрокам
        try:
            from services.push import send_push
            push_text = t("push.evening_fire", lang or "en")
            await send_push(bot, user_id, push_text)
        except Exception:
            pass

    logging.info(f"[EVENING] fire: sent to {sent}/{len(players)}")
    return sent
