# services/radio.py

import re

from core.time_utils import now
from db.connection import get_conn
from db.players import get_player, find_by_name


class RadioError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


# ============ Частоты ============

LPD_MIN = 433.075
LPD_MAX = 434.775
LPD_STEP = 0.025

PMR_MIN = 446.00625
PMR_MAX = 446.09375
PMR_STEP = 0.0125

RADIO_CENTER_FREQ = 27.135   # CB-15, радио у костра


def parse_frequency(text: str) -> float | None:
    """
    Парсит частоту из ввода.
    Принимает: "433.175", "433,175", "446.031", "433.175 МГц"
    Возвращает: float или None.
    """
    text = text.strip().lower()
    text = re.sub(r"\s*(мгц|mhz)\s*$", "", text)
    text = text.replace(",", ".")

    try:
        freq = float(text)
    except ValueError:
        return None

    # Проверяем LPD433
    if LPD_MIN - 0.001 <= freq <= LPD_MAX + 0.001:
        step = round(freq / LPD_STEP) * LPD_STEP
        if abs(freq - step) < 0.001:
            return round(step, 3)
        return None

    # Проверяем PMR446
    if PMR_MIN - 0.001 <= freq <= PMR_MAX + 0.001:
        step = round(freq / PMR_STEP) * PMR_STEP
        if abs(freq - step) < 0.0001:
            return round(step, 5)
        return None

    return None


def format_frequency(freq: float) -> str:
    """Форматирует частоту."""
    if freq >= 446:
        return f"{freq:.5f} МГц"
    if freq >= 27 and freq < 30:
        return f"{freq:.3f} МГц"
    return f"{freq:.3f} МГц"


def get_lpd_channels(count: int = 12) -> list[float]:
    """Первые N каналов LPD433."""
    return [round(LPD_MIN + i * LPD_STEP, 3) for i in range(count)]


def get_pmr_channels() -> list[float]:
    """Все 8 каналов PMR446."""
    return [round(PMR_MIN + i * PMR_STEP, 5) for i in range(8)]


# ============ Рация игрока ============

def get_radio(user_id: int) -> dict:
    """Получить рацию игрока. Создать, если нет."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM radios WHERE user_id = ?", (user_id,))
    row = cur.fetchone()

    if not row:
        cur.execute(
            "INSERT INTO radios (user_id, frequency) VALUES (?, ?)",
            (user_id, LPD_MIN),
        )
        conn.commit()
        conn.close()
        return {"user_id": user_id, "frequency": LPD_MIN, "is_on": 1, "has_radio": 1}

    conn.close()
    return dict(row)


def set_frequency(user_id: int, freq: float):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE radios SET frequency = ? WHERE user_id = ?",
        (freq, user_id),
    )
    conn.commit()
    conn.close()


def toggle_radio(user_id: int) -> bool:
    """Вкл/выкл рацию. Возвращает новое состояние."""
    radio = get_radio(user_id)
    new_state = 0 if radio["is_on"] else 1
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE radios SET is_on = ? WHERE user_id = ?",
        (new_state, user_id),
    )
    conn.commit()
    conn.close()
    return bool(new_state)


# ============ Отправка ============

def send_on_frequency(user_id: int, text: str) -> dict:
    """Отправить сообщение на частоте рации."""
    radio = get_radio(user_id)
    if not radio["has_radio"]:
        raise RadioError("radio.no_radio")
    if not radio["is_on"]:
        raise RadioError("radio.off")

    freq = radio["frequency"]
    sender = get_player(user_id)
    sender_name = sender["display_name"] or sender["username"]

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO freq_messages (frequency, user_id, display_name, text, sent_at)
        VALUES (?, ?, ?, ?, ?)
    """, (freq, user_id, sender_name, text, now()))

    # Кто на этой частоте (не считая отправителя)
    cur.execute("""
        SELECT user_id FROM radios
        WHERE frequency = ? AND is_on = 1 AND has_radio = 1 AND user_id != ?
    """, (freq, user_id))
    listeners = [row[0] for row in cur.fetchall()]
    conn.commit()
    conn.close()

    return {
        "frequency": freq,
        "text": text,
        "sender_name": sender_name,
        "listeners": listeners,
    }


def get_freq_history(freq: float, limit: int = 20) -> list[dict]:
    """Последние сообщения на частоте."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, display_name, text, sent_at
        FROM freq_messages
        WHERE frequency = ?
        ORDER BY sent_at DESC
        LIMIT ?
    """, (freq, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


# ============ Радио в центре ============

def send_radio_center(user_id: int, text: str, encrypted_for: int | None = None) -> dict:
    """Сказать в радио у костра."""
    sender = get_player(user_id)
    if not sender:
        raise RadioError("start.need_start")

    if sender["location"] != "center":
        raise RadioError("radio.not_center")

    sender_name = sender["display_name"] or sender["username"]

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO radio_messages
        (user_id, display_name, text, encrypted_for, sent_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, sender_name, text, encrypted_for, now()))
    conn.commit()
    conn.close()

    return {
        "sender_name": sender_name,
        "text": text,
        "encrypted_for": encrypted_for,
    }


def get_radio_history(limit: int = 30) -> list[dict]:
    """История радио."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, display_name, text, encrypted_for, sent_at
        FROM radio_messages
        WHERE sent_at >= datetime('now', '-24 hours')
        ORDER BY sent_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def resolve_encrypted_target(text: str) -> tuple[int | None, str]:
    """
    Проверяет, есть ли @ник в начале текста.
    Возвращает (user_id или None, очищенный текст).
    """
    if not text.startswith("@"):
        return None, text

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None, text

    nick = parts[0][1:]  # убираем @
    clean_text = parts[1]

    target = find_by_name(nick)
    if not target:
        return None, text

    return target["user_id"], clean_text