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




def step_21_pvp_flag():
    """PvP-флаг: set, has, clear."""
    from db.pvp import set_pvp_flag, has_pvp_flag, clear_pvp_flag, get_pvp_flag_time_left

    set_pvp_flag(TEST_USER_ID)
    has = has_pvp_flag(TEST_USER_ID)
    left = get_pvp_flag_time_left(TEST_USER_ID)
    clear_pvp_flag(TEST_USER_ID)
    has_after = has_pvp_flag(TEST_USER_ID)

    ok = has and left > 0 and not has_after
    log("21. pvp flag (set/has/clear)", ok, f"has={has}, left={left}s, after_clear={has_after}")


def step_22_pvp_attack():
    """PvP-атака: attack_player (урон по жертве)."""
    from db.pvp import set_pvp_flag
    from services.pvp import attack_player, PvPError
    from db.players import get_player as gp, update_player_fields as upf

    # Оба в центре, оба с PvP-флагом
    upf(TEST_USER_ID, {"location": "center", "hp": 100})
    upf(999999998, {"location": "center", "hp": 100})
    set_pvp_flag(TEST_USER_ID)
    set_pvp_flag(999999998)

    victim = gp(999999998)
    victim_name = victim["username"] or victim["display_name"]

    # Симулировать: игрок должен быть в PvP-зоне (центр лабиринта, а не Глэйда)
    # is_pvp_zone проверяет maze_layer > 0 → надо обоих в лабиринт
    upf(TEST_USER_ID, {"maze_layer": 1, "maze_section": "L1_N1"})
    upf(999999998, {"maze_layer": 1, "maze_section": "L1_N1"})

    try:
        result = attack_player(TEST_USER_ID, victim_name)
        ok = result["damage"] > 0 and result["victim_id"] == 999999998
        log("22. pvp attack", ok, f"dmg={result['damage']}, victim_hp={result['victim_hp']}")
    except PvPError as e:
        log("22. pvp attack", False, f"{e.key} {e.kwargs}")


def step_23_pvp_duel():
    """PvP-дуэль: challenge + accept (через services)."""
    from services.pvp import challenge_duel, resolve_duel, PvPError
    from db.players import get_player as gp, update_player_fields as upf
    import random

    # Ставка 0
    victim = gp(999999998)
    victim_name = victim["username"] or victim["display_name"]

    try:
        result = challenge_duel(TEST_USER_ID, victim_name, stake=0)
        duel_id = result["duel_id"]

        # Случайный победитель (как в handler)
        winner_id = random.choice([TEST_USER_ID, 999999998])
        resolve = resolve_duel(duel_id, winner_id)

        ok = resolve["stake"] == 0
        log("23. duel (challenge+resolve)", ok, f"winner={resolve['winner_name']}, stake={resolve['stake']}")
    except PvPError as e:
        log("23. duel", False, f"{e.key} {e.kwargs}")


def step_24_clan_chat():
    """Клан-чат: send_clan_message (2 участника)."""
    from services.clans import send_clan_message, ClanError
    from db.clans import get_player_clan

    clan = get_player_clan(TEST_USER_ID)
    if not clan:
        log("24. clan chat", False, "no clan")
        return

    try:
        result = send_clan_message(TEST_USER_ID, "Привет, клан!")
        ok = len(result["recipients"]) >= 1 and result["text"] == "Привет, клан!"
        log("24. clan chat", ok, f"recipients={result['recipients']}, text={result['text'][:20]}")
    except ClanError as e:
        log("24. clan chat", False, f"{e.key}")


def step_25_npc_bring_meat():
    """NPC сдать мясо: bring_to_npc (с активным квестом)."""
    from services.daily_quests import ensure_today_quest, get_today_quest
    from db.connection import get_conn
    from services.npc_actions import bring_to_npc, NPCActionError
    from db.inventory import add_item
    from db.players import update_player_fields as upf

    # Принудительно взять квест bring_meat_3
    today = __import__("datetime").datetime.utcnow().date().isoformat()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM daily_quests WHERE user_id = ? AND quest_date = ?", (TEST_USER_ID, today))
        cur.execute("""
            INSERT INTO daily_quests (user_id, quest_date, quest_key, progress, need, status)
            VALUES (?, ?, 'bring_meat_3', 0, 3, 'active')
        """, (TEST_USER_ID, today))
        conn.commit()
    finally:
        conn.close()

    # Дать 1 мясо
    add_item(TEST_USER_ID, "meat", 1)

    try:
        result = bring_to_npc(TEST_USER_ID, "frypan", "meat", 1)
        ok = result["ok"] and result["progress_updated"]
        log("25. npc bring meat", ok, f"progress_updated={result['progress_updated']}, completed={result['quest_completed']}")
    except NPCActionError as e:
        log("25. npc bring meat", False, f"{e.key} {e.kwargs}")


def step_26_daily_quest_complete():
    """Daily quest: complete через try_complete (награда)."""
    from services.daily_quests import get_today_quest, try_complete, add_progress
    from db.connection import get_conn
    from datetime import datetime

    today = datetime.utcnow().date().isoformat()

    # Установить квест complete
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM daily_quests WHERE user_id = ? AND quest_date = ?", (TEST_USER_ID, today))
        cur.execute("""
            INSERT INTO daily_quests (user_id, quest_date, quest_key, progress, need, status)
            VALUES (?, ?, 'kill_griever_1', 1, 1, 'complete')
        """, (TEST_USER_ID, today))
        conn.commit()
    finally:
        conn.close()

    from db.players import get_player, update_player_fields as upf
    p = get_player(TEST_USER_ID)
    tokens_before = p["tokens"]

    result = try_complete(TEST_USER_ID)
    p = get_player(TEST_USER_ID)
    ok = result is not None and p["tokens"] > tokens_before

    log("26. daily quest complete", ok,
        f"reward={result['reward'] if result else None}, tokens {tokens_before} → {p['tokens']}")


def step_27_radio():
    """Радио: send_on_frequency + get_freq_history."""
    from services.radio import get_radio, send_on_frequency, get_freq_history
    from db.players import update_player_fields as upf

    upf(TEST_USER_ID, {"location": "center"})
    radio = get_radio(TEST_USER_ID)
    if not radio["is_on"]:
        from services.radio import toggle_radio
        toggle_radio(TEST_USER_ID)

    result = send_on_frequency(TEST_USER_ID, "Тест радио")
    history = get_freq_history(result["frequency"], limit=5)
    ok = any(m["text"] == "Тест радио" for m in history)

    log("27. radio (send + history)", ok,
        f"freq={result['frequency']}, listeners={len(result['listeners'])}, history_len={len(history)}")


def step_28_whisper():
    """Шёпот: send_whisper (оба в центре)."""
    from services.whisper import send_whisper, get_unread_whispers, mark_whispers_read
    from db.players import get_player as gp, update_player_fields as upf

    upf(TEST_USER_ID, {"location": "center"})
    upf(999999998, {"location": "center"})

    target = gp(999999998)
    target_name = target["username"] or target["display_name"]

    try:
        result = send_whisper(TEST_USER_ID, target_name, "Тайное сообщение")
        unread = get_unread_whispers(999999998)
        ok = len(unread) >= 1
        log("28. whisper", ok,
            f"to={result['to_name']}, unread={len(unread)}")
        mark_whispers_read(999999998)
    except Exception as e:
        log("28. whisper", False, str(e))


def step_29_say():
    """Say: add_event в локации (2 участника)."""
    from services.event_log import add_event, get_recent_events
    from db.players import get_player as gp, update_player_fields as upf

    upf(TEST_USER_ID, {"location": "center"})
    upf(999999998, {"location": "center"})

    # Симулировать: add_event для получателя
    add_event(999999998, "say_received", "💬 SimUser: Привет", severity="chat")
    events = get_recent_events(999999998, limit=5, severity="chat")
    ok = any("Привет" in e["text"] for e in events)

    log("29. say (event_log)", ok, f"events={[e['text'][:30] for e in events]}")


def step_30_gates_final():
    """Финал: 5 ключей → try_open_gates (в центре)."""
    from services.achievements import try_open_gates
    from db.players import get_player as gp, update_player_fields as upf
    from db.keys import has_player_key
    from core.maze_current import get_current_season

    season = get_current_season()

    # Оба в центре лабиринта
    upf(TEST_USER_ID, {"maze_layer": 1, "maze_section": "L1_C"})
    upf(999999998, {"maze_layer": 1, "maze_section": "L1_C"})

    # Выдать 5 ключей обоим через season_keys
    from db.connection import get_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        for uid in (TEST_USER_ID, 999999998):
            for num in (1, 2, 3, 4, 5):
                cur.execute("""
                    INSERT OR IGNORE INTO season_keys
                    (season_id, key_number, layer, section_id, wing, found_by)
                    VALUES (?, ?, 1, 'L1_C', 'C', ?)
                """, (season, num, uid))
        conn.commit()
    finally:
        conn.close()

    # try_open_gates: need tier players_at_gates. Пока 2 игрока, tier tiny → 1
    result = try_open_gates(TEST_USER_ID)
    # Может быть None, если gates уже открыты, или если не хватает игроков
    if result:
        ok = len(result["winners"]) >= 1
        log("30. gates open (final)", ok, f"winners={result['winners']}")
    else:
        # Проверить, что gates открыты или уже открывались
        from services.achievements import get_gates_info
        info = get_gates_info()
        ok = info["is_open"]
        log("30. gates (already open or no winners)", ok, f"is_open={info['is_open']}")


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
        step_21_pvp_flag()
        step_22_pvp_attack()
        step_23_pvp_duel()
        step_24_clan_chat()
        step_25_npc_bring_meat()
        step_26_daily_quest_complete()
        step_27_radio()
        step_28_whisper()
        step_29_say()
        step_30_gates_final()
        print("\n=== RESULT: ALL 30 STEPS OK ===")
    except SystemExit as e:
        print(f"\n=== RESULT: FAIL — {e} ===")
        raise
    finally:
        # Не удаляем — оставим для проверки в БД
        pass


if __name__ == "__main__":
    main()
