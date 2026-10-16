# services/whisper.py

from core.time_utils import now
from db.connection import get_conn
from db.players import get_player, find_by_name


class WhisperError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


def send_whisper(from_id: int, to_nick: str, text: str) -> dict:
    """
    Отправить шёпот игроку.
    Работает ТОЛЬКО если оба в одной локации.
    """
    sender = get_player(from_id)
    if not sender:
        raise WhisperError("start.need_start")

    target = find_by_name(to_nick)
    if not target:
        raise WhisperError("whisper.not_found")

    if target["user_id"] == from_id:
        raise WhisperError("whisper.self")

    # Проверка локации
    if sender["location"] != target["location"]:
        raise WhisperError("whisper.too_far")

    if sender["maze_layer"] != target.get("maze_layer", 0):
        raise WhisperError("whisper.too_far")

    # Сохранить в БД
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO whispers (from_id, to_id, text, sent_at)
        VALUES (?, ?, ?, ?)
    """, (from_id, target["user_id"], text, now()))
    conn.commit()
    conn.close()

    return {
        "to_id": target["user_id"],
        "to_name": target["display_name"] or target["username"],
        "text": text,
    }


def get_unread_whispers(user_id: int) -> list[dict]:
    """Получить непрочитанные шёпоты."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, from_id, text, sent_at FROM whispers
        WHERE to_id = ? AND read_at IS NULL
        ORDER BY sent_at ASC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_whispers_read(user_id: int):
    """Пометить все шёпоты как прочитанные."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE whispers SET read_at = ?
        WHERE to_id = ? AND read_at IS NULL
    """, (now(), user_id))
    conn.commit()
    conn.close()