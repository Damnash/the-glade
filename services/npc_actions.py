# services/npc_actions.py

import random


class NPCActionError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


# ============ КЛИНТ — Крафт ============

CRAFT_RECIPES = {
    "knife": {
        "tokens": 5,
        "materials": {},  # пока пусто
        "result_item": "knife",
        "result_qty": 1,
        "name_key": "item.knife.name",
    },
    "torch": {
        "tokens": 3,
        "materials": {},
        "result_item": "torch",
        "result_qty": 3,
        "name_key": "item.torch.name",
    },
    "rope": {
        "tokens": 2,
        "materials": {},
        "result_item": "rope",
        "result_qty": 1,
        "name_key": "item.rope.name",
    },
    "water_flask": {
        "tokens": 4,
        "materials": {},
        "result_item": "water_flask",
        "result_qty": 1,
        "name_key": "item.water_flask.name",
    },
}


def craft(user_id: int, recipe_key: str) -> dict:
    """Крафт предмета за жетоны."""
    from db.players import get_player, update_player_fields
    from db.inventory import add_item

    if recipe_key not in CRAFT_RECIPES:
        raise NPCActionError("npc.clint.unknown_recipe")

    recipe = CRAFT_RECIPES[recipe_key]
    player = get_player(user_id)

    # Бонус клана (скидка на крафт)
    from services.bonuses import get_clan_bonus
    clan_bonus = get_clan_bonus(player)
    discount = clan_bonus.get("craft_discount", 0)
    final_cost = int(recipe["tokens"] * (1 - discount))
    final_cost = max(1, final_cost)  # минимум 1

    if player.get("tokens", 0) < final_cost:
        raise NPCActionError(
            "npc.clint.no_tokens",
            cost=final_cost,
            have=player.get("tokens", 0),
        )

    # Списываем жетоны
    update_player_fields(user_id, {
        "tokens": player["tokens"] - final_cost,
    })

    # Выдаём предмет
    add_item(user_id, recipe["result_item"], recipe["result_qty"])

    return {
        "item": recipe["result_item"],
        "qty": recipe["result_qty"],
        "cost": final_cost,
        "discount": discount,
    }


# ============ АЛБИ — Квесты ============

# Простые квесты — ежедневные
SIMPLE_QUESTS = {
    "fragments_3": {
        "name_key": "npc.alby.quest.fragments_3",
        "type": "collect",
        "item_key": "map_fragment",
        "need": 3,
        "reward_tokens": 20,
    },
    "grievers_5": {
        "name_key": "npc.alby.quest.grievers_5",
        "type": "kill",
        "monster": "any",
        "need": 5,
        "reward_tokens": 15,
    },
    "talk_minho": {
        "name_key": "npc.alby.quest.talk_minho",
        "type": "visit",
        "target": "minho",
        "need": 1,
        "reward_tokens": 5,
    },
}


def get_active_quest(user_id: int) -> dict | None:
    """Активный квест игрока."""
    from db.connection import get_conn

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM player_quests
        WHERE user_id = ? AND status = 'active'
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def start_quest(user_id: int, quest_key: str) -> dict:
    """Начать квест."""
    from db.connection import get_conn
    from core.time_utils import now

    if quest_key not in SIMPLE_QUESTS:
        raise NPCActionError("npc.alby.unknown_quest")

    # Уже есть активный?
    if get_active_quest(user_id):
        raise NPCActionError("npc.alby.already_has_quest")

    quest = SIMPLE_QUESTS[quest_key]

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO player_quests (user_id, quest_key, progress, need, status, started_at)
        VALUES (?, ?, 0, ?, 'active', ?)
    """, (user_id, quest_key, quest["need"], now()))
    conn.commit()
    conn.close()

    return quest


def update_quest_progress(user_id: int, event_type: str, event_data: dict):
    """Обновить прогресс квеста."""
    from db.connection import get_conn

    quest = get_active_quest(user_id)
    if not quest:
        return

    quest_key = quest["quest_key"]
    spec = SIMPLE_QUESTS.get(quest_key)
    if not spec:
        return

    matches = False
    if spec["type"] == "collect" and event_type == "collect":
        if event_data.get("item") == spec["item_key"]:
            matches = True
    elif spec["type"] == "kill" and event_type == "kill":
        matches = True
    elif spec["type"] == "visit" and event_type == "visit":
        if event_data.get("target") == spec["target"]:
            matches = True

    if not matches:
        return

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE player_quests
        SET progress = progress + 1
        WHERE user_id = ? AND status = 'active'
    """, (user_id,))
    conn.commit()
    conn.close()


def try_complete_quest(user_id: int) -> dict | None:
    """Попробовать завершить квест. Возвращает награду или None."""
    from db.connection import get_conn
    from db.players import get_player, update_player_fields
    from core.time_utils import now

    quest = get_active_quest(user_id)
    if not quest:
        return None

    if quest["progress"] < quest["need"]:
        return None

    spec = SIMPLE_QUESTS.get(quest["quest_key"])
    if not spec:
        return None

    # Награда
    player = get_player(user_id)
    reward = spec["reward_tokens"]

    update_player_fields(user_id, {
        "tokens": player.get("tokens", 0) + reward,
    })

    # Помечаем квест выполненным
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE player_quests
        SET status = 'complete', completed_at = ?
        WHERE user_id = ? AND status = 'active'
    """, (now(), user_id))
    conn.commit()
    conn.close()

    return {
        "quest_key": quest["quest_key"],
        "reward": reward,
    }


# ============ ГАЛЛИ — Провокации ============

def gally_respond(user_id: int, response: str) -> dict:
    """Ответ Галли.
    response: "rude" | "silent" | "fight"
    """
    from db.players import get_player, update_player_fields

    player = get_player(user_id)

    if response == "silent":
        return {"type": "silent"}

    if response == "rude":
        # Галли бьёт — рандом 3-8
        damage = random.randint(3, 8)
        new_hp = max(1, player["hp"] - damage)
        update_player_fields(user_id, {"hp": new_hp})
        return {"type": "rude", "damage": damage, "hp": new_hp}

    if response == "fight":
        # Шанс победы зависит от HP
        hp = player["hp"]
        if hp > 80:
            chance = 0.7
        elif hp > 50:
            chance = 0.4
        else:
            chance = 0.15

        if random.random() < chance:
            # Победа — +5 жетонов
            reward = 5
            update_player_fields(user_id, {
                "tokens": player.get("tokens", 0) + reward,
            })
            return {"type": "fight_win", "reward": reward}
        else:
            # Поражение — большой урон
            damage = random.randint(8, 15)
            new_hp = max(1, player["hp"] - damage)
            update_player_fields(user_id, {"hp": new_hp})
            return {"type": "fight_lose", "damage": damage, "hp": new_hp}

    raise NPCActionError("npc.gally.unknown_response")


# ============ УИНСТОН — Обмен ============

TRADE_RATES = {
    "food_to_tokens": {
        "give_item": "food",
        "give_qty": 5,
        "get_tokens": 3,
    },
    "water_to_tokens": {
        "give_item": "water",
        "give_qty": 3,
        "get_tokens": 2,
    },
    "tokens_to_food": {
        "give_tokens": 3,
        "get_item": "food",
        "get_qty": 5,
    },
    "tokens_to_water": {
        "give_tokens": 2,
        "get_item": "water",
        "get_qty": 3,
    },
}


def winston_trade(user_id: int, trade_key: str) -> dict:
    """Обмен с Уинстоном."""
    from db.players import get_player, update_player_fields

    if trade_key not in TRADE_RATES:
        raise NPCActionError("npc.winston.unknown_trade")

    trade = TRADE_RATES[trade_key]
    player = get_player(user_id)

    updates = {}

    # Отдаёт игрок
    if "give_item" in trade:
        item = trade["give_item"]
        qty = trade["give_qty"]
        have = player.get(item, 0)
        if have < qty:
            raise NPCActionError(
                "npc.winston.not_enough",
                item=item, need=qty, have=have,
            )
        updates[item] = have - qty

    if "give_tokens" in trade:
        tokens = trade["give_tokens"]
        have = player.get("tokens", 0)
        if have < tokens:
            raise NPCActionError(
                "npc.winston.not_enough_tokens",
                need=tokens, have=have,
            )
        updates["tokens"] = have - tokens

    # Получает игрок
    if "get_tokens" in trade:
        updates["tokens"] = updates.get("tokens", player.get("tokens", 0)) + trade["get_tokens"]

    if "get_item" in trade:
        item = trade["get_item"]
        qty = trade["get_qty"]
        if item == "food":
            updates["food"] = min(
                player.get("food", 0) + qty,
                player.get("max_food", 10),
            )
        elif item == "water":
            updates["water"] = min(
                player.get("water", 0) + qty,
                player.get("max_water", 5),
            )

    update_player_fields(user_id, updates)

    return {
        "trade_key": trade_key,
        "updates": updates,
    }
