# services/buffs.py
#
# Баффы / дебаффы: проклятие, благословение.
# Влияют на шансы Гриверов/фрагментов, HP при переходе, воду при питье.

import logging
from datetime import datetime, timedelta

from db.connection import get_conn
from core.time_utils import now, parse_dt


# Баффы: (ключ, длительность в часах, тип)
BUFFS = {
    "cursed": {
        "duration_hours": 2,
        "modifiers": {
            "monster_mult": 1.10,     # +10% Гриверов
            "fragment_mult": 0.90,    # −10% фрагментов
            "flee_mult": 0.90,        # −10% бега
            "hp_per_move": -2,        # −2 HP при переходе
        },
    },
    "blessed": {
        "duration_hours": 2,
        "modifiers": {
            "monster_mult": 0.90,     # −10% Гриверов
            "fragment_mult": 1.10,    # +10% фрагментов
            "flee_mult": 1.10,        # +10% бега
            "water_bonus": 1,         # +1 вода при питье
        },
    },
}


def add_buff(user_id: int, buff_key: str) -> bool:
    """Добавить бафф игроку. Возвращает True, если новый."""
    spec = BUFFS.get(buff_key)
    if not spec:
        return False

    # Уже есть активный?
    active = get_active_buffs(user_id)
    if any(b["buff_key"] == buff_key for b in active):
        return False

    expires = now() + timedelta(hours=spec["duration_hours"])
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO player_buffs (user_id, buff_key, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, buff_key, expires))
        conn.commit()
    finally:
        conn.close()

    # В журнал (important)
    try:
        from core.i18n import t
        from db.players import get_player
        from services.event_log import add_event, cleanup_old_events
        p = get_player(user_id)
        if p:
            lang = p["language"]
            add_event(user_id, "buff_applied",
                      t(f"buff.{buff_key}.applied", lang, hours=spec["duration_hours"]),
                      severity="important")
            cleanup_old_events(user_id)
    except Exception as e:
        logging.warning(f"[BUFF] log failed: {e}")

    return True


def get_active_buffs(user_id: int) -> list[dict]:
    """Активные баффы (не истёкшие)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT buff_key, applied_at, expires_at FROM player_buffs
            WHERE user_id = ? AND expires_at > ?
            ORDER BY applied_at DESC
        """, (user_id, now()))
        rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_buff_modifiers(user_id: int) -> dict:
    """Суммарные модификаторы от всех активных баффов."""
    active = get_active_buffs(user_id)
    result = {
        "monster_mult": 1.0,
        "fragment_mult": 1.0,
        "flee_mult": 1.0,
        "hp_per_move": 0,
        "water_bonus": 0,
    }
    for b in active:
        spec = BUFFS.get(b["buff_key"])
        if not spec:
            continue
        for k, v in spec["modifiers"].items():
            if k in ("monster_mult", "fragment_mult", "flee_mult"):
                result[k] *= v
            else:
                result[k] += v
    return result


def clear_expired_buffs(user_id: int | None = None):
    """Удалить истёкшие баффы (для одного или всех)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute("DELETE FROM player_buffs WHERE user_id = ? AND expires_at <= ?", (user_id, now()))
        else:
            cur.execute("DELETE FROM player_buffs WHERE expires_at <= ?", (now(),))
        conn.commit()
    finally:
        conn.close()


def format_buffs_for_display(user_id: int, lang: str) -> str:
    """Строка активных баффов для отображения."""
    from core.i18n import t
    active = get_active_buffs(user_id)
    if not active:
        return ""
    parts = []
    for b in active:
        key = b["buff_key"]
        expires = parse_dt(b["expires_at"])
        if expires:
            left = max(0, int((expires - now()).total_seconds() // 60))
            parts.append(t(f"buff.{key}.line", lang, time=f"{left}м"))
    return " · ".join(parts)
