# tools/simulate_game.py
#
# Симуляция полного цикла игрока (без Telegram):
# - создание → intro → первый квест → работа → лабиринт → бой → смерть
# - проверка БД после каждого шага

import sys
import logging
from pathlib import Path
from datetime import timedelta

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.WARNING)

from core.i18n import load_locales, t
load_locales()

from db.connection import init_db, get_conn
from db.players import get_player, update_player_fields, get_lang
from core.time_utils import now

TEST_USER_ID = 999999999
TEST_NAME = "SimUser"


def log(step: str, ok: bool, detail: str = ""):
    status = "OK" if ok else "FAIL"
    print(f"[{step}] {status} {detail}")
    if not ok:
        raise SystemExit(f"FAIL at step: {step} — {detail}")


def cleanup_test_user():
    """Удалить тестового игрока и его данные."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        for table, col in [
            ("players", "user_id"), ("inventory", "user_id"),
            ("player_log", "user_id"), ("player_diary", "user_id"),
            ("player_buffs", "user_id"), ("player_titles", "user_id"),
            ("player_achievements", "user_id"), ("season_scores", "user_id"),
            ("npc_visits", "user_id"), ("starter_quest", "user_id"),
            ("dropped_diaries", "user_id"), ("memorial", "user_id"),
            ("maze_runs", "user_id"), ("active_combats", "user_id"),
            ("clan_members", "user_id"), ("clan_storage", "clan_id"),
        ]:
            try:
                cur.execute(f"DELETE FROM {table} WHERE {col} = ?", (TEST_USER_ID,))
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()


def step_1_init():
    init_db()
    log("1. init_db", True)


def step_2_create_player():
    from db.players import create_player
    from services.maps import create_personal_map
    from db.inventory import add_item
    from db.pvp import give_shield

    create_player(TEST_USER_ID, TEST_NAME.lower(), TEST_NAME, "ru", "center")
    create_personal_map(TEST_USER_ID, TEST_NAME)
    add_item(TEST_USER_ID, "key_1", 1)
    give_shield(TEST_USER_ID)

    p = get_player(TEST_USER_ID)
    log("2. create_player", p is not None, f"id={TEST_USER_ID}, loc={p['location'] if p else '?'}")


def step_3_intro():
    from db.inventory import add_item
    from content.intro_dialogs import STARTER_INVENTORY

    # Выбрать перк и профессию
    update_player_fields(TEST_USER_ID, {"perk": "truth", "profession": "engineer"})
    # Выдать стартовый инвентарь
    for item, qty in STARTER_INVENTORY.items():
        add_item(TEST_USER_ID, item, qty)
    # Инженеру — компас
    add_item(TEST_USER_ID, "compass", 1)
    # Завершить intro
    update_player_fields(TEST_USER_ID, {"intro_done": 1})

    p = get_player(TEST_USER_ID)
    log("3. intro (perk=truth, prof=engineer)", p["intro_done"] == 1)


def step_4_starter_quest():
    from services.starter_quest import start_starter_quest, get_starter_quest
    start_starter_quest(TEST_USER_ID)
    sq = get_starter_quest(TEST_USER_ID)
    log("4. starter_quest", sq is not None and sq["status"] == "active", f"status={sq['status'] if sq else '?'}")


def step_5_work():
    from services.work import start_work, collect_rewards, WorkError
    from db.players import update_player_fields as upf

    # Игрок в центре — перевести на фермы
    upf(TEST_USER_ID, {"location": "farms"})
    # Начать работу
    try:
        info = start_work(TEST_USER_ID, "farm")
    except WorkError as e:
        log("5. start_work", False, f"{e.key} {e.kwargs}")
        return
    # Ускорить: сдвинуть work_ends_at в прошлое
    p = get_player(TEST_USER_ID)
    upf(TEST_USER_ID, {"work_ends_at": now() - timedelta(seconds=1)})
    rewards = collect_rewards(TEST_USER_ID)
    log("5. work (farm + collect)", rewards is not None, f"rewards={rewards}")


def step_6_starter_complete():
    from services.starter_quest import complete_starter_quest, get_starter_quest
    bonus = complete_starter_quest(TEST_USER_ID)
    sq = get_starter_quest(TEST_USER_ID)
    ok = bonus is not None and sq["status"] == "complete"
    log("6. starter_quest complete", ok, f"bonus={bonus}, status={sq['status'] if sq else '?'}")


def step_7_enter_maze():
    from services.maze import enter_maze, MazeError
    from services.maze_runs import start_run

    # Перевести к воротам
    update_player_fields(TEST_USER_ID, {"location": "north_gates"})
    try:
        section = enter_maze(TEST_USER_ID, "north_gates")
    except MazeError as e:
        log("7. enter_maze", False, f"{e.key}")
        return
    update_player_fields(TEST_USER_ID, {"maze_layer": 1, "maze_section": section})
    start_run(TEST_USER_ID, layer=1, entry_section=section)
    log("7. enter_maze", True, f"section={section}")


def step_8_move():
    from services.maze_runs import move_in_run
    p = get_player(TEST_USER_ID)
    section = p["maze_section"]
    # Найти соседнюю секцию
    from db.maze_map import get_section
    from core.maze_current import get_current_season
    season = get_current_season()
    sec = get_section(season, 1, section)
    if not sec or not sec["exits"]:
        log("8. move", False, f"no exits from {section}")
        return
    target = sec["exits"][0]
    result = move_in_run(TEST_USER_ID, target)
    log("8. move", result.get("ok", False), f"{section} → {target}, depth={result.get('depth')}")


def step_9_combat():
    from services.combat import start_combat, player_attack, get_active_combat, give_victory_rewards
    p = get_player(TEST_USER_ID)
    section = p["maze_section"]
    start_combat(TEST_USER_ID, "young", section, 1)
    for i in range(20):
        result = player_attack(TEST_USER_ID)
        if result.get("victory"):
            give_victory_rewards(TEST_USER_ID, "young")
            log("9. combat (young, win)", True, f"after {i+1} hits")
            return
    log("9. combat", False, "no victory in 20 hits")


def step_10_death():
    from services.death import die_in_maze
    p = get_player(TEST_USER_ID)
    # Убить (HP=0) и вызвать die_in_maze
    update_player_fields(TEST_USER_ID, {"hp": 0})
    try:
        result = die_in_maze(TEST_USER_ID)
    except Exception as e:
        log("10. death", False, str(e))
        return
    p = get_player(TEST_USER_ID)
    ok = p["location"] == "center" and p["maze_layer"] == 0
    log("10. death + respawn", ok, f"loc={p['location']}, maze_layer={p['maze_layer']}, result={result}")


def main():
    print("=== SIMULATE GAME ===\n")
    cleanup_test_user()
    try:
        step_1_init()
        step_2_create_player()
        step_3_intro()
        step_4_starter_quest()
        step_5_work()
        step_6_starter_complete()
        step_7_enter_maze()
        step_8_move()
        step_9_combat()
        step_10_death()
        print("\n=== RESULT: ALL STEPS OK ===")
    except SystemExit as e:
        print(f"\n=== RESULT: FAIL — {e} ===")
        raise
    finally:
        # Не удаляем — оставим для проверки в БД
        pass


if __name__ == "__main__":
    main()
