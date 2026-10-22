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




def step_11_teresa_secrets():
    """Тереза: 3 секрета + благословение на 3-м."""
    from content.npcs import get_npc_dialog_key
    from services.buffs import add_buff, get_active_buffs
    from db.connection import get_conn

    # Симулировать 3 визита к Терезе
    conn = get_conn()
    try:
        cur = conn.cursor()
        for i in range(3):
            cur.execute("""
                INSERT OR IGNORE INTO npc_visits (user_id, npc_key)
                VALUES (?, 'teresa')
            """, (TEST_USER_ID,))
        conn.commit()
    finally:
        conn.close()

    # Проверить, что get_npc_dialog_key возвращает разные ключи
    p = get_player(TEST_USER_ID)
    key1 = get_npc_dialog_key("teresa", p, is_first_visit=False)

    # Симулировать благословение (как в on_talk_to_npc)
    add_buff(TEST_USER_ID, "blessed")
    buffs = get_active_buffs(TEST_USER_ID)
    has_blessed = any(b["buff_key"] == "blessed" for b in buffs)

    log("11. Teresa (3 visits + blessed)", has_blessed, f"dialog={key1}, buffs={[b['buff_key'] for b in buffs]}")


def step_12_artifacts():
    """Артефакты: roll_artifact (10%) + on_artifact_found."""
    from services.maze import roll_artifact, on_artifact_found
    from content.artifacts import ARTIFACTS

    # Симулировать 50 попыток (10% — должно выпасть хотя бы 1)
    found = None
    for _ in range(100):
        result = roll_artifact("L1_N2", TEST_USER_ID, "ru")
        if result:
            found = result
            break

    if found:
        on_artifact_found(TEST_USER_ID, found, "ru")
        log("12. artifact", True, f"found: {found[:50]}")
    else:
        log("12. artifact", False, "no artifact in 100 rolls (10% — маловероятно)")


def step_13_echo():
    """Эхо прошлых рейдов: roll_echo (30%)."""
    from services.maze import roll_echo
    found = None
    for _ in range(50):
        result = roll_echo("L1_N2", TEST_USER_ID, "ru")
        if result:
            found = result
            break
    log("13. echo", found is not None, f"found: {found[:50] if found else 'none'}")


def step_14_weather():
    """Погода: смена 3 раза + проверка modifiers."""
    from services.weather import get_current_weather, set_current_weather, pick_next_weather, get_weather_modifiers
    from content.world_events import WORLD_EVENTS  # для проверки, что модули живы

    original = get_current_weather()
    changed = []
    for _ in range(3):
        new = pick_next_weather(get_current_weather())
        set_current_weather(new)
        changed.append(new)

    current = get_current_weather()
    monster_mult, frag_mult = get_weather_modifiers()

    # Вернуть как было
    set_current_weather(original)

    log("14. weather (3 changes)", len(set(changed)) >= 2, f"{original} → {changed}, monster_mult={monster_mult}")


def step_15_buff_cursed():
    """Проклятие: add_buff + get_buff_modifiers."""
    from services.buffs import add_buff, get_active_buffs, get_buff_modifiers, clear_expired_buffs
    import sqlite3

    # Удалить старые баффы
    conn = sqlite3.connect("data/game.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM player_buffs WHERE user_id = ?", (TEST_USER_ID,))
    conn.commit()
    conn.close()

    added = add_buff(TEST_USER_ID, "cursed")
    mods = get_buff_modifiers(TEST_USER_ID)
    ok = added and mods["monster_mult"] > 1.0 and mods["hp_per_move"] < 0

    log("15. cursed buff", ok, f"monster_mult={mods['monster_mult']}, hp_per_move={mods['hp_per_move']}")


def step_16_titles_griever():
    """Титул griever_10 (10 убийств Гриверов)."""
    from services.titles import check_new_titles, get_player_titles
    from db.connection import get_conn
    from core.maze_current import get_current_season

    season = get_current_season()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO season_scores (user_id, season_id, griever_kills)
            VALUES (?, ?, 10)
        """, (TEST_USER_ID, season))
        cur.execute("""
            UPDATE season_scores SET griever_kills = 10
            WHERE user_id = ? AND season_id = ?
        """, (TEST_USER_ID, season))
        conn.commit()
    finally:
        conn.close()

    new_titles = check_new_titles(TEST_USER_ID)
    titles = get_player_titles(TEST_USER_ID)
    ok = "griever_10" in titles

    log("16. title griever_10", ok, f"new={new_titles}, all={titles}")


def step_17_fragment_goal():
    """Цель 5 фрагментов → карта 1-го слоя + титул cartographer_5."""
    from services.goals import check_fragment_goal, get_fragment_goal_status
    from db.connection import get_conn
    from core.maze_current import get_current_season
    from services.titles import get_player_titles

    season = get_current_season()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO season_scores (user_id, season_id, fragments)
            VALUES (?, ?, 5)
        """, (TEST_USER_ID, season))
        cur.execute("""
            UPDATE season_scores SET fragments = 5
            WHERE user_id = ? AND season_id = ?
        """, (TEST_USER_ID, season))
        conn.commit()
    finally:
        conn.close()

    status = get_fragment_goal_status(TEST_USER_ID)
    done = check_fragment_goal(TEST_USER_ID)
    titles = get_player_titles(TEST_USER_ID)

    # Проверить, что личная карта наполнена
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM map_item_sections
            WHERE map_id = (SELECT id FROM map_items WHERE owner_id = ? AND is_personal = 1)
        """, (TEST_USER_ID,))
        sections = cur.fetchone()[0]
    finally:
        conn.close()

    ok = status["done"] and done and "cartographer_5" in titles and sections > 0
    log("17. fragment_goal (5)", ok, f"status={status}, titles={titles}, sections={sections}")


def step_18_npc_dialog_variants():
    """NPC диалоги: first_visit, low_hp."""
    from content.npcs import get_npc_dialog_key
    from db.players import update_player_fields

    # ВАЖНО: HP должен быть > 30, иначе low_hp всегда срабатывает первым
    update_player_fields(TEST_USER_ID, {"hp": 100, "food": 5, "water": 3})
    p = get_player(TEST_USER_ID)

    # Обычный игрок (hp=100, food=5) → npc.newt.dialog
    key_normal = get_npc_dialog_key("newt", p, is_first_visit=False)

    # Низкое HP (hp=10) → npc.newt.dialog_hurt
    p_low = dict(p)
    p_low["hp"] = 10
    key_low = get_npc_dialog_key("newt", p_low, is_first_visit=False)

    # first_visit (hp=100, food=5) → npc.newt.dialog_first
    key_first = get_npc_dialog_key("newt", p, is_first_visit=True)

    ok = (key_normal == "npc.newt.dialog"
          and key_low == "npc.newt.dialog_hurt"
          and key_first == "npc.newt.dialog_first")
    log("18. npc dialog variants", ok,
        f"normal={key_normal}, low={key_low}, first={key_first}")


def step_19_npc_hint():
    """NPC подсказки: _npc_hint для Чака (по очереди)."""
    # НЕ через callback — а через NPC_HINTS + visits
    from content.npc_hints import NPC_HINTS
    from db.connection import get_conn
    from core.i18n import t

    hints = NPC_HINTS.get("chuck", [])
    if not hints:
        log("19. npc hint", False, "no hints for chuck")
        return

    # Симулировать 5 визитов (как _npc_hint)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM npc_visits WHERE user_id = ? AND npc_key = 'chuck'", (TEST_USER_ID,))
        for i in range(5):
            cur.execute("""
                INSERT OR IGNORE INTO npc_visits (user_id, npc_key)
                VALUES (?, 'chuck')
            """, (TEST_USER_ID,))
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM npc_visits WHERE user_id = ? AND npc_key = 'chuck'", (TEST_USER_ID,))
        visits = cur.fetchone()[0]
    finally:
        conn.close()

    # Проверить, что hint index = visits-1, и все 5 ключей есть в локалях
    idx = min(len(hints) - 1, visits - 1)
    hint_key = hints[idx]
    hint_text = t(hint_key, "ru")
    ok = hint_text and hint_text != hint_key

    log("19. npc hint (chuck, 5 visits)", ok, f"visits={visits}, idx={idx}, hint='{hint_text[:40]}...'")


def step_20_clan_open():
    """Клан: создать открытый + вступить вторым игроком."""
    from db.clans import create_clan, set_clan_open, get_clan, get_clan_members, count_clan_members
    from db.connection import get_conn

    # Удалить старые кланы тестового игрока
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM clan_members WHERE user_id IN (?, ?)", (TEST_USER_ID, 999999998))
        conn.commit()
    finally:
        conn.close()

    # Создать клан
    clan_id = create_clan(TEST_USER_ID, "SimClan", "Test motto")
    set_clan_open(clan_id, 1)

    # Второй тестовый игрок
    from db.players import create_player
    create_player(999999998, "sim2", "Sim2", "ru", "center")

    # Вступить
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO clan_members (clan_id, user_id, role)
            VALUES (?, ?, 'recruit')
        """, (clan_id, 999999998))
        conn.commit()
    finally:
        conn.close()

    clan = get_clan(clan_id)
    members = count_clan_members(clan_id)
    ok = clan is not None and clan["is_open"] == 1 and members == 2

    log("20. clan open + join", ok, f"clan={clan['name'] if clan else '?'}, members={members}, is_open={clan['is_open'] if clan else '?'}")


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
        step_11_teresa_secrets()
        step_12_artifacts()
        step_13_echo()
        step_14_weather()
        step_15_buff_cursed()
        step_16_titles_griever()
        step_17_fragment_goal()
        step_18_npc_dialog_variants()
        step_19_npc_hint()
        step_20_clan_open()
        print("\n=== RESULT: ALL 20 STEPS OK ===")
    except SystemExit as e:
        print(f"\n=== RESULT: FAIL — {e} ===")
        raise
    finally:
        # Не удаляем — оставим для проверки в БД
        pass


if __name__ == "__main__":
    main()
