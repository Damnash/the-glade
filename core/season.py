# core/season.py

from datetime import datetime, timedelta

from db.connection import get_conn


# Тиры сезона
TIERS = {
    "tiny": {
        "min": 1, "max": 5,
        "sections": 12, "fragments": 8, "keys": 2,
        "players_at_gates": 1, "pvp": False,
        "hp": 40, "energy": 30,
        "food": 2, "water": 1, "torches": 1, "rope": 0,
    },
    "small": {
        "min": 6, "max": 15,
        "sections": 25, "fragments": 16, "keys": 3,
        "players_at_gates": 2, "pvp": True,
        "hp": 50, "energy": 40,
        "food": 3, "water": 2, "torches": 2, "rope": 1,
    },
    "medium": {
        "min": 16, "max": 30,
        "sections": 37, "fragments": 25, "keys": 4,
        "players_at_gates": 3, "pvp": True,
        "hp": 60, "energy": 50,
        "food": 4, "water": 2, "torches": 2, "rope": 1,
    },
    "large": {
        "min": 31, "max": 60,
        "sections": 62, "fragments": 40, "keys": 5,
        "players_at_gates": 5, "pvp": True,
        "hp": 70, "energy": 60,
        "food": 5, "water": 3, "torches": 3, "rope": 2,
    },
    "epic": {
        "min": 61, "max": 10**9,
        "sections": 80, "fragments": 55, "keys": 5,
        "players_at_gates": 7, "pvp": True,
        "hp": 80, "energy": 70,
        "food": 6, "water": 3, "torches": 3, "rope": 2,
    },
}


def get_active_players_count() -> int:
    """Игроки, заходившие за последние 7 дней."""
    conn = get_conn()
    cur = conn.cursor()
    cutoff = datetime.utcnow() - timedelta(days=7)
    cur.execute(
        "SELECT COUNT(*) FROM players WHERE last_seen >= ?",
        (cutoff,),
    )
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_current_tier() -> str:
    active = get_active_players_count()
    for tier_name, spec in TIERS.items():
        if spec["min"] <= active <= spec["max"]:
            return tier_name
    return "tiny"


def get_tier_config() -> dict:
    return TIERS[get_current_tier()]