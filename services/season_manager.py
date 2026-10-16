# services/season_manager.py

import logging
from datetime import datetime

from core.maze_current import get_current_season, get_season_day
from db.connection import get_conn


SEASON_LENGTH_DAYS = 90


def should_end_season(season_id: int) -> bool:
    """Пора ли завершить сезон?"""
    day = get_season_day(season_id)
    return day > SEASON_LENGTH_DAYS


def end_season(season_id: int) -> dict:
    """
    Завершить сезон.
    Возвращает статистику.
    """
    logging.info(f"[SEASON] Ending season {season_id}")

    # 1. Топ-3 по очкам → Зал Славы + звания
    from db.achievements import get_leaderboard, add_to_hall, give_achievement
    from db.players import get_player

    top = get_leaderboard(season_id, limit=3)
    winners = []

    for i, entry in enumerate(top):
        uid = entry["user_id"]
        p = get_player(uid)
        if not p:
            continue

        name = p["display_name"] or p["username"]

        # Утешительные звания (если нет главных)
        if i == 0:
            add_to_hall(season_id, uid, name, "top1")
            winners.append({"place": 1, "name": name, "score": entry["score"]})
        elif i == 1:
            add_to_hall(season_id, uid, name, "top2")
            winners.append({"place": 2, "name": name, "score": entry["score"]})
        elif i == 2:
            add_to_hall(season_id, uid, name, "top3")
            winners.append({"place": 3, "name": name, "score": entry["score"]})

    # 2. Создать новый сезон
    new_season_id = season_id + 1

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO maze_state (season_id, start_date, layers_unlocked)
        VALUES (?, ?, 1)
    """, (new_season_id, datetime.utcnow()))
    conn.commit()
    conn.close()

    logging.info(f"[SEASON] New season {new_season_id} started")

    # 3. Сбросить состояние игроков
    reset_players_state()

    # 4. Удалить карты, ключи, очки, PvP-логи старого сезона
    cleanup_old_season(season_id)

    return {
        "old_season": season_id,
        "new_season": new_season_id,
        "winners": winners,
    }


def reset_players_state():
    """Сбросить состояние игроков."""
    conn = get_conn()
    cur = conn.cursor()

    # Сброс всех прогрессов
    cur.execute("""
        UPDATE players SET
            hp = 100,
            energy = 100,
            sanity = 100,
            food = 0,
            water = 0,
            tokens = 0,
            location = 'center',
            maze_layer = 0,
            maze_section = NULL,
            status = 'active',
            work_type = NULL,
            work_ends_at = NULL,
            last_seen = CURRENT_TIMESTAMP,
            last_fed_at = CURRENT_TIMESTAMP,
            last_drank_at = CURRENT_TIMESTAMP,
            last_sanity_at = CURRENT_TIMESTAMP
    """)

    # Очистить инвентарь
    cur.execute("DELETE FROM inventory")

    # Очистить приглашения, дуэли
    cur.execute("DELETE FROM clan_invites")
    cur.execute("DELETE FROM duels")
    cur.execute("DELETE FROM steal_cooldowns")
    cur.execute("DELETE FROM active_combats")
    cur.execute("DELETE FROM maze_moves")
    cur.execute("DELETE FROM items_on_ground")

    # Очистить кланы
    cur.execute("DELETE FROM clan_members")
    cur.execute("DELETE FROM clan_messages")
    cur.execute("DELETE FROM clan_map_sections")
    cur.execute("DELETE FROM clans")

    conn.commit()
    conn.close()

    logging.info("[SEASON] Players state reset")


def cleanup_old_season(season_id: int):
    """Удалить данные старого сезона."""
    conn = get_conn()
    cur = conn.cursor()

    # Карты
    cur.execute("DELETE FROM map_items WHERE created_at < (SELECT start_date FROM maze_state WHERE season_id = ?)", (season_id,))
    cur.execute("DELETE FROM map_item_sections WHERE season_id = ?", (season_id,))

    # Ключи
    cur.execute("DELETE FROM season_keys WHERE season_id = ?", (season_id,))

    # Очки
    cur.execute("DELETE FROM season_scores WHERE season_id = ?", (season_id,))

    # PvP-лог
    cur.execute("DELETE FROM pvp_log WHERE happened_at < (SELECT start_date FROM maze_state WHERE season_id = ?)", (season_id,))

    # maze_map сезона
    cur.execute("DELETE FROM maze_map WHERE season_id = ?", (season_id,))
    cur.execute("DELETE FROM maze_meta WHERE season_id = ?", (season_id,))
    cur.execute("DELETE FROM maze_discovered WHERE season_id = ?", (season_id,))
    cur.execute("DELETE FROM fragment_finds WHERE season_id = ?", (season_id,))
    cur.execute("DELETE FROM gates_state WHERE season_id = ?", (season_id,))

    # Приглашения клана
    # (уже удалены)

    conn.commit()
    conn.close()

    logging.info(f"[SEASON] Cleaned up season {season_id}")


def start_new_season_if_needed() -> dict | None:
    """
    Проверить и запустить новый сезон.
    Возвращает статистику, если сезон завершён.
    """
    current = get_current_season()

    if not should_end_season(current):
        return None

    return end_season(current)


def get_season_info() -> dict:
    """Информация о текущем сезоне."""
    season = get_current_season()
    day = get_season_day(season)

    from core.maze_current import get_layers_unlocked
    layers = get_layers_unlocked(season)

    return {
        "season_id": season,
        "day": day,
        "days_left": max(0, SEASON_LENGTH_DAYS - day + 1),
        "total_days": SEASON_LENGTH_DAYS,
        "layers_unlocked": layers,
    }
