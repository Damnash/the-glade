# services/diary.py
#
# Автодневник: система пишет важные события в player_diary.
# Тексты — в локалях (diary.auto.*).

from core.time_utils import now
from db.connection import get_conn


def add_diary_entry(user_id: int, text: str):
    """Добавить запись в дневник (без форматирования)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO player_diary (user_id, text, created_at) VALUES (?, ?, ?)",
            (user_id, text, now()),
        )
        conn.commit()
    finally:
        conn.close()


def add_diary_auto(user_id: int, event: str, **kwargs):
    """Автозапись в дневник с локализацией. event — ключ (e.g. 'enter_maze')."""
    from core.i18n import t
    from db.players import get_player

    player = get_player(user_id)
    if not player:
        return
    lang = player["language"]
    key = f"diary.auto.{event}"
    text = t(key, lang, **kwargs)
    if not text or text == key:
        return  # ключа нет — пропускаем
    # Префикс с датой
    date_prefix = t("diary.auto.date_prefix", lang, date=now().strftime("%Y-%m-%d %H:%M"))
    add_diary_entry(user_id, f"{date_prefix} {text}")

def get_player_autodiary_text(user_id: int) -> str:
    """Собрать все автозаписи (начинаются с '[') в один текст."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT text FROM player_diary
            WHERE user_id = ? AND text LIKE '[%]%'
            ORDER BY id ASC
        """, (user_id,))
        rows = cur.fetchall()
    finally:
        conn.close()
    return "\n".join(r[0] for r in rows)

def get_dropped_diaries(section_id: str, layer: int) -> list[dict]:
    """Дневники, выпавшие в секции и ещё не найденные."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, original_user_id, display_name, text, dropped_at
            FROM dropped_diaries
            WHERE section_id = ? AND layer = ? AND found_by IS NULL
            ORDER BY dropped_at DESC
        """, (section_id, layer))
        rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def mark_diary_found(diary_id: int, user_id: int):
    """Отметить, что игрок прочитал дневник."""
    from core.time_utils import now
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE dropped_diaries SET found_by = ?, found_at = ?
            WHERE id = ?
        """, (user_id, now(), diary_id))
        conn.commit()
    finally:
        conn.close()

