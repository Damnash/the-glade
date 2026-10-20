# services/push.py
#
# Push-уведомления игрокам (если оффлайн).

import logging
from datetime import datetime, timedelta

from db.connection import get_conn
from db.players import get_player


def is_online(user_id: int, minutes: int = 10) -> bool:
    """Игрок активен за последние N минут?"""
    p = get_player(user_id)
    if not p:
        return False
    last = p.get("last_seen")
    if not last:
        return False
    try:
        from core.time_utils import parse_dt, now, seconds_since
        dt = parse_dt(last)
        if not dt:
            return False
        return seconds_since(dt) < minutes * 60
    except Exception:
        return False


async def send_push(bot, user_id: int, text: str, force: bool = False):
    """Отправить push, если игрок оффлайн (или force=True)."""
    if not force and is_online(user_id, minutes=10):
        return False
    try:
        await bot.send_message(chat_id=user_id, text=text)
        return True
    except Exception as e:
        logging.warning(f"[PUSH] {user_id} failed: {e}")
        return False
