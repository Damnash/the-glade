# content/titles.py
#
# Титулы — за достижения. Показываются в /stats, /who, /top.
# Условия: убийства Гриверов, фрагменты, секреты Терезы, работы.

TITLES = {
    # Убийства Гриверов
    "griever_10": {
        "name_key": "title.griever_10.name",
        "desc_key": "title.griever_10.desc",
        "icon": "🐺",
        "condition": {"type": "griever_kills", "need": 10},
    },
    "griever_25": {
        "name_key": "title.griever_25.name",
        "desc_key": "title.griever_25.desc",
        "icon": "🩸",
        "condition": {"type": "griever_kills", "need": 25},
    },
    "griever_50": {
        "name_key": "title.griever_50.name",
        "desc_key": "title.griever_50.desc",
        "icon": "💀",
        "condition": {"type": "griever_kills", "need": 50},
    },
    # Фрагменты карты
    "cartographer_5": {
        "name_key": "title.cartographer_5.name",
        "desc_key": "title.cartographer_5.desc",
        "icon": "🧭",
        "condition": {"type": "fragments", "need": 5},
    },
    "cartographer_10": {
        "name_key": "title.cartographer_10.name",
        "desc_key": "title.cartographer_10.desc",
        "icon": "🗺️",
        "condition": {"type": "fragments", "need": 10},
    },
    "cartographer_30": {
        "name_key": "title.cartographer_30.name",
        "desc_key": "title.cartographer_30.desc",
        "icon": "🧭",
        "condition": {"type": "fragments", "need": 30},
    },
    # Секреты Терезы
    "seeker_5": {
        "name_key": "title.seeker_5.name",
        "desc_key": "title.seeker_5.desc",
        "icon": "🌙",
        "condition": {"type": "teresa_secrets", "need": 5},
    },
    "seeker_10": {
        "name_key": "title.seeker_10.name",
        "desc_key": "title.seeker_10.desc",
        "icon": "🔮",
        "condition": {"type": "teresa_secrets", "need": 10},
    },
    # Работа
    "worker_10": {
        "name_key": "title.worker_10.name",
        "desc_key": "title.worker_10.desc",
        "icon": "⚒️",
        "condition": {"type": "work_done", "need": 10},
    },
    # Ключи
    "key_bearer": {
        "name_key": "title.key_bearer.name",
        "desc_key": "title.key_bearer.desc",
        "icon": "🗝️",
        "condition": {"type": "keys_found", "need": 3},
    },
    # Смерти (за упорство)
    "unbroken": {
        "name_key": "title.unbroken.name",
        "desc_key": "title.unbroken.desc",
        "icon": "🛡️",
        "condition": {"type": "deaths", "need": 5},
    },
}
