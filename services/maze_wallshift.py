# services/maze_wallshift.py
#
# Стены Лабиринта сдвигаются раз в неделю.
# Секции те же, меняются только связи между ними.

import logging
import random

from db.connection import get_conn
from db.maze_map import load_layer, get_section
from core.maze_current import get_current_season, get_season_day


WALLSHIFT_INTERVAL_DAYS = 7


def should_wallshift(season_id: int) -> bool:
    """Пора ли сдвигать стены (день % 7 == 0)."""
    day = get_season_day(season_id)
    return day > 0 and day % WALLSHIFT_INTERVAL_DAYS == 0


def has_wallshift_today(season_id: int, day: int) -> bool:
    """Уже был сдвиг в этот день?"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT value FROM system_state
            WHERE key = ?
        """, (f"wallshift_day_{season_id}",))
        row = cur.fetchone()
        if not row:
            return False
        return str(row[0]) == str(day)
    finally:
        conn.close()


def mark_wallshift_done(season_id: int, day: int):
    """Отметить, что сдвиг был."""
    from datetime import datetime
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO system_state (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (f"wallshift_day_{season_id}", str(day), datetime.utcnow()))
        conn.commit()
    finally:
        conn.close()


def wallshift(season_id: int, layer: int = 1) -> dict:
    """
    Сдвинуть стены: перегенерировать связи между кольцами.
    
    Логика:
    - Цепочка вперёд (кольцо k → k+1) ОСТАЁТСЯ.
    - Обратные рёбра (k → k-1) — пересоздаются случайно.
    - Рёбра через одно (k → k+2) — пересоздаются случайно.
    - Рёбра внутри одного крыла (соседние кольца) — остаются.
    - Центр — связан с последним кольцом (N30, S30, W30, E30) — остаётся.
    """
    from db.maze_map import save_layer  # для сохранения

    layer_data = load_layer(season_id, layer)
    if not layer_data:
        return {"ok": False, "reason": "no_layer"}

    sections = layer_data["sections"]
    entrances = layer_data["entrances"]
    center = layer_data["center"]

    wings = ["N", "S", "W", "E"]

    # Найдём все секции по крыльям
    by_wing = {w: [] for w in wings}
    for sid, sec in sections.items():
        if sec.get("wing") in wings:
            by_wing[sec["wing"]].append(sid)

    # 1. Оставляем цепочку вперёд + центр + соседние кольца
    new_exits = {}
    for sid, sec in sections.items():
        new_exits[sid] = []

    # Цепочка вперёд
    for w in wings:
        sorted_sections = sorted(by_wing[w], key=lambda x: sections[x]["ring"])
        for i in range(len(sorted_sections) - 1):
            a = sorted_sections[i]
            b = sorted_sections[i + 1]
            new_exits[a].append(b)
            new_exits[b].append(a)

    # Центр — связан с последними
    for w in wings:
        if by_wing[w]:
            last = sorted(by_wing[w], key=lambda x: sections[x]["ring"])[-1]
            new_exits[last].append(center)
            new_exits[center].append(last)

    # 2. Добавляем случайные рёбра (кроме цепочки)
    added = 0
    max_edges = 15

    attempts = 0
    while added < max_edges and attempts < 100:
        attempts += 1
        w1 = random.choice(wings)
        w2 = random.choice(wings)

        if not by_wing[w1] or not by_wing[w2]:
            continue

        a = random.choice(by_wing[w1])
        b = random.choice(by_wing[w2])

        if a == b:
            continue
        if b in new_exits[a] or a in new_exits[b]:
            continue

        # Только между соседними кольцами (|Δring| <= 2)
        if abs(sections[a]["ring"] - sections[b]["ring"]) > 2:
            continue

        # Ограничение на количество выходов
        if len(new_exits[a]) >= 4 or len(new_exits[b]) >= 4:
            continue

        new_exits[a].append(b)
        new_exits[b].append(a)
        added += 1

    # 3. Проверка связности (все секции достижимы до центра)
    from collections import deque
    reachable = {center}
    queue = deque([center])
    while queue:
        node = queue.popleft()
        for nxt in new_exits[node]:
            if nxt not in reachable:
                reachable.add(nxt)
                queue.append(nxt)

    if len(reachable) < len(sections):
        logging.warning(f"[WALLSHIFT] not all sections reachable: {len(reachable)}/{len(sections)}")
        return {"ok": False, "reason": "disconnected", "reachable": len(reachable), "total": len(sections)}

    # 4. Обновляем БД
    conn = get_conn()
    try:
        cur = conn.cursor()
        import json
        for sid, exits in new_exits.items():
            cur.execute("""
                UPDATE maze_map
                SET exits = ?
                WHERE season_id = ? AND layer = ? AND section_id = ?
            """, (json.dumps(exits), season_id, layer, sid))
        conn.commit()
    finally:
        conn.close()

    logging.info(f"[WALLSHIFT] season={season_id} layer={layer}: {added} new edges")

    return {
        "ok": True,
        "added_edges": added,
        "total_sections": len(sections),
        "reachable": len(reachable),
    }
