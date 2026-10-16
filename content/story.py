# content/story.py


# ============ ЭТАПЫ (разблокируют квесты) ============

STORY_STAGES = {
    "arrived": {
        "name_key": "story.stage.arrived.name",
        "desc_key": "story.stage.arrived.desc",
        "unlocked_by": None,  # доступен сразу
    },
    "met_alby": {
        "name_key": "story.stage.met_alby.name",
        "desc_key": "story.stage.met_alby.desc",
        "unlocked_by": "first_step",
    },
    "met_minho": {
        "name_key": "story.stage.met_minho.name",
        "desc_key": "story.stage.met_minho.desc",
        "unlocked_by": "find_minho",
    },
    "met_teresa": {
        "name_key": "story.stage.met_teresa.name",
        "desc_key": "story.stage.met_teresa.desc",
        "unlocked_by": "find_teresa",
    },
    "learned_truth": {
        "name_key": "story.stage.learned_truth.name",
        "desc_key": "story.stage.learned_truth.desc",
        "unlocked_by": "teresa_secret",
    },
    "final_ready": {
        "name_key": "story.stage.final_ready.name",
        "desc_key": "story.stage.final_ready.desc",
        "unlocked_by": "voice_of_maze",
    },
}


# ============ КВЕСТЫ (10) ============

STORY_QUESTS = {
    # 1. Первый шаг — от Алби
    "first_step": {
        "title_key": "story.quest.first_step.title",
        "desc_key": "story.quest.first_step.desc",
        "giver": "alby",
        "type": "enter_maze",  # войти в Лабиринт
        "need": 1,
        "reward": {"tokens": 10},
        "reward_achievement": "newcomer",
        "unlocks": ["met_alby"],
    },

    # 2. Найти Минхо — от Алби
    "find_minho": {
        "title_key": "story.quest.find_minho.title",
        "desc_key": "story.quest.find_minho.desc",
        "giver": "alby",
        "type": "talk_npc",  # поговорить с NPC
        "target": "minho",
        "need": 1,
        "reward": {"tokens": 15},
        "unlocks": ["met_minho"],
    },

    # 3. Разведка — от Минхо
    "recon": {
        "title_key": "story.quest.recon.title",
        "desc_key": "story.quest.recon.desc",
        "giver": "minho",
        "type": "visit_sections",  # посетить N секций
        "need": 3,
        "reward": {"tokens": 30},
        "reward_achievement": "scout_runner",
    },

    # 4. Фрагмент карты — от Минхо
    "fragment_hunt": {
        "title_key": "story.quest.fragment_hunt.title",
        "desc_key": "story.quest.fragment_hunt.desc",
        "giver": "minho",
        "type": "find_fragments",
        "need": 1,
        "reward": {"tokens": 40},
        "reward_achievement": "cartographer_story",
    },

    # 5. Найти Терезу — от Минхо
    "find_teresa": {
        "title_key": "story.quest.find_teresa.title",
        "desc_key": "story.quest.find_teresa.desc",
        "giver": "minho",
        "type": "talk_npc",
        "target": "teresa",
        "need": 1,
        "reward": {"tokens": 50},
        "unlocks": ["met_teresa"],
    },

    # 6. Тайна Терезы — от Терезы
    "teresa_secret": {
        "title_key": "story.quest.teresa_secret.title",
        "desc_key": "story.quest.teresa_secret.desc",
        "giver": "teresa",
        "type": "find_key",
        "target": 3,  # ключ 3
        "need": 1,
        "reward": {"tokens": 100, "resource": {"metal": 3}},
        "reward_achievement": "keeper_of_secret",
        "unlocks": ["learned_truth"],
    },

    # 7. Голос Лабиринта — от Терезы
    "voice_of_maze": {
        "title_key": "story.quest.voice_of_maze.title",
        "desc_key": "story.quest.voice_of_maze.desc",
        "giver": "teresa",
        "type": "kill_grievers",
        "need": 5,
        "reward": {"tokens": 150},
        "reward_achievement": "hunter_story",
        "unlocks": ["final_ready"],
    },

    # 8. Через стены — от Терезы
    "through_walls": {
        "title_key": "story.quest.through_walls.title",
        "desc_key": "story.quest.through_walls.desc",
        "giver": "teresa",
        "type": "reach_center",  # дойти до Центра
        "need": 1,
        "reward": {"tokens": 80},
    },

    # 9. Ключи Врат — от Терезы
    "keys_of_gates": {
        "title_key": "story.quest.keys_of_gates.title",
        "desc_key": "story.quest.keys_of_gates.desc",
        "giver": "teresa",
        "type": "collect_keys",
        "need": 3,  # минимум 3 ключа
        "reward": {"tokens": 200},
        "reward_achievement": "keykeeper_story",
    },

    # 10. Путь к Вратам — от Терезы
    "path_to_gates": {
        "title_key": "story.quest.path_to_gates.title",
        "desc_key": "story.quest.path_to_gates.desc",
        "giver": "teresa",
        "type": "open_gates",
        "need": 1,
        "reward": {"tokens": 500},
        "reward_achievement": "freed_story",
    },
}


# ============ ДОСТИЖЕНИЯ ЗА СЮЖЕТ ============

STORY_ACHIEVEMENTS = {
    "newcomer": {
        "name_key": "ach.newcomer.name",
        "desc_key": "ach.newcomer.desc",
        "icon": "🌱",
    },
    "scout_runner": {
        "name_key": "ach.scout_runner.name",
        "desc_key": "ach.scout_runner.desc",
        "icon": "🏃",
    },
    "cartographer_story": {
        "name_key": "ach.cartographer_story.name",
        "desc_key": "ach.cartographer_story.desc",
        "icon": "🗺️",
    },
    "keeper_of_secret": {
        "name_key": "ach.keeper_of_secret.name",
        "desc_key": "ach.keeper_of_secret.desc",
        "icon": "🤫",
    },
    "hunter_story": {
        "name_key": "ach.hunter_story.name",
        "desc_key": "ach.hunter_story.desc",
        "icon": "🐺",
    },
    "keykeeper_story": {
        "name_key": "ach.keykeeper_story.name",
        "desc_key": "ach.keykeeper_story.desc",
        "icon": "🗝️",
    },
    "freed_story": {
        "name_key": "ach.freed_story.name",
        "desc_key": "ach.freed_story.desc",
        "icon": "🌟",
    },
}
