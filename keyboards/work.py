# keyboards/work.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from core.time_utils import humanize_seconds, seconds_until
from content.work import WORK_TYPES


def work_keyboard(lang: str, player: dict, session: str = "") -> InlineKeyboardMarkup:
    """Меню «Работа»."""
    rows = []
    s = f":{session}" if session else ""
    loc = player["location"]
    status = player["status"]

    if status == "working":
        work_type = player.get("work_type")
        ends_at = player.get("work_ends_at")

        if work_type:
            left = seconds_until(ends_at) if ends_at else 0
            rows.append([
                InlineKeyboardButton(
                    text=t("work.status_line", lang,
                           work=t(f"work.{work_type}", lang),
                           time=humanize_seconds(left, lang)),
                    callback_data=f"noop{s}",
                )
            ])

        rows.append([
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
        ])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if status == "sleeping":
        rows.append([
            InlineKeyboardButton(text=t("work.sleeping", lang), callback_data=f"noop{s}"),
        ])
        rows.append([
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
        ])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    works = [k for k, v in WORK_TYPES.items() if loc in v["locations"]]

    if not works:
        rows.append([
            InlineKeyboardButton(text=t("work.no_work_here", lang), callback_data=f"noop{s}"),
        ])
    else:
        reward_icons = {"food": "🍞", "tokens": "🪙", "water": "💧"}
        for w in works:
            spec = WORK_TYPES[w]
            duration = humanize_seconds(spec["duration_sec"], lang)
            reward = ", ".join(
                f"{reward_icons.get(k, k)} +{v}"
                for k, v in spec["rewards"].items()
            )
            label = t("work.btn_line", lang,
                      work=t(f"work.{w}", lang),
                      duration=duration,
                      reward=reward)
            rows.append([
                InlineKeyboardButton(text=label, callback_data=f"work:{w}{s}"),
            ])

    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
