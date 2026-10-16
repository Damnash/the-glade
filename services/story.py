# services/story.py

from content.story import STORY_QUESTS, STORY_STAGES, STORY_ACHIEVEMENTS
from db.story import (
    unlock_stage, is_stage_unlocked, get_player_stages,
    get_quest_status, set_quest_status, add_progress, get_active_quests,
)


class StoryError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


def get_available_quests(user_id: int, giver: str) -> list[str]:
    """Доступные квесты от NPC."""
    result = []
    for key, quest in STORY_QUESTS.items():
        if quest["giver"] != giver:
            continue
        status = get_quest_status(user_id, key)
        if status == "available":
            result.append(key)
    return result


def get_active_quests_for(user_id: int, giver: str = None) -> list[dict]:
    """Активные квесты."""
    active = get_active_quests(user_id)
    result = []
    for q in active:
        if q["status"] != "active":
            continue
        quest = STORY_QUESTS.get(q["quest_key"])
        if not quest:
            continue
        if giver and quest["giver"] != giver:
            continue
        result.append({
            "key": q["quest_key"],
            "progress": q["progress"],
            "need": quest["need"],
            "quest": quest,
        })
    return result


def start_quest(user_id: int, quest_key: str) -> dict:
    """Начать квест."""
    quest = STORY_QUESTS.get(quest_key)
    if not quest:
        raise StoryError("story.err.unknown_quest")

    status = get_quest_status(user_id, quest_key)
    if status == "active":
        raise StoryError("story.err.already_active")
    if status == "complete":
        raise StoryError("story.err.already_complete")

    set_quest_status(user_id, quest_key, "active")
    return quest


def check_quest_progress(user_id: int, quest_key: str) -> dict:
    """Проверить, завершён ли квест."""
    from db.connection import get_conn
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT progress FROM story_quests
        WHERE user_id = ? AND quest_key = ?
    """, (user_id, quest_key))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {"done": False, "progress": 0}

    quest = STORY_QUESTS.get(quest_key)
    if not quest:
        return {"done": False, "progress": 0}

    progress = row[0]
    return {
        "done": progress >= quest["need"],
        "progress": progress,
        "need": quest["need"],
    }


def complete_quest(user_id: int, quest_key: str) -> dict:
    """Завершить квест — выдать награды."""
    from db.players import get_player, update_player_fields
    from db.achievements import give_achievement

    quest = STORY_QUESTS.get(quest_key)
    if not quest:
        raise StoryError("story.err.unknown_quest")

    status = get_quest_status(user_id, quest_key)
    if status != "active":
        raise StoryError("story.err.not_active")

    check = check_quest_progress(user_id, quest_key)
    if not check["done"]:
        raise StoryError("story.err.not_done")

    # Награды
    player = get_player(user_id)
    reward = quest.get("reward", {})
    updates = {}

    tokens = reward.get("tokens", 0)
    if tokens:
        updates["tokens"] = player.get("tokens", 0) + tokens

    # Ресурсы
    resources = reward.get("resource", {})
    if resources:
        from db.inventory import add_item
        for item_key, qty in resources.items():
            add_item(user_id, item_key, qty)

    if updates:
        update_player_fields(user_id, updates)

    # Звание
    ach_key = quest.get("reward_achievement")
    if ach_key:
        give_achievement(user_id, ach_key)

    # Разблокировка этапов
    for stage_key in quest.get("unlocks", []):
        unlock_stage(user_id, stage_key)

    set_quest_status(user_id, quest_key, "complete")

    return {
        "quest": quest,
        "reward": reward,
        "achievement": ach_key,
    }


# ============ Трекинг прогресса ============

def track_event(user_id: int, event_type: str, data: dict = None):
    """Трекинг событий для квестов."""
    data = data or {}

    for quest_key, quest in STORY_QUESTS.items():
        status = get_quest_status(user_id, quest_key)
        if status != "active":
            continue

        if quest["type"] != event_type:
            continue

        # Дополнительные условия
        if event_type == "talk_npc":
            if data.get("npc") != quest.get("target"):
                continue
        elif event_type == "find_key":
            if data.get("key_number") != quest.get("target"):
                continue
        elif event_type == "visit_sections":
            # любая новая секция
            pass
        elif event_type == "find_fragments":
            pass
        elif event_type == "kill_grievers":
            pass
        elif event_type == "reach_center":
            pass
        elif event_type == "collect_keys":
            # обновляем прогресс по количеству
            from db.keys import get_player_keys
            from core.maze_current import get_current_season
            season = get_current_season()
            keys = get_player_keys(season, user_id)
            # Установим прогресс = количество ключей
            from db.connection import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                UPDATE story_quests SET progress = ?
                WHERE user_id = ? AND quest_key = ? AND status = 'active'
            """, (len(keys), user_id, quest_key))
            conn.commit()
            conn.close()
            continue

        add_progress(user_id, quest_key, 1)
