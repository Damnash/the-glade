# services/keys.py

import random

from core.maze_current import get_current_season, get_season_day
from db.keys import (
    KEY_DAY, KEY_DUPLICATE_DAYS,
    has_player_key, get_player_keys, key_spawned, key_exists_unfound,
    spawn_key, find_key_in_section, mark_key_found,
    get_key_by_number, drop_player_key, respawn_key,
)
from db.maze_map import load_layer


class KeyError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


FIND_CHANCE = 0.10  # 10% за осмотр


WINGS = ["N", "S", "W", "E"]


def ensure_keys_spawned(season_id: int):
    """
    Утром: спавн/переспавн ключей.
    
    - Ключ 2: кольцо 1-2
    - Ключ 3: кольцо 2-3
    - Ключ 4: кольцо 3-4
    - Ключ 5: центр
    
    Если ключ найден — не трогаем.
    Если не найден и spawned_date != today — переспавн.
    """
    from datetime import date as _date
    today = _date.today().isoformat()
    day = get_season_day(season_id)
    layer_data = load_layer(season_id, 1)
    if not layer_data:
        return

    sections = layer_data["sections"]

    # Группируем секции по крыльям и кольцам
    by_wing_ring = {}
    for sid, sec in sections.items():
        wing = sec["wing"]
        ring = sec["ring"]
        if wing == "C":
            continue
        by_wing_ring.setdefault((wing, ring), []).append(sid)

    # Ключи 2, 3, 4
    for key_num in [2, 3, 4]:
        spawn_day = KEY_DAY[key_num]
        if day < spawn_day:
            continue

        all_keys = get_key_by_number(season_id, key_num)
        found_keys = [k for k in all_keys if k["found_by"] is not None]

        # Если ключ уже найден — не трогаем
        if found_keys:
            continue

        # Уже есть не найденный? Проверим дату
        unfound = [k for k in all_keys if k["found_by"] is None]
        if unfound:
            k = unfound[0]
            if k.get("spawned_date") != today:
                # Переспавн — в новую секцию
                target_ring = {2: 1, 3: 2, 4: 3}[key_num]
                wing = random.choice(WINGS)
                candidates = by_wing_ring.get((wing, target_ring), [])
                if not candidates:
                    for (w, r), secs in by_wing_ring.items():
                        if r == target_ring:
                            candidates = secs
                            wing = w
                            break
                if candidates:
                    new_section = random.choice(candidates)
                    respawn_key(k["id"], new_section, wing, 1, today)
        else:
            # Первый спавн
            target_ring = {2: 1, 3: 2, 4: 3}[key_num]
            wing = random.choice(WINGS)
            candidates = by_wing_ring.get((wing, target_ring), [])
            if not candidates:
                for (w, r), secs in by_wing_ring.items():
                    if r == target_ring:
                        candidates = secs
                        wing = w
                        break
            if candidates:
                section_id = random.choice(candidates)
                spawn_key(season_id, key_num, section_id, wing, 1, spawned_date=today)

    # Ключ 5 — центр
    if day >= KEY_DAY[5]:
        all_keys = get_key_by_number(season_id, 5)
        found = [k for k in all_keys if k["found_by"] is not None]
        if not found:
            unfound = [k for k in all_keys if k["found_by"] is None]
            center_id = layer_data.get("center")
            if not unfound and center_id:
                spawn_key(season_id, 5, center_id, "C", 1, spawned_date=today)
            elif unfound:
                k = unfound[0]
                if k.get("spawned_date") != today and center_id:
                    respawn_key(k["id"], center_id, "C", 1, today)


def _spawn_key_random(season_id: int, key_num: int, by_wing_ring: dict, layer: int = 1):
    """Разместить ключ в случайной секции."""
    # Ключи 2, 3, 4 — на разных кольцах: 2 → ring 1, 3 → ring 2, 4 → ring 3
    target_ring = {2: 1, 3: 2, 4: 3}.get(key_num, 1)

    # Случайное крыло
    wing = random.choice(WINGS)
    candidates = by_wing_ring.get((wing, target_ring), [])
    if not candidates:
        # Fallback — любая секция нужного кольца
        for (w, r), secs in by_wing_ring.items():
            if r == target_ring:
                candidates.extend(secs)
                wing = w
                break

    if not candidates:
        return

    section_id = random.choice(candidates)
    spawn_key(season_id, key_num, section_id, wing, layer)


def _check_duplicate(season_id: int, key_num: int, day: int, by_wing_ring: dict):
    """Проверить, нужен ли дубликат."""
    dup_days = KEY_DUPLICATE_DAYS.get(key_num, 14)
    spawn_day = KEY_DAY[key_num]

    if day < spawn_day + dup_days:
        return

    # Есть ли уже дубликат?
    all_keys = get_key_by_number(season_id, key_num)
    if len(all_keys) >= 2:
        return  # уже есть 2

    # Проверяем, найден ли первый
    if not all_keys:
        return

    first = all_keys[0]
    if first["found_by"] is None:
        # Ещё не найден — дубликат не нужен? Или нужен?
        # По правилам — да, дубликат, чтобы кто-то мог найти
        pass

    # Создаём дубликат в другом крыле
    first_wing = first["wing"]
    other_wings = [w for w in WINGS if w != first_wing]
    wing = random.choice(other_wings)

    target_ring = {2: 1, 3: 2, 4: 3}.get(key_num, 1)
    candidates = by_wing_ring.get((wing, target_ring), [])
    if not candidates:
        for (w, r), secs in by_wing_ring.items():
            if r == target_ring and w != first_wing:
                candidates.extend(secs)
                wing = w
                break

    if not candidates:
        return

    section_id = random.choice(candidates)
    spawn_key(season_id, key_num, section_id, wing, layer=1, duplicate_of=first["id"])


def try_find_key(user_id: int, section_id: str, layer: int) -> int | None:
    """
    Попытка найти ключ в секции при осмотре.
    Возвращает номер ключа или None.
    """
    season = get_current_season()

    # Проверяем, есть ли в этой секции нераскрытый ключ
    key = find_key_in_section(season, layer, section_id)
    if not key:
        return None

    # 10% шанс
    if random.random() > FIND_CHANCE:
        return None

    key_num = key["key_number"]

    # Уже есть?
    if has_player_key(season, user_id, key_num):
        return None  # Не отдаём дубликат

    mark_key_found(key["id"], user_id)

    # Story tracking
    try:
        from services.story import track_event
        track_event(user_id, "find_key", {"key_number": key_num})
        track_event(user_id, "collect_keys")
    except Exception:
        pass

    return key_num


def get_player_keys_with_status(season_id: int, user_id: int) -> list[dict]:
    """
    Статус ключей игрока.
    Возвращает список: {num, has, day, found}
    """
    player_keys = set(get_player_keys(season_id, user_id))
    day = get_season_day(season_id)

    result = []
    for num in [1, 2, 3, 4, 5]:
        result.append({
            "num": num,
            "has": num in player_keys,
            "day": KEY_DAY[num],
            "available": day >= KEY_DAY[num],
        })
    return result


def drop_all_keys_on_death(user_id: int, section_id: str, layer: int) -> int:
    """Все ключи игрока выпадают."""
    season = get_current_season()

    # Получаем ключи игрока
    player_keys = get_player_keys(season, user_id)

    # Нужно знать wing секции
    layer_data = load_layer(season, layer)
    wing = "?"
    if layer_data and section_id in layer_data["sections"]:
        wing = layer_data["sections"][section_id]["wing"]

    dropped = 0
    for num in player_keys:
        if drop_player_key(season, user_id, num, section_id, layer, wing):
            dropped += 1

    return dropped


# ============ Слух о ключе (v1.1) ============

WING_NAMES = {
    "N": "loc.north_gates.name",
    "S": "loc.south_gates.name",
    "W": "loc.west_gates.name",
    "E": "loc.east_gates.name",
}


def get_today_key_rumor(season_id: int) -> dict | None:
    """
    Слух о ненайденном ключе.
    Возвращает {'key_num': int, 'wing': str, 'wing_name_key': str} или None.
    """
    from db.keys import get_key_wing, get_key_by_number

    day = get_season_day(season_id)

    for key_num in [2, 3, 4, 5]:
        spawn_day = KEY_DAY[key_num]
        if day < spawn_day:
            continue

        # Уже найден?
        keys = get_key_by_number(season_id, key_num)
        found = any(k["found_by"] is not None for k in keys)
        if found:
            continue

        wing = get_key_wing(season_id, key_num)
        if wing:
            return {
                "key_num": key_num,
                "wing": wing,
                "wing_name_key": WING_NAMES.get(wing, "loc.center.name"),
            }

    return None
