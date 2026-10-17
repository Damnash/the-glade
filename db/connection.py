# db/connection.py

import os
import sqlite3

from config import DB_PATH


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    # WAL: читатели и писатель не блокируют друг друга
    conn.execute("PRAGMA journal_mode=WAL")
    # busy_timeout: ждать до 10 сек, если БД заблокирована
    conn.execute("PRAGMA busy_timeout=10000")
    # synchronous=NORMAL: быстрее, безопасно с WAL
    conn.execute("PRAGMA synchronous=NORMAL")
    # foreign_keys: включить
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            display_name TEXT,
            language TEXT DEFAULT 'en',
            location TEXT DEFAULT 'center',
            status TEXT DEFAULT 'active',
            hp INTEGER DEFAULT 100,
            sanity INTEGER DEFAULT 100,
            max_food INTEGER DEFAULT 10,
            max_water INTEGER DEFAULT 5,
            energy INTEGER DEFAULT 100,
            food INTEGER DEFAULT 0,
            water INTEGER DEFAULT 0,
            tokens INTEGER DEFAULT 0,
            work_type TEXT,
            work_ends_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_action TIMESTAMP,
            last_fed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_drank_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_sanity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            main_message_id INTEGER,
            profession TEXT,
            perk TEXT,
            intro_done INTEGER DEFAULT 0,
            current_session TEXT,
            maze_layer INTEGER DEFAULT 0,
            maze_section TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_key TEXT,
            quantity INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, item_key)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS maze_map (
            season_id INTEGER,
            layer INTEGER,
            section_id TEXT,
            name TEXT,
            wing TEXT,
            ring INTEGER,
            section_type TEXT,
            exits TEXT,
            PRIMARY KEY (season_id, layer, section_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS maze_meta (
            season_id INTEGER,
            layer INTEGER,
            key TEXT,
            value TEXT,
            PRIMARY KEY (season_id, layer, key)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS maze_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_id INTEGER UNIQUE,
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            layers_unlocked INTEGER DEFAULT 1,
            keys_collected TEXT DEFAULT '[]',
            fragments_collected INTEGER DEFAULT 0,
            gates_opened INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS maze_map (
            season_id INTEGER,
            layer INTEGER,
            section_id TEXT,
            name TEXT,              -- ← новое
            wing TEXT,
            ring INTEGER,
            section_type TEXT,
            exits TEXT,
            PRIMARY KEY (season_id, layer, section_id)
        )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS whispers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_id INTEGER,
        to_id INTEGER,
        text TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        read_at TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS radios (
        user_id INTEGER PRIMARY KEY,
        frequency REAL DEFAULT 433.075,
        is_on INTEGER DEFAULT 1,
        has_radio INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS radio_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            display_name TEXT,
            text TEXT,
            encrypted_for INTEGER,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS freq_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            frequency REAL,
            user_id INTEGER,
            display_name TEXT,
            text TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS maze_discovered (
            season_id INTEGER,
            layer INTEGER,
            section_id TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            discovered_by INTEGER,
            PRIMARY KEY (season_id, layer, section_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fragment_finds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_id INTEGER,
            user_id INTEGER,
            section_id TEXT,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_fragment_finds_date
            ON fragment_finds(found_at)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS map_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            owner_id INTEGER,
            creator_id INTEGER,
            is_personal INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_location TEXT,
            current_layer INTEGER,
            dropped_at TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_map_owner ON map_items(owner_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_map_location
            ON map_items(current_location, current_layer)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS map_item_sections (
            map_id INTEGER,
            season_id INTEGER,
            layer INTEGER,
            section_id TEXT,
            custom_name TEXT,
            note TEXT,
            drawn_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (map_id, season_id, layer, section_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS map_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            map_id INTEGER,
            from_id INTEGER,
            to_id INTEGER,
            shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            copied INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_share_to ON map_shares(to_id, expires_at)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS items_on_ground (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_key TEXT,
            quantity INTEGER DEFAULT 1,
            section_id TEXT,
            layer INTEGER,
            dropped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ground_location
            ON items_on_ground(section_id, layer, dropped_at)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS active_combats (
            user_id INTEGER PRIMARY KEY,
            monster_type TEXT,
            monster_hp INTEGER,
            monster_max_hp INTEGER,
            section_id TEXT,
            layer INTEGER,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS season_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_id INTEGER,
            key_number INTEGER,
            layer INTEGER,
            section_id TEXT,
            wing TEXT,
            found_by INTEGER,
            found_at TIMESTAMP,
            duplicate_of INTEGER,
            spawned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_keys_season
            ON season_keys(season_id, key_number, found_by)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            quest_key TEXT,
            progress INTEGER DEFAULT 0,
            need INTEGER,
            status TEXT DEFAULT 'active',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_quests_user
            ON player_quests(user_id, status)
    """)

    # ============ maze_runs (v1) ============
    # Запись на вылазку в Лабиринт: один run = одна вылазка.
    # Переходы мгновенные, но таймер ends_at ограничивает время в Лабиринте.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS maze_runs (
            user_id INTEGER PRIMARY KEY,
            layer INTEGER NOT NULL,
            current_section TEXT NOT NULL,
            entry_section TEXT NOT NULL,
            depth INTEGER DEFAULT 0,
            started_at TIMESTAMP NOT NULL,
            ends_at TIMESTAMP NOT NULL
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_maze_runs_ends
            ON maze_runs(ends_at)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clans (
            clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            leader_id INTEGER NOT NULL,
            motto TEXT,
            treasury INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_open INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clan_members (
            clan_id INTEGER,
            user_id INTEGER,
            role TEXT DEFAULT 'recruit',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (clan_id, user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clan_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clan_id INTEGER,
            from_id INTEGER,
            to_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clan_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clan_id INTEGER,
            user_id INTEGER,
            display_name TEXT,
            text TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clan_map_sections (
            clan_id INTEGER,
            season_id INTEGER,
            layer INTEGER,
            section_id TEXT,
            contributed_by INTEGER,
            custom_name TEXT,
            note TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (clan_id, season_id, layer, section_id)
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_clan_members_user ON clan_members(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_clan_invites_to ON clan_invites(to_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_clan_messages_clan ON clan_messages(clan_id, sent_at)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_shields (
            user_id INTEGER PRIMARY KEY,
            expires_at TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS duels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenger_id INTEGER,
            opponent_id INTEGER,
            stake_tokens INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pvp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            killer_id INTEGER,
            victim_id INTEGER,
            action TEXT,
            section_id TEXT,
            layer INTEGER,
            tokens_gained INTEGER DEFAULT 0,
            items_gained INTEGER DEFAULT 0,
            happened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS steal_cooldowns (
            user_id INTEGER PRIMARY KEY,
            last_steal TIMESTAMP
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_pvp_killer ON pvp_log(killer_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pvp_victim ON pvp_log(victim_id)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_achievements (
            user_id INTEGER,
            achievement_key TEXT,
            earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            season_id INTEGER,
            PRIMARY KEY (user_id, achievement_key)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS season_scores (
            user_id INTEGER,
            season_id INTEGER,
            score INTEGER DEFAULT 0,
            kills INTEGER DEFAULT 0,
            griever_kills INTEGER DEFAULT 0,
            fragments INTEGER DEFAULT 0,
            keys_found INTEGER DEFAULT 0,
            deaths INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, season_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hall_of_fame (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_id INTEGER,
            user_id INTEGER,
            display_name TEXT,
            achievement_key TEXT,
            achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS gates_state (
            season_id INTEGER PRIMARY KEY,
            opened_at TIMESTAMP,
            opened_by INTEGER,
            winner_ids TEXT
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_scores_season ON season_scores(season_id, score DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hall_season ON hall_of_fame(season_id)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_type TEXT,
            text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_log_user ON player_log(user_id, created_at DESC)")

    # Migration v0.2 → v1: удалить устаревшую таблицу maze_moves
    cur.execute("DROP TABLE IF EXISTS maze_moves")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS story_quests (
            user_id INTEGER,
            quest_key TEXT,
            status TEXT DEFAULT 'available',
            progress INTEGER DEFAULT 0,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            PRIMARY KEY (user_id, quest_key)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS story_stages (
            user_id INTEGER,
            stage_key TEXT,
            status TEXT DEFAULT 'locked',
            unlocked_at TIMESTAMP,
            PRIMARY KEY (user_id, stage_key)
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_story_user ON story_quests(user_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stages_user ON story_stages(user_id, status)")

    conn.commit()
    conn.close()












