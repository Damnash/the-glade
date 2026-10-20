# services/weather.py
#
# Погода в Глэйде: меняется раз в час. Хранится в system_state.
# Влияет на описания локаций и шансы событий.

import random
import logging
from datetime import datetime

from db.connection import get_conn


# Погода: (ключ, множитель шанса Гриверов, множитель шанса фрагментов)
WEATHERS = {
    "clear":     (1.0, 1.0),
    "fog":       (1.5, 0.8),   # туман: Гриверы чаще, фрагменты реже
    "rain":      (0.9, 0.9),   # дождь
    "wind":      (1.0, 1.2),   # ветер: фрагменты чаще
    "storm":     (1.8, 0.5),   # гроза: Гриверы часто, фрагменты редко
    "calm":      (0.8, 1.3),   # затишье: безопаснее
}

# Веса выбора (какая погода чаще)
WEATHER_WEIGHTS = {
    "clear": 3,
    "fog":   2,
    "rain":  2,
    "wind":  2,
    "storm": 1,
    "calm":  2,
}


def get_current_weather() -> str:
    """Текущая погода (из system_state) или 'clear'."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM system_state WHERE key = 'weather'")
        row = cur.fetchone()
        return row[0] if row else "clear"
    finally:
        conn.close()


def set_current_weather(key: str):
    """Записать текущую погоду."""
    if key not in WEATHERS:
        key = "clear"
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO system_state (key, value, updated_at)
            VALUES ('weather', ?, ?)
        """, (key, datetime.utcnow()))
        conn.commit()
    finally:
        conn.close()


def pick_next_weather(current: str) -> str:
    """Выбрать новую погоду, не повторяя текущую."""
    keys = []
    weights = []
    for k, w in WEATHER_WEIGHTS.items():
        if k == current:
            continue
        keys.append(k)
        weights.append(w)
    return random.choices(keys, weights=weights, k=1)[0]


def get_weather_modifiers() -> tuple[float, float]:
    """(monster_chance_mult, fragment_chance_mult) для текущей погоды."""
    key = get_current_weather()
    return WEATHERS.get(key, (1.0, 1.0))


async def change_weather(bot):
    """Сменить погоду + broadcast всем игрокам (в 📋 СОБЫТИЯ)."""
    from core.i18n import t
    from services.event_log import add_event, cleanup_old_events

    current = get_current_weather()
    new = pick_next_weather(current)
    set_current_weather(new)

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
            text = t(f"weather.{new}.change", lang or "en")
            add_event(user_id, "weather_change", text, severity="important")
            cleanup_old_events(user_id)
            sent += 1
        except Exception:
            pass

    logging.info(f"[WEATHER] {current} → {new}, sent to {sent}/{len(players)}")
    return new
