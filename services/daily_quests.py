# services/daily_quests.py
#
# Логика ежедневных личных квестов.
# Один квест на игрока в сутки (UTC).

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from db.connection import get_conn
from content.daily_quests import DAILY_QUESTS, pick_daily_quest, get_quest


UTC = ZoneInfo("UTC")


def _today_utc() -> str:
    return datetime.now(UTC).date().isoformat()


def _get_conn():
    return get_conn()


# ============ Чтение ============

def get_today_quest(user_id: int) -> dict | None:
    """Получить квест игрока на сегодня или None."""
    today = _today_utc()
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, quest_date, quest_key, progress, need, status,
                   started_at, completed_at
            FROM daily_quests
            WHERE user_id = ? AND quest_date = ?
        """, (user_id, today))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ============ Выдача ============

def ensure_today_quest(user_id: int) -> dict:
    """
    Гарантирует, что у игрока есть квест на сегодня.
    Если нет — создаёт. Возвращает запись.
    """
    existing = get_today_quest(user_id)
    if existing:
        return existing

    # Создать новый
    quest_key = pick_daily_quest()
    quest = get_quest(quest_key)
    if not quest:
        raise ValueError(f"Unknown quest key: {quest_key}")

    today = _today_utc()
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO daily_quests
            (user_id, quest_date, quest_key, progress, need, status, started_at)
            VALUES (?, ?, ?, 0, ?, 'active', ?)
        """, (user_id, today, quest_key, quest["need"], datetime.utcnow()))
        conn.commit()
    finally:
        conn.close()

    logging.info(f"[DQ] user={user_id} got quest={quest_key}")

    # Перечитать (на случай гонки)
    return get_today_quest(user_id)


# ============ Прогресс ============

def add_progress(user_id: int, quest_type: str, amount: int = 1) -> bool:
    """
    Добавить прогресс квестам этого типа (если квест сегодня активен).
    Возвращает True, если прогресс изменился.
    """
    existing = get_today_quest(user_id)
    if not existing:
        return False

    if existing["status"] != "active":
        return False

    quest_key = existing["quest_key"]
    quest = get_quest(quest_key)
    if not quest:
        return False

    if quest["type"] != quest_type:
        return False

    new_progress = min(existing["progress"] + amount, existing["need"])

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE daily_quests SET progress = ?
            WHERE user_id = ? AND quest_date = ?
        """, (new_progress, user_id, existing["quest_date"]))

        # Если достигли need — перевести в 'complete'
        if new_progress >= existing["need"]:
            cur.execute("""
                UPDATE daily_quests SET status = 'complete', completed_at = ?
                WHERE user_id = ? AND quest_date = ?
            """, (datetime.utcnow(), user_id, existing["quest_date"]))

        conn.commit()
    finally:
        conn.close()

    logging.debug(f"[DQ] user={user_id} {quest_type} +{amount} → {new_progress}/{existing['need']}")
    return True


# ============ Завершение ============

def try_complete(user_id: int) -> dict | None:
    """
    Завершить квест, если прогресс набран и статус 'complete'.
    Выдать награду, поставить 'rewarded'.
    Возвращает {'quest': quest, 'reward': reward} или None.
    """
    existing = get_today_quest(user_id)
    if not existing:
        return None

    if existing["status"] != "complete":
        return None

    quest_key = existing["quest_key"]
    quest = get_quest(quest_key)
    if not quest:
        return None

    reward = quest.get("reward", {})

    # Выдаём награду
    from db.players import get_player, update_player_fields
    from db.inventory import add_item

    player = get_player(user_id)
    if not player:
        return None

    # Жетоны
    tokens = reward.get("tokens", 0)
    if tokens > 0:
        update_player_fields(user_id, {
            "tokens": player.get("tokens", 0) + tokens,
        })

    # Ресурсы
    resources = reward.get("resource", {})
    if resources:
        for item_key, qty in resources.items():
            add_item(user_id, item_key, qty)

    # Статус → rewarded
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE daily_quests SET status = 'rewarded'
            WHERE user_id = ? AND quest_date = ?
        """, (user_id, existing["quest_date"]))
        conn.commit()
    finally:
        conn.close()

    logging.info(f"[DQ] user={user_id} rewarded for {quest_key}: {reward}")
    return {"quest": quest, "reward": reward}


# ============ Форматирование ============

def format_reward(reward: dict, lang: str) -> str:
    """Форматировать награду в строку."""
    from core.i18n import t
    parts = []

    tokens = reward.get("tokens", 0)
    if tokens > 0:
        parts.append(f"🪙 +{tokens}")

    resources = reward.get("resource", {})
    for item_key, qty in resources.items():
        name = t(f"item.{item_key}.name", lang)
        parts.append(f"{name} +{qty}")

    return ", ".join(parts) if parts else "—"
