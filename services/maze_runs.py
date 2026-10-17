# services/maze_runs.py
#
# Управление вылазками в Лабиринт (v1).
#
# Одна вылазка = одна запись в maze_runs.
# Переходы МГНОВЕННЫЕ, но таймер ends_at ограничивает время в Лабиринте.
# Игрок, не вернувшийся до ends_at — погибает.

from datetime import timedelta
from collections import deque

from core.time_utils import now, parse_dt, seconds_until
from core.daycycle import is_night
from db.connection import get_conn
from db.maze_map import get_section, load_layer
from db.players import get_player, update_player_fields


# ============ Настройки ============

RUN_DURATION_SEC = 600  # 10 минут на вылазку


class MazeRunError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


# ============ Получение ============

def get_run(user_id: int) -> dict | None:
    """Активная вылазка игрока или None."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM maze_runs WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_expired_runs() -> list[dict]:
    """Все вылазки, у которых истёк таймер. Для фоновой задачи."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM maze_runs WHERE ends_at <= ?",
        (now(),),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_timer(user_id: int) -> dict:
    """
    Проверить таймер вылазки.
    Возвращает: {"has_run": bool, "expired": bool, "seconds_left": int}
    """
    run = get_run(user_id)
    if not run:
        return {"has_run": False, "expired": False, "seconds_left": 0}

    ends_at = parse_dt(run["ends_at"])
    left = seconds_until(ends_at)
    return {
        "has_run": True,
        "expired": left <= 0,
        "seconds_left": max(0, left),
        "run": run,
    }


# ============ BFS — глубина от входа ============

def _bfs_depth(layer: dict, start: str, target: str) -> int:
    """
    Кратчайшее расстояние от start до target по графу секций.
    Возвращает int (0 если start == target). Если пути нет — возвращает -1.
    """
    sections = layer["sections"]
    if start not in sections or target not in sections:
        return -1
    if start == target:
        return 0

    queue = deque([(start, 0)])
    visited = {start}

    while queue:
        node, dist = queue.popleft()
        for nxt in sections[node]["exits"]:
            if nxt == target:
                return dist + 1
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, dist + 1))

    return -1  # нет пути


def _get_current_layer(user_id: int) -> dict | None:
    """Загрузить текущий слой Лабиринта игрока."""
    from core.maze_current import get_current_season
    run = get_run(user_id)
    if not run:
        return None
    season = get_current_season()
    return load_layer(season, run["layer"])


# ============ Жизненный цикл ============

def start_run(user_id: int, layer: int, entry_section: str) -> dict:
    """
    Создать вылазку. Возвращает запись maze_runs (dict).
    Если уже есть активная — ошибка.
    """
    existing = get_run(user_id)
    if existing:
        raise MazeRunError("maze.already_in_run")

    started_at = now()
    ends_at = started_at + timedelta(seconds=RUN_DURATION_SEC)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO maze_runs
        (user_id, layer, current_section, entry_section, depth, started_at, ends_at)
        VALUES (?, ?, ?, ?, 0, ?, ?)
    """, (user_id, layer, entry_section, entry_section, started_at, ends_at))
    conn.commit()
    conn.close()

    return {
        "user_id": user_id,
        "layer": layer,
        "current_section": entry_section,
        "entry_section": entry_section,
        "depth": 0,
        "started_at": started_at,
        "ends_at": ends_at,
    }


def end_run(user_id: int) -> None:
    """Удалить вылазку (успешный выход или смерть)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM maze_runs WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def move_in_run(user_id: int, to_section: str) -> dict:
    """
    Мгновенный переход в новую секцию.
    
    Проверяет:
      - есть ли активная вылазка
      - не истёк ли таймер
      - валидность перехода (to_section — сосед current_section)
    
    Списывает ресурсы через services.survival.consume_on_move.
    Пересчитывает depth через BFS.
    Возвращает отчёт:
      {
          "ok": bool,
          "reason": str,       # если ok=False
          "current_section": str,
          "depth": int,
          "survival": dict,    # отчёт survival
          "death": bool,       # hp <= 0
      }
    """
    from services.survival import consume_on_move

    run = get_run(user_id)
    if not run:
        return {"ok": False, "reason": "no_run"}

    # Проверка таймера
    timer = check_timer(user_id)
    if timer["expired"]:
        return {"ok": False, "reason": "timer_expired"}

    # Загружаем слой
    layer = _get_current_layer(user_id)
    if not layer:
        return {"ok": False, "reason": "no_layer"}

    current = run["current_section"]
    sections = layer["sections"]

    # Проверка существования
    if to_section not in sections:
        return {"ok": False, "reason": "no_section"}

    # Проверка соседства
    if to_section not in sections[current]["exits"]:
        return {"ok": False, "reason": "not_adjacent"}

    # Списываем ресурсы
    survival_report = consume_on_move(user_id, is_night=is_night())

    # Считаем depth от to_section до entry_section
    depth = _bfs_depth(layer, to_section, run["entry_section"])
    if depth < 0:
        depth = run["depth"]  # fallback

    # Обновляем maze_runs
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE maze_runs
        SET current_section = ?, depth = ?
        WHERE user_id = ?
    """, (to_section, depth, user_id))
    conn.commit()
    conn.close()

    # Синхронизируем maze_section у игрока
    update_player_fields(user_id, {"maze_section": to_section})

    # Daily quest progress
    try:
        from services.daily_quests import add_progress
        add_progress(user_id, "visit_sections", 1)
    except Exception:
        pass

    # Story tracking (для сюжетных квестов типа "Разведка")
    try:
        from services.story import track_event
        track_event(user_id, "visit_sections")

        # Если секция — центр, отметить "reach_center"
        section_obj = layer["sections"].get(to_section)
        if section_obj and section_obj.get("type") == "center":
            track_event(user_id, "reach_center")
    except Exception as e:
        import logging
        logging.debug(f"[maze_runs] story track_event error: {e}")

    return {
        "ok": True,
        "current_section": to_section,
        "depth": depth,
        "survival": survival_report,
        "death": survival_report.get("death", False),
    }


def _gate_from_section(section_id: str) -> str:
    """Определить ворота Глэййда по ID секции (L1_N1 → north_gates)."""
    wing_to_gate = {
        "N": "north_gates",
        "S": "south_gates",
        "W": "west_gates",
        "E": "east_gates",
    }
    if not section_id:
        return "center"
    try:
        parts = section_id.split("_")
        wing = parts[1][0]
        return wing_to_gate.get(wing, "center")
    except (IndexError, ValueError):
        return "center"


def try_exit_run(user_id: int) -> dict:
    """
    Попытка выйти из Лабиринта.
    Разрешено только если current_section == entry_section.

    Возвращает:
      {"ok": True, "gate": str} — если вышли
      {"ok": False, "reason": str, "depth": int} — если нет
    """
    run = get_run(user_id)

    if not run:
        # Recovery: если maze_runs нет, но игрок "в Лабиринте" —
        # принудительно вытаскиваем его в Глэйд.
        player = get_player(user_id)
        if player and player.get("maze_layer", 0) > 0:
            gate = _gate_from_section(player.get("maze_section") or "")
            update_player_fields(user_id, {
                "location": gate,
                "maze_layer": 0,
                "maze_section": None,
            })
            return {"ok": True, "gate": gate, "recovered": True}
        return {"ok": False, "reason": "no_run"}

    current = run["current_section"]
    entry = run["entry_section"]

    if current != entry:
        return {
            "ok": False,
            "reason": "not_at_entry",
            "depth": run["depth"],
            "current_section": current,
        }

    # Определяем ворота по entry_section
    gate = _gate_from_section(entry)
    if gate == "center" and entry != "L1_C":
        return {"ok": False, "reason": "unknown_entry"}

    # Обновляем игрока
    update_player_fields(user_id, {
        "location": gate,
        "maze_layer": 0,
        "maze_section": None,
    })

    # Удаляем run
    end_run(user_id)

    # Daily quest progress
    try:
        from services.daily_quests import add_progress
        add_progress(user_id, "return_alive", 1)
    except Exception:
        pass

    return {"ok": True, "gate": gate}


def force_end_on_death(user_id: int) -> None:
    """Принудительно завершить вылазку (смерть, телепорт и т.п.)."""
    end_run(user_id)
