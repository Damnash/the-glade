# core/time_utils.py

from datetime import datetime, timezone


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def seconds_since(dt) -> int:
    dt = parse_dt(dt)
    if not dt:
        return 0
    return int((now() - dt).total_seconds())


def seconds_until(dt) -> int:
    dt = parse_dt(dt)
    if not dt:
        return 0
    return max(0, int((dt - now()).total_seconds()))


def humanize_seconds(seconds: int, lang: str = "en") -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    if lang == "ru":
        parts = []
        if h:
            parts.append(f"{h}ч")
        if m:
            parts.append(f"{m}м")
        if s and not h:
            parts.append(f"{s}с")
        return " ".join(parts) or "0с"

    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s and not h:
        parts.append(f"{s}s")
    return " ".join(parts) or "0s"