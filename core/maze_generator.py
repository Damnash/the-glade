# core/maze_generator.py

import random


# ============ Параметры генерации (default) ============

WING_SIZE = 30           # секций в крыле (large)
WING_COUNT = 4           # крыльев в слое
CENTER_SIZE = 2          # секций в центре (large)
CYCLES_RATIO = 0.20      # 20% связей — циклы
MIN_DEAD_ENDS = 8        # минимум тупиков
MAX_EXITS_PER_SECTION = 4


# ============ Основная функция ============

def generate_layer(layer_number: int, seed: int | None = None,
                    wing_size: int | None = None,
                    center_size: int | None = None) -> dict:
    """
    Генерирует карту одного слоя Лабиринта.
    Параметры wing_size/center_size переопределяют глобальные.
    """
    if seed is not None:
        random.seed(seed)

    wing_size = wing_size or WING_SIZE
    center_size = center_size or CENTER_SIZE

    sections = {}
    prefix = f"L{layer_number}_"

    # 1. Секции крыльев
    for wing in ["N", "S", "W", "E"]:
        for ring in range(1, wing_size + 1):
            sid = f"{prefix}{wing}{ring}"
            sections[sid] = {
                "wing": wing,
                "ring": ring,
                "type": "corridor",
                "exits": [],
            }

    # 2. Центр
    center_id = f"{prefix}C"
    sections[center_id] = {
        "wing": "C",
        "ring": 0,
        "type": "center",
        "exits": [],
    }

    # 3. Граф внутри каждого крыла
    for wing in ["N", "S", "W", "E"]:
        wing_sections = [f"{prefix}{wing}{r}" for r in range(1, wing_size + 1)]
        _generate_wing_graph(sections, wing_sections, wing, wing_size)

    # 4. Связать крылья с центром
    for wing in ["N", "S", "W", "E"]:
        wing_end = f"{prefix}{wing}{wing_size}"
        _add_edge(sections, wing_end, center_id)

    # 5. Циклы
    _add_cycles(sections, cycles_ratio=CYCLES_RATIO)

    # 6. Тупики
    _ensure_dead_ends(sections, min_count=MIN_DEAD_ENDS)

    # 7. Типы секций
    _classify_sections(sections)

    # 8. Входы
    entrances = {
        "N": f"{prefix}N1",
        "S": f"{prefix}S1",
        "W": f"{prefix}W1",
        "E": f"{prefix}E1",
    }

    return {
        "sections": sections,
        "center": center_id,
        "entrances": entrances,
        "stairs_down": center_id,
    }


# ============ Внутренние функции ============

def _generate_wing_graph(sections: dict, wing_sections: list, wing: str,
                          wing_size: int = WING_SIZE):
    """
    Генерация графа крыла по правилам «колец».
    
    Правила:
      1. Цепочка вперёд: ring k → ring k+1 (обязательно).
      2. Обратные рёбра: ring k → ring k-1 (создаёт циклы).
      3. Внутри кольца: соседние секции одного кольца связаны с шансом.
      4. Рёбра «дальше 2 колец» запрещены.
      5. Шанс горизонтальных связей между крыльями — отдельно.
    """
    import random as _r
    from collections import defaultdict

    # Группируем секции по кольцу
    # wing_sections = [f"{prefix}{wing}{r}" for r in range(1, wing_size+1)]
    # ring_map[ring] = section_id
    ring_map = {}
    for sid in wing_sections:
        # sid = "L1_N5" → ring = 5
        try:
            ring = int(sid.split(wing)[-1])
        except (ValueError, IndexError):
            continue
        ring_map[ring] = sid

    rings = sorted(ring_map.keys())  # [1, 2, 3, ..., 30]

    # === 1. Цепочка вперёд (обязательно) ===
    for k in range(len(rings) - 1):
        a = ring_map[rings[k]]
        b = ring_map[rings[k + 1]]
        _add_edge(sections, a, b)

    # === 2. Обратные рёбра (создают циклы) ===
    for k in range(1, len(rings) - 1):
        # с шансом 40% добавить ребро в предыдущее кольцо
        # (кроме крайних)
        if _r.random() < 0.4:
            a = ring_map[rings[k]]
            b = ring_map[rings[k - 1]]
            _add_edge(sections, a, b)

    # === 3. Соседи внутри кольца: (ring, ring+1) — горизонтальные ===
    # Реализуется в отдельной функции ниже, на уровне всего слоя.

    # === 4. Небольшая доля «дальних» рёбер (для интриги) ===
    # Но только соседние-через-одно (ring k ↔ ring k+2) с очень низким шансом.
    for k in range(len(rings) - 2):
        if _r.random() < 0.05:  # 5%
            a = ring_map[rings[k]]
            b = ring_map[rings[k + 2]]
            _add_edge(sections, a, b)


def _add_edge(sections: dict, a: str, b: str):
    if b not in sections[a]["exits"]:
        sections[a]["exits"].append(b)
    if a not in sections[b]["exits"]:
        sections[b]["exits"].append(a)


def _are_connected(sections: dict, a: str, b: str) -> bool:
    return b in sections[a]["exits"]


def _add_cycles(sections: dict, cycles_ratio: float = 0.20):
    """
    Добавляет циклы (рёбра внутри одного кольца и между соседними).
    Не создаёт «паразитных» дальних рёбер.
    """
    import random as _r

    # Группируем секции по (wing, ring)
    by_wing_ring = {}
    for sid, spec in sections.items():
        if spec.get("type") == "center":
            continue
        wing = spec["wing"]
        ring = spec["ring"]
        by_wing_ring.setdefault((wing, ring), []).append(sid)

    all_sections = [sid for sid, s in sections.items() if s.get("type") != "center"]
    target_cycles = max(2, int(len(all_sections) * cycles_ratio))

    added = 0
    attempts = 0
    max_attempts = target_cycles * 10

    while added < target_cycles and attempts < max_attempts:
        attempts += 1
        a = _r.choice(all_sections)
        spec_a = sections[a]
        wing_a = spec_a["wing"]
        ring_a = spec_a["ring"]

        # Кандидаты: то же кольцо, другого крыла (например, N5 ↔ S5)
        # или соседнее кольцо в том же крыле (N5 ↔ N6)
        candidates = []

        # Соседние кольца в том же крыле
        for delta in (-1, 1):
            r2 = ring_a + delta
            if r2 >= 1:
                key = (wing_a, r2)
                for sid in by_wing_ring.get(key, []):
                    if sid != a and sid not in spec_a["exits"]:
                        candidates.append(sid)

        # То же кольцо, разные крылья
        for wing_b in ("N", "S", "W", "E"):
            if wing_b == wing_a:
                continue
            key = (wing_b, ring_a)
            for sid in by_wing_ring.get(key, []):
                if sid != a and sid not in spec_a["exits"]:
                    candidates.append(sid)

        if not candidates:
            continue

        b = _r.choice(candidates)

        # Проверка лимитов
        if len(spec_a["exits"]) >= MAX_EXITS_PER_SECTION:
            continue
        if len(sections[b]["exits"]) >= MAX_EXITS_PER_SECTION:
            continue

        _add_edge(sections, a, b)
        added += 1


def _ensure_dead_ends(sections: dict, min_count: int = 8):
    """
    Создаёт тупики БЕЗОПАСНО:
      - удаляет только рёбра, соединяющие секции ОДНОГО крыла
      - НЕ удаляет рёбра между кольцами (не рвёт цепочку)
      - удаляет симметрично
      - проверяет связность после каждого удаления
    """
    import random as _r
    from collections import deque

    def count_dead_ends():
        return sum(1 for s in sections.values() if len(s["exits"]) == 1)

    def is_connected(start, target, skip_edge=None):
        """BFS от start до target. skip_edge = (a, b) — игнорировать это ребро."""
        if start not in sections or target not in sections:
            return False
        queue = deque([start])
        visited = {start}
        while queue:
            node = queue.popleft()
            for nxt in sections[node]["exits"]:
                # Пропускаем указанное ребро
                if skip_edge:
                    a, b = skip_edge
                    if (node == a and nxt == b) or (node == b and nxt == a):
                        continue
                if nxt == target:
                    return True
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        return False

    # Проверяем связность «вход→центр» для всех крыльев
    center = None
    entrances = {}
    for sid, spec in sections.items():
        if spec.get("type") == "center":
            center = sid
        if spec.get("ring") == 1:
            wing = spec["wing"]
            if wing not in entrances:
                entrances[wing] = sid

    def all_connected():
        if not center:
            return True
        for wing, entry in entrances.items():
            if not is_connected(entry, center):
                return False
        return True

    if not all_connected():
        return  # Изначально не связно — не наша забота

    attempts = 0
    max_attempts = 200

    while count_dead_ends() < min_count and attempts < max_attempts:
        attempts += 1

        # Кандидаты: секции с >=3 рёбрами, ring != 1
        candidates = []
        for sid, spec in sections.items():
            if spec.get("type") == "center":
                continue
            if len(spec["exits"]) < 3:
                continue
            if spec["ring"] == 1:
                continue
            candidates.append(sid)

        if not candidates:
            break

        sid = _r.choice(candidates)
        spec = sections[sid]
        wing = spec["wing"]

        # Ищем ребро, которое соединяет секции ОДНОГО крыла
        # (не между кольцами)
        removable = []
        for target in spec["exits"]:
            target_spec = sections.get(target)
            if not target_spec:
                continue
            if target_spec.get("type") == "center":
                continue
            if target_spec.get("wing") != wing:
                continue
            # Кольца должны совпадать или быть рядом
            ring_diff = abs(spec["ring"] - target_spec["ring"])
            if ring_diff > 2:
                continue
            removable.append(target)

        if not removable:
            continue

        target = _r.choice(removable)

        # Проверяем, что после удаления связность сохранится
        if not is_connected(sid, target, skip_edge=(sid, target)):
            continue  # Удаление разорвало бы граф

        # Удаляем симметрично
        if target in sections[sid]["exits"]:
            sections[sid]["exits"].remove(target)
        if sid in sections[target]["exits"]:
            sections[target]["exits"].remove(sid)

        # Проверяем глобальную связность
        if not all_connected():
            # Откат
            _add_edge(sections, sid, target)
            continue


def _classify_sections(sections: dict):
    for sid, spec in sections.items():
        if spec["type"] == "center":
            continue
        exits_count = len(spec["exits"])
        if exits_count == 1:
            spec["type"] = "dead_end"
        elif exits_count == 2:
            spec["type"] = "corridor"
        elif exits_count == 3:
            spec["type"] = "junction"
        else:
            spec["type"] = "hall"


# ============ Имена секций ============

SECTION_NAMES = {
    "corridor": [
        "Затопленный коридор", "Узкий проход", "Мшистый коридор",
        "Треснувший ход", "Тёмный туннель", "Каменный жёлоб",
        "Наклонный коридор", "Сырой проход",
    ],
    "hall": [
        "Зал Эха", "Круглый зал", "Просторная пещера",
        "Разрушенный зал", "Зал с колоннами",
    ],
    "dead_end": [
        "Тупик", "Глухой закуток", "Каменный мешок",
        "Стена", "Обрыв пути",
    ],
    "junction": [
        "Развилка", "Перекрёсток", "Развилка трёх путей",
        "Раздорожье",
    ],
    "center": [
        "Сердце Лабиринта", "Центральный зал",
        "Ядро", "Средоточие",
    ],
}

ROMAN = ["", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X",
         " XI", " XII", " XIII", " XIV", " XV"]


def assign_names(sections: dict, lang: str = "ru") -> dict:
    used = {}
    result = {}

    for sid, spec in sections.items():
        stype = spec.get("type", "corridor")
        options = SECTION_NAMES.get(stype, ["Секция"])
        base = random.choice(options)
        count = used.get(base, 0)
        used[base] = count + 1

        if count > 0:
            suffix = ROMAN[count] if count < len(ROMAN) else f" {count+1}"
            name = base + suffix
        else:
            name = base

        result[sid] = name

    return result


# ============ Отладка ============

def print_map(layer: dict):
    sections = layer["sections"]
    print(f"\n=== Layer map ({len(sections)} sections) ===\n")
    for sid, spec in sorted(sections.items()):
        print(f"{sid:12} [{spec['type']:10}] exits: {spec['exits']}")
    print(f"\nCenter: {layer['center']}")
    print(f"Entrances: {layer['entrances']}")


if __name__ == "__main__":
    layer = generate_layer(1, seed=42)
    print_map(layer)
