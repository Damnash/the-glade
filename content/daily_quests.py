# content/daily_quests.py
#
# Пул ежедневных личных квестов.
# Один квест на игрока в сутки (автоматически при первом заходе).

# Типы:
#   kill_griever   — убить N Гриверов
#   find_fragments — найти N фрагментов
#   visit_sections — посетить N секций
#   return_alive   — выйти из Лабиринта живым
#   bring_meat     — принести N мяса (Фрайпан)
#   find_water     — принести N фляг воды (Уинстон)


DAILY_QUESTS = {
    # ============ Простые ============
    "kill_griever_1": {
        "type": "kill_griever",
        "need": 1,
        "title_key": "dq.kill_griever_1.title",
        "desc_key": "dq.kill_griever_1.desc",
        "reward": {"tokens": 5},
        "icon": "⚔️",
    },
    "kill_griever_3": {
        "type": "kill_griever",
        "need": 3,
        "title_key": "dq.kill_griever_3.title",
        "desc_key": "dq.kill_griever_3.desc",
        "reward": {"tokens": 12, "resource": {"torch": 1}},
        "icon": "⚔️",
    },
    "find_fragments_2": {
        "type": "find_fragments",
        "need": 2,
        "title_key": "dq.find_fragments_2.title",
        "desc_key": "dq.find_fragments_2.desc",
        "reward": {"tokens": 10},
        "icon": "🗺️",
    },
    "visit_sections_5": {
        "type": "visit_sections",
        "need": 5,
        "title_key": "dq.visit_sections_5.title",
        "desc_key": "dq.visit_sections_5.desc",
        "reward": {"tokens": 8, "resource": {"torch": 1}},
        "icon": "🏃",
    },
    "return_alive": {
        "type": "return_alive",
        "need": 1,
        "title_key": "dq.return_alive.title",
        "desc_key": "dq.return_alive.desc",
        "reward": {"tokens": 6},
        "icon": "🚪",
    },

    # ============ NPC ============
    "bring_meat_3": {
        "type": "bring_meat",
        "need": 3,
        "title_key": "dq.bring_meat_3.title",
        "desc_key": "dq.bring_meat_3.desc",
        "reward": {"tokens": 8, "resource": {"food": 3}},
        "icon": "🥩",
    },
    "find_water_2": {
        "type": "find_water",
        "need": 2,
        "title_key": "dq.find_water_2.title",
        "desc_key": "dq.find_water_2.desc",
        "reward": {"tokens": 6, "resource": {"water_flask": 1}},
        "icon": "💧",
    },
}


SIMPLE_KEYS = [
    "kill_griever_1",
    "kill_griever_3",
    "find_fragments_2",
    "visit_sections_5",
    "return_alive",
]

NPC_KEYS = [
    "bring_meat_3",
    "find_water_2",
]


def pick_daily_quest() -> str:
    """Выбрать случайный квест на день (70% простой, 30% NPC)."""
    import random
    if random.random() < 0.3:
        return random.choice(NPC_KEYS)
    return random.choice(SIMPLE_KEYS)


def get_quest(key: str) -> dict | None:
    return DAILY_QUESTS.get(key)
