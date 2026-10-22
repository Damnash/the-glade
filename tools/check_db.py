# tools/check_db.py
#
# Проверка БД: все таблицы, все колонки, консистентность игроков, кланов, титулов.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.connection import get_conn, init_db


# Ожидаемые таблицы
EXPECTED_TABLES = {
    "players", "inventory", "maze_map", "maze_meta", "maze_state",
    "whispers", "radios", "radio_messages", "freq_messages",
    "maze_discovered", "fragment_finds", "map_items", "map_item_sections",
    "map_shares", "items_on_ground", "active_combats", "season_keys",
    "player_quests", "maze_runs", "clans", "clan_members", "clan_invites",
    "clan_messages", "clan_map_sections", "clan_storage", "clan_upgrades",
    "player_shields", "pvp_flags", "duels", "pvp_log", "steal_cooldowns",
    "player_achievements", "season_scores", "hall_of_fame", "gates_state",
    "player_log", "system_state", "daily_quests", "story_quests",
    "story_stages", "player_diary", "npc_visits", "player_titles",
    "player_buffs", "memorial", "starter_quest", "dropped_diaries",
}

# Ожидаемые колонки (после миграций)
EXPECTED_COLUMNS = {
    "players": {"fragment_goal_done", "main_message_id", "current_session", "intro_done"},
    "player_log": {"severity"},
    "season_keys": {"spawned_date"},
}


def main():
    print("=== DB CHECK ===\n")

    init_db()  # убедимся, что все миграции применены

    conn = get_conn()
    cur = conn.cursor()

    # 1. Таблицы
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = {r[0] for r in cur.fetchall()}
    missing_tables = EXPECTED_TABLES - existing
    print(f"Tables: {len(existing)} (expected {len(EXPECTED_TABLES)})")
    if missing_tables:
        print(f"  MISSING TABLES: {sorted(missing_tables)}")
    else:
        print("  all expected tables present: OK")

    # 2. Колонки
    for table, expected_cols in EXPECTED_COLUMNS.items():
        cur.execute(f"PRAGMA table_info({table})")
        cols = {r[1] for r in cur.fetchall()}
        missing = expected_cols - cols
        if missing:
            print(f"  MISSING COLUMNS in {table}: {sorted(missing)}")

    # 3. Игроки
    cur.execute("SELECT user_id, display_name, intro_done, current_session, main_message_id FROM players")
    players = cur.fetchall()
    print(f"\nPlayers: {len(players)}")
    problems = 0
    for p in players:
        uid, name, intro, sess, msg = p["user_id"], p["display_name"], p["intro_done"], p["current_session"], p["main_message_id"]
        if intro and not sess:
            print(f"  WARN: {name} (id={uid}) intro_done=1, but session=None")
            problems += 1
        if not intro:
            print(f"  INFO: {name} (id={uid}) intro_done=0 (не завершил intro)")

    # 4. Кланы — у каждого должен быть лидер
    cur.execute("SELECT clan_id, name, leader_id FROM clans")
    clans = cur.fetchall()
    print(f"\nClans: {len(clans)}")
    for c in clans:
        cur.execute("SELECT role FROM clan_members WHERE clan_id = ? AND user_id = ?", (c["clan_id"], c["leader_id"]))
        row = cur.fetchone()
        if not row or row["role"] != "leader":
            print(f"  FAIL: clan {c['name']} (id={c['clan_id']}) — leader {c['leader_id']} not in members or wrong role")
            problems += 1
        else:
            print(f"  OK: {c['name']} (leader={c['leader_id']})")

    # 5. Титулы — ключи должны быть в TITLES
    from content.titles import TITLES
    cur.execute("SELECT user_id, title_key FROM player_titles")
    titles = cur.fetchall()
    print(f"\nPlayer titles: {len(titles)}")
    for t in titles:
        if t["title_key"] not in TITLES:
            print(f"  FAIL: unknown title_key '{t['title_key']}' for user {t['user_id']}")
            problems += 1

    # 6. Баффы — истёкшие можно удалить
    cur.execute("SELECT user_id, buff_key, expires_at FROM player_buffs")
    buffs = cur.fetchall()
    print(f"\nPlayer buffs (all): {len(buffs)}")
    from core.time_utils import now, parse_dt
    active = 0
    for b in buffs:
        exp = parse_dt(b["expires_at"])
        if exp and exp > now():
            active += 1
    print(f"  active: {active}")

    # 7. Мемориал
    cur.execute("SELECT COUNT(*) FROM memorial")
    print(f"\nMemorial: {cur.fetchone()[0]}")

    # 8. Dropped diaries
    cur.execute("SELECT COUNT(*) FROM dropped_diaries")
    print(f"Dropped diaries: {cur.fetchone()[0]}")

    # 9. Daily quests (активные)
    cur.execute("SELECT COUNT(*) FROM daily_quests WHERE status = 'active'")
    print(f"Active daily quests: {cur.fetchone()[0]}")

    # 10. Starter quests (активные)
    cur.execute("SELECT COUNT(*) FROM starter_quest WHERE status = 'active'")
    print(f"Active starter quests: {cur.fetchone()[0]}")

    conn.close()

    print(f"\n=== RESULT: {'OK' if problems == 0 else f'{problems} problems'} ===")
    sys.exit(0 if problems == 0 else 1)


if __name__ == "__main__":
    main()
