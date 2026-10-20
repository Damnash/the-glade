# services/work.py

from datetime import timedelta

from content.work import WORK_TYPES
from core.player_state import update_player_state
from services.event_log import add_event, cleanup_old_events
from core.time_utils import now, parse_dt, seconds_until
from db.players import get_player, update_player_fields


class WorkError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs


def available_works(player: dict) -> list[str]:
    """Доступные работы в локации. Ночью — только стража и смотровая."""
    from core.daycycle import is_night
    loc = player["location"]
    works = [k for k, v in WORK_TYPES.items() if loc in v["locations"]]
    if is_night():
        works = [w for w in works if w in ("guard", "watch")]
    return works


def start_work(user_id: int, work_type: str) -> dict:
    player = update_player_state(get_player(user_id))
    if not player:
        raise WorkError("start.need_start")

    if player["status"] == "sleeping":
        raise WorkError("work.sleeping")

    if player["status"] == "working":
        ends = parse_dt(player.get("work_ends_at"))
        left = seconds_until(ends)
        raise WorkError("work.already", time=left)

    if work_type not in WORK_TYPES:
        raise WorkError("work.unknown")

    spec = WORK_TYPES[work_type]
    if player["location"] not in spec["locations"]:
        raise WorkError("work.wrong_place")

    # Ночью — только стража и смотровая
    from core.daycycle import is_night
    if is_night() and work_type not in ("guard", "watch"):
        raise WorkError("work.night")

    if player["energy"] < spec["needs_energy"]:
        raise WorkError("work.tired", need=spec["needs_energy"], have=player["energy"])

    ends_at = now() + timedelta(seconds=spec["duration_sec"])

    update_player_fields(user_id, {
        "status": "working",
        "work_type": work_type,
        "work_ends_at": ends_at,
        "last_seen": now(),
        "energy": player["energy"] - spec["energy_cost"],
    })

    return {
        "work_type": work_type,
        "ends_at": ends_at,
        "duration": spec["duration_sec"],
        "rewards": spec["rewards"],
    }


def collect_rewards(user_id: int) -> dict | None:
    player = get_player(user_id)
    if not player or player["status"] != "working":
        return None

    ends_at = parse_dt(player.get("work_ends_at"))
    if not ends_at or now() < ends_at:
        return None

    work_type = player.get("work_type")
    spec = WORK_TYPES.get(work_type)
    if not spec:
        update_player_fields(user_id, {
            "status": "active",
            "work_type": None,
            "work_ends_at": None,
        })
        return None

    rewards = dict(spec["rewards"])

    # Бонус клана (ферма → больше еды)
    from services.bonuses import get_clan_bonus
    clan_bonus = get_clan_bonus(player)

    if work_type == "farm" and "food" in rewards:
        food_bonus = clan_bonus.get("food_bonus", 0)
        if food_bonus > 0:
            rewards["food"] = int(rewards["food"] * (1 + food_bonus))

    updates = {
        "status": "active",
        "work_type": None,
        "work_ends_at": None,
    }
    for key, amount in rewards.items():
        updates[key] = player.get(key, 0) + amount

    update_player_fields(user_id, updates)

    # Лог для главного меню (с наградой)
    try:
        from core.i18n import t
        def _fmt(rewards, lang):
            icons = {"food": "🍞", "tokens": "🪙", "water": "💧"}
            return ", ".join(f"{icons.get(k, k)} +{v}" for k, v in rewards.items())
        add_event(
            user_id, "work_done",
            t("log.work_done", player["language"], rewards=_fmt(rewards, player["language"])),
            severity="chat",
        )
        cleanup_old_events(user_id)

        # Автодневник
        try:
            from services.diary import add_diary_auto
            add_diary_auto(user_id, "work_done",
                           work=t(f"work.{work_type}", player["language"]),
                           rewards=_fmt(rewards, player["language"]))
        except Exception:
            pass
    except Exception:
        pass

    return rewards
