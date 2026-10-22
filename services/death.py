# services/death.py

import random

from db.connection import get_conn
from db.map_items import drop_all_non_personal_maps, get_maps_on_ground
from db.players import get_player, die_and_respawn
from core.time_utils import now
from services.event_log import add_event, cleanup_old_events


class DeathError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


# ============ Выпадение предметов ============

def drop_inventory_to_ground(user_id: int, section_id: str, layer: int) -> int:
    """Все предметы из инвентаря падают в секции."""
    conn = get_conn()
    cur = conn.cursor()

    # Берём инвентарь
    cur.execute("""
        SELECT item_key, quantity FROM inventory
        WHERE user_id = ?
    """, (user_id,))
    items = cur.fetchall()

    dropped = 0
    for item_key, quantity in items:
        cur.execute("""
            INSERT INTO items_on_ground
            (user_id, item_key, quantity, section_id, layer, dropped_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, item_key, quantity, section_id, layer, now()))
        dropped += 1

    # Очищаем инвентарь
    cur.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()
    return dropped


# ============ Главная функция ============

def die_in_maze(user_id: int, lang: str = "ru") -> dict:
    """
    Игрок умирает в Лабиринте.
    Возвращает dict с деталями для отображения.
    """
    player = get_player(user_id)
    if not player:
        raise DeathError("start.need_start")

    section_id = player.get("maze_section")
    layer = player.get("maze_layer", 1)

    if not section_id or layer == 0:
        raise DeathError("maze.not_in_maze")

    # 1. Выпадают карты (НЕ-личные)
    maps_dropped = drop_all_non_personal_maps(user_id, section_id, layer)

    # 2. Выпадают предметы
    items_dropped = drop_inventory_to_ground(user_id, section_id, layer)

    # Очки за смерть
    from services.achievements import award_points
    award_points(user_id, "death", field="deaths")

    # Автодневник
    try:
        from services.diary import add_diary_auto
        add_diary_auto(user_id, "died", section=section_id)
    except Exception:
        pass

    # Потеря дневника: копируем автозаписи в dropped_diaries, очищаем player_diary
    try:
        from db.connection import get_conn
        from services.diary import get_player_autodiary_text

        auto_text = get_player_autodiary_text(user_id)
        if auto_text:
            player = get_player(user_id)
            display_name = player["display_name"] or player["username"] if player else "?"
            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO dropped_diaries
                    (original_user_id, display_name, text, section_id, layer)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, display_name, auto_text, section_id, layer))
                # Очищаем автозаписи (ручные — оставляем)
                cur.execute("DELETE FROM player_diary WHERE user_id = ? AND text LIKE '[%]%'", (user_id,))
                conn.commit()
            finally:
                conn.close()
    except Exception as e:
        import logging
        logging.warning(f"[DEATH] drop diary failed: {e}")
    # Лог для главного меню
    try:
        from core.i18n import t
        _p = get_player(user_id)
        if _p:
            add_event(user_id, "died", t("log.died", _p["language"]), severity="important")
            cleanup_old_events(user_id)
    except Exception:
        pass

    # 3. Завершаем вылазку (если была)
    from services.maze_runs import end_run
    end_run(user_id)

    # 4. Выпадают ключи
    from services.keys import drop_all_keys_on_death
    keys_dropped = drop_all_keys_on_death(user_id, section_id, layer)

    # 4. Респавн
    die_and_respawn(user_id)

    # 5. Записать в memorial (для поминания) — с именем секции
    try:
        from services.weekly_memorial import record_death
        from core.maze_current import get_current_season
        from db.maze_map import get_section
        from core.i18n import t

        _player = get_player(user_id)
        if _player:
            _name = _player["display_name"] or _player["username"] or "?"
            _lang = _player["language"]

            # Имя секции (если есть)
            _section_display = section_id
            try:
                _season = get_current_season()
                _sec = get_section(_season, layer, section_id)
                if _sec and _sec.get("name"):
                    _section_display = _sec["name"]
            except Exception:
                pass

            _message = t("memorial.death_line", _lang,
                         section=_section_display, layer=layer)
            record_death(user_id, _name, _message)
    except Exception as e:
        import logging
        logging.warning(f"[DEATH] memorial failed: {e}")

    # 5. Проклятие (50% при смерти)
    try:
        import random
        if random.random() < 0.5:
            from services.buffs import add_buff
            add_buff(user_id, "cursed")
    except Exception:
        pass

    return {
        "section_id": section_id,
        "layer": layer,
        "maps_dropped": maps_dropped,
        "items_dropped": items_dropped,
        "keys_dropped": keys_dropped,
    }


def check_death(user_id: int) -> bool:
    """
    Проверяет, должен ли игрок умереть.
    Если да — убивает и респавнит.
    Возвращает True, если игрок умер.
    """
    player = get_player(user_id)
    if not player:
        return False

    if player["hp"] > 0:
        return False

    if player.get("maze_layer", 0) == 0:
        # Не в Лабиринте — просто обнуляем HP, не убиваем
        return False

    die_in_maze(user_id)
    return True


# ============ Подбор предметов ============

def pickup_all_items(user_id: int, section_id: str, layer: int) -> dict:
    """Подобрать все предметы и карты из секции."""
    from db.inventory import add_item
    from db.map_items import pickup_map

    conn = get_conn()
    cur = conn.cursor()

    # Предметы
    cur.execute("""
        SELECT id, item_key, quantity FROM items_on_ground
        WHERE section_id = ? AND layer = ?
    """, (section_id, layer))
    items = cur.fetchall()

    for item_id, item_key, quantity in items:
        add_item(user_id, item_key, quantity)
        cur.execute("DELETE FROM items_on_ground WHERE id = ?", (item_id,))

    # Карты
    cur.execute("""
        SELECT id FROM map_items
        WHERE owner_id IS NULL AND current_location = ? AND current_layer = ?
    """, (section_id, layer))
    maps = cur.fetchall()

    picked_maps = 0
    for (map_id,) in maps:
        if pickup_map(map_id, user_id):
            picked_maps += 1

    conn.commit()
    conn.close()

    return {
        "items": len(items),
        "maps": picked_maps,
    }


# ============ Сообщения о смерти ============

DEATH_MESSAGES = {
    "ru": [
        "Лабиринт забрал тебя. Стены сомкнулись, и ты не успел.",
        "Ты падаешь. Холодный камень принимает тебя.",
        "Последнее, что ты слышишь — низкий гул. Потом темнота.",
        "Гриверы нашли тебя. Это было быстро.",
        "Ты не вернулся с рейда. Стены запомнят твоё имя.",
        "Твой факел погас. Лабиринт не прощает темноты.",
        "Стены сдвинулись. Ты не успел отскочить.",
        "Ты слышал шаги, но было поздно. Они быстрее.",
        "Пол ушёл из-под ног. Ты не успел схватиться.",
        "Из темноты вылетело что-то. Ты не увидел — только почувствовал.",
        "Коридор замкнулся. Ты был внутри.",
        "Ты заблудился. Слишком долго. Слишком глубоко.",
        "Крик застрял в горле. Никто не услышал.",
        "Твоя рация замолчала. Навсегда.",
        "Ты увидел свет — но это был не выход.",
        "Стены покрылись изнутри. Ты был частью этого.",
        "Ты шёл в правильном направлении. Просто не в этот раз.",
        "Пыль в воздухе остановилась. Вместе с тобой.",
        "Лабиринт снова изменился. Ты — тоже. Уже не живой.",
        "Последний вдох. Последний шаг. Последняя тьма.",
    ],
    "en": [
        "The Maze took you. The walls closed in, and you weren't fast enough.",
        "You fall. Cold stone receives you.",
        "The last thing you hear is a low hum. Then darkness.",
        "The Grievers found you. It was quick.",
        "You did not return from the run. The walls will remember your name.",
        "Your torch went out. The Maze does not forgive darkness.",
        "The walls shifted. You did not dodge in time.",
        "You heard footsteps, but it was too late. They are faster.",
        "The floor fell away. You did not catch yourself.",
        "Something flew out of the darkness. You did not see it — only felt it.",
        "The corridor sealed itself. You were inside.",
        "You got lost. Too long. Too deep.",
        "The scream stuck in your throat. No one heard.",
        "Your radio went silent. Forever.",
        "You saw a light — but it was not the exit.",
        "The walls closed from within. You were part of it.",
        "You walked the right way. Just not this time.",
        "The dust in the air stopped. With you.",
        "The Maze changed again. So did you. No longer alive.",
        "Last breath. Last step. Last darkness.",
    ],
}

GLOBAL_DEATH_MESSAGES = {
    "ru": [
        "📢 Где-то в Лабиринте погиб Бегун.",
        "📢 Стены сомкнулись над кем-то. Имя неизвестно.",
        "📢 Гул Лабиринта стал громче — он забрал ещё одного.",
        "📢 В Глэйде убавилось на одного. Лабиринт молчит.",
        "📢 Чей-то факел погас. Навсегда.",
        "📢 Кто-то не вернулся с рейда.",
        "📢 Лабиринт снова напомнил, что он живой.",
        "📢 Ещё одно имя останется только в памяти.",
        "📢 Стены запомнили ещё одного Бегуна.",
        "📢 Холодный камень принял ещё одну душу.",
        "📢 Где-то в темноте стало тише. Кто-то ушёл.",
        "📢 Лабиринт редко отпускает тех, кто заходит глубоко.",
        "📢 Кто-то сегодня не вернётся к костру.",
        "📢 Тишина в эфире. Никто не ответил.",
        "📢 Гриверы снова на охоте.",
        "📢 Ещё один Бегун ушёл в темноту и не вернулся.",
        "📢 Последний вдох где-то в глубине.",
        "📢 Стены приняли ещё одну жертву.",
        "📢 Лабиринт напомнил, что он старше всех.",
        "📢 Чей-то путь оборвался. Имя неизвестно.",
    ],
    "en": [
        "📢 Somewhere in the Maze, a Runner has fallen.",
        "📢 The walls closed over someone. The name is unknown.",
        "📢 The hum of the Maze grew louder — it took another.",
        "📢 The Glade is one less. The Maze is silent.",
        "📢 Someone's torch went out. Forever.",
        "📢 Someone did not return from the run.",
        "📢 The Maze reminded us again that it is alive.",
        "📢 Another name will remain only in memory.",
        "📢 The walls remember another Runner.",
        "📢 Cold stone received another soul.",
        "📢 Somewhere in the dark, it went quiet. Someone left.",
        "📢 The Maze rarely releases those who go deep.",
        "📢 Someone will not return to the fire tonight.",
        "📢 Silence on the air. No one answered.",
        "📢 The Grievers are hunting again.",
        "📢 Another Runner walked into the dark and did not return.",
        "📢 A last breath somewhere in the depths.",
        "📢 The walls have taken another.",
        "📢 The Maze reminded us it is older than all of us.",
        "📢 Someone's path ended. The name is unknown.",
    ],
}


def random_death_message(lang: str = "ru") -> str:
    """Случайное сообщение о смерти для игрока."""
    pool = DEATH_MESSAGES.get(lang, DEATH_MESSAGES["ru"])
    return random.choice(pool)


def random_global_death_message(lang: str = "ru") -> str:
    """Случайное сообщение о смерти для всех."""
    pool = GLOBAL_DEATH_MESSAGES.get(lang, GLOBAL_DEATH_MESSAGES["ru"])
    return random.choice(pool)
