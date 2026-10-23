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


def _try_acquire_state(key: str, value: str) -> bool:
    """Атомарно: если key != value — записать value и вернуть True. Иначе False.

    Защита от гонки между несколькими инстансами бота и от повторного
    broadcast, если _broadcast упал после успешной записи.
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO system_state (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            WHERE system_state.value != excluded.value
        """, (key, value, datetime.utcnow()))
        conn.commit()
        return cur.rowcount > 0
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
                if _try_acquire_state("last_morning_notification", today):
                    logging.info("[DAYCYCLE] morning: gates open")
                    try:
                        await _broadcast(bot, "daycycle.morning", with_advice=True)
                    except Exception as e:
                        logging.error(f"[DAYCYCLE] morning broadcast failed: {e}")

            # ============ 22:00 — ВЕЧЕР ============
            # Воскресенье, 20:00 — поминание павших
            if hour == 20 and datetime.now(UTC).weekday() == 6:  # 6 = воскресенье
                if _try_acquire_state("last_memorial_date", today):
                    logging.info("[DAYCYCLE] Sunday memorial")
                    try:
                        from services.weekly_memorial import broadcast_memorial
                        await broadcast_memorial(bot)
                    except Exception as e:
                        logging.error(f"[DAYCYCLE] memorial error: {e}")

            if hour == 22:
                if _try_acquire_state("last_evening_notification", today):
                    logging.info("[DAYCYCLE] evening: gates closed")
                    try:
                        await _broadcast(bot, "daycycle.evening")
                    except Exception as e:
                        logging.error(f"[DAYCYCLE] evening broadcast failed: {e}")

                    # Вечерний костёр — всем игрокам
                    try:
                        from services.evening_fire import start_evening_fire_async
                        await start_evening_fire_async(bot)
                    except Exception as e:
                        logging.error(f"[DAYCYCLE] evening fire error: {e}")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"daycycle_events error: {e}")


async def _broadcast(bot, text_key: str, with_advice: bool = False):
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

    # Совет дня + слух о ключе (если нужен)
    advice_key = None
    rumor = None
    if with_advice:
        try:
            from services.daily_advice import get_today_advice_key
            advice_key = get_today_advice_key()
        except Exception as e:
            logging.error(f"[DAYCYCLE] advice error: {e}")

        try:
            from services.keys import ensure_keys_spawned, get_today_key_rumor
            from services.maze_wallshift import should_wallshift, has_wallshift_today, wallshift, mark_wallshift_done
            from core.maze_current import get_current_season, get_season_day

            season = get_current_season()
            day = get_season_day(season)

            # Wallshift раз в 7 дней
            if should_wallshift(season) and not has_wallshift_today(season, day):
                result = wallshift(season, 1)
                logging.info(f"[DAYCYCLE] wallshift: {result}")
                mark_wallshift_done(season, day)

                # Уведомление игрокам
                try:
                    from db.players import get_conn as _pc
                    from core.i18n import t as _t

                    conn = _pc()
                    cur = conn.cursor()
                    cur.execute("SELECT user_id, language FROM players WHERE intro_done = 1")
                    ws_players = cur.fetchall()
                    conn.close()

                    ws_bot = bot
                    for uid, ulang in ws_players:
                        try:
                            text = _t("wallshift.notification", ulang or "en")
                            await ws_bot.send_message(chat_id=uid, text=text)
                        except Exception:
                            pass
                except Exception as e:
                    logging.error(f"[DAYCYCLE] wallshift notify: {e}")

            ensure_keys_spawned(season)
            rumor = get_today_key_rumor(season)
        except Exception as e:
            logging.error(f"[DAYCYCLE] rumor error: {e}")

    sent = 0
    for user_id, lang in players:
        try:
            text = t(text_key, lang or "en")
            if advice_key:
                advice_text = t(advice_key, lang or "en")
                advice_title = t("advice.title", lang or "en")
                text = text + "\n\n" + advice_title + "\n" + advice_text

            if rumor:
                rumor_title = t("keys.rumor_title", lang or "en")
                wing = t(rumor["wing_name_key"], lang or "en")
                rumor_body = t("keys.rumor_body", lang or "en", num=rumor["key_num"], wing=wing)
                rumor_hint = t("keys.rumor_hint", lang or "en")
                text = text + "\n\n" + rumor_title + "\n" + rumor_body + "\n<i>" + rumor_hint + "</i>"

            await bot.send_message(chat_id=user_id, text=text)
            sent += 1
        except Exception as e:
            logging.debug(f"[DAYCYCLE] send to {user_id} failed: {e}")

    logging.info(f"[DAYCYCLE] broadcast '{text_key}': {sent}/{len(players)} (advice={advice_key}, rumor={rumor})")
