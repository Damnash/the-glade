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
    """Growing Tree алгоритм для крыла."""
    start = wing_sections[0]
    visited = {start}
    active = [start]

    while active:
        current = random.choice(active)
        sid = current

        neighbors = [s for s in wing_sections if s != sid and s not in visited]

        if not neighbors:
            active.remove(current)
            continue

        next_section = random.choice(neighbors)
        _add_edge(sections, sid, next_section)

        visited.add(next_section)
        active.append(next_section)

    # Дополнительные связи для циклов
    extra_edges = max(1, wing_size // 2)
    for _ in range(extra_edges):
        a = random.choice(wing_sections)
        b = random.choice(wing_sections)
        if a != b and not _are_connected(sections, a, b):
            _add_edge(sections, a, b)


def _add_edge(sections: dict, a: str, b: str):
    if b not in sections[a]["exits"]:
        sections[a]["exits"].append(b)
    if a not in sections[b]["exits"]:
        sections[b]["exits"].append(a)


def _are_connected(sections: dict, a: str, b: str) -> bool:
    return b in sections[a]["exits"]


def _add_cycles(sections: dict, cycles_ratio: float = 0.20):
    all_sections = list(sections.keys())
    target_cycles = max(2, int(len(all_sections) * cycles_ratio))

    added = 0
    attempts = 0
    while added < target_cycles and attempts < 200:
        attempts += 1
        a = random.choice(all_sections)
        b = random.choice(all_sections)

        if a == b:
            continue
        if _are_connected(sections, a, b):
            continue
        if len(sections[a]["exits"]) >= MAX_EXITS_PER_SECTION:
            continue
        if len(sections[b]["exits"]) >= MAX_EXITS_PER_SECTION:
            continue

        _add_edge(sections, a, b)
        added += 1


def _ensure_dead_ends(sections: dict, min_count: int = 8):
    dead_ends = [sid for sid, s in sections.items() if len(s["exits"]) == 1]

    while len(dead_ends) < min_count:
        candidates = [
            sid for sid, s in sections.items()
            if len(s["exits"]) >= 3 and s["ring"] != 1
        ]
        if not candidates:
            break

        sid = random.choice(candidates)
        target = random.choice(sections[sid]["exits"])
        sections[sid]["exits"].remove(target)
        if sid in sections[target]["exits"]:
            sections[target]["exits"].remove(sid)

        dead_ends = [s for s, v in sections.items() if len(v["exits"]) == 1]


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
