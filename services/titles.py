# services/titles.py
#
# Проверка и выдача титулов.

from content.titles import TITLES
from db.connection import get_conn
from db.players import get_player


def _get_player_stats(user_id: int) -> dict:
    """Собрать статистику игрока (для проверки титулов)."""
    from core.maze_current import get_current_season
    season = get_current_season()

    conn = get_conn()
    try:
        cur = conn.cursor()

        # Season score (griever_kills, fragments, deaths)
        cur.execute("""
            SELECT griever_kills, fragments, deaths, keys_found
            FROM season_scores
            WHERE user_id = ? AND season_id = ?
        """, (user_id, season))
        row = cur.fetchone()
        score = dict(row) if row else {"griever_kills": 0, "fragments": 0, "deaths": 0, "keys_found": 0}

        # Teresa secrets (по COUNT npc_visits с npc_key='teresa')
        cur.execute("""
            SELECT COUNT(*) FROM npc_visits
            WHERE user_id = ? AND npc_key = 'teresa'
        """, (user_id,))
        teresa_visits = cur.fetchone()[0]
        # секрет показывается со 2-го визита, значит секретов = max(0, visits - 1)
        teresa_secrets = max(0, teresa_visits - 1)

        # work_done (COUNT player_log с event_type='work_done')
        cur.execute("""
            SELECT COUNT(*) FROM player_log
            WHERE user_id = ? AND event_type = 'work_done'
        """, (user_id,))
        work_done = cur.fetchone()[0]

    finally:
        conn.close()

    return {
        "griever_kills": score.get("griever_kills", 0) or 0,
        "fragments": score.get("fragments", 0) or 0,
        "deaths": score.get("deaths", 0) or 0,
        "keys_found": score.get("keys_found", 0) or 0,
        "teresa_secrets": teresa_secrets,
        "work_done": work_done,
    }


def get_player_titles(user_id: int) -> list[str]:
    """Список ключей титулов, которые есть у игрока."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT title_key FROM player_titles
            WHERE user_id = ?
        """, (user_id,))
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def check_new_titles(user_id: int) -> list[str]:
    """Проверить, какие новые титулы заслужил игрок. Выдать и вернуть."""
    stats = _get_player_stats(user_id)
    existing = set(get_player_titles(user_id))

    new_titles = []
    for title_key, spec in TITLES.items():
        if title_key in existing:
            continue
        cond = spec["condition"]
        ctype = cond["type"]
        need = cond["need"]
        have = stats.get(ctype, 0)
        if have >= need:
            # Выдать
            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR IGNORE INTO player_titles (user_id, title_key)
                    VALUES (?, ?)
                """, (user_id, title_key))
                conn.commit()
            finally:
                conn.close()

            # В журнал (important)
            try:
                from core.i18n import t
                from services.event_log import add_event, cleanup_old_events
                p = get_player(user_id)
                if p:
                    lang = p["language"]
                    add_event(user_id, "new_title",
                              t("title.new", lang, title=f"{spec['icon']} {t(spec['name_key'], lang)}"),
                              severity="important")
                    cleanup_old_events(user_id)
            except Exception:
                pass

            new_titles.append(title_key)

    return new_titles


def get_player_title_display(user_id: int, lang: str) -> str:
    """Строка титула для отображения (или пусто)."""
    from core.i18n import t
    titles = get_player_titles(user_id)
    if not titles:
        return ""
    # Берём самый «старший» титул — последний выданный
    last = titles[-1]
    spec = TITLES.get(last)
    if not spec:
        return ""
    return f"{spec['icon']} {t(spec['name_key'], lang)}"
