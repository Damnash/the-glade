# core/daycycle.py

from core.time_utils import now


PHASES = {
    "dawn":  {"start": 6,  "end": 9,  "key": "time.phase.dawn",  "icon": "🌅"},
    "day":   {"start": 9,  "end": 18, "key": "time.phase.day",   "icon": "☀️"},
    "dusk":  {"start": 18, "end": 22, "key": "time.phase.dusk",  "icon": "🌆"},
    "night": {"start": 22, "end": 6,  "key": "time.phase.night", "icon": "🌙"},
}


def get_current_phase() -> str:
    """Текущая фаза дня."""
    hour = now().hour
    if 6 <= hour < 9:
        return "dawn"
    if 9 <= hour < 18:
        return "day"
    if 18 <= hour < 22:
        return "dusk"
    return "night"


def get_phase_spec(phase: str) -> dict:
    return PHASES.get(phase, PHASES["day"])


def is_night() -> bool:
    return get_current_phase() == "night"


def is_day() -> bool:
    return get_current_phase() == "day"


def is_dusk() -> bool:
    return get_current_phase() == "dusk"


def is_dawn() -> bool:
    return get_current_phase() == "dawn"


def get_time_str() -> str:
    """HH:MM UTC."""
    t = now()
    return f"{t.hour:02d}:{t.minute:02d}"


def get_phase_label(lang: str) -> str:
    """Локализованное название фазы."""
    from core.i18n import t
    phase = get_current_phase()
    spec = get_phase_spec(phase)
    return f"{spec['icon']} {t(spec['key'], lang)}"


def format_time_line(lang: str) -> str:
    """Строка времени для статов."""
    from core.i18n import t
    phase = get_current_phase()
    spec = get_phase_spec(phase)
    time_str = get_time_str()
    return f"🕐 {time_str} UTC · {spec['icon']} {t(spec['key'], lang)}"
