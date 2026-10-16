# keyboards/help.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t


HELP_CATEGORIES = [
    ("movement", "🚶"),
    ("actions", "⚒️"),
    ("maze", "🌀"),
    ("communication", "📡"),
    ("clan", "👥"),
    ("maps", "🗺️"),
    ("pvp", "⚔️"),
    ("progress", "🏆"),
    ("info", "📊"),
]


def help_main_keyboard(lang: str, session: str = "") -> InlineKeyboardMarkup:
    """Главное меню help."""
    s = f":{session}" if session else ""
    rows = []

    buttons = []
    for key, icon in HELP_CATEGORIES:
        name = t(f"help.cat.{key}.short", lang)
        buttons.append(
            InlineKeyboardButton(
                text=f"{icon} {name}",
                callback_data=f"help:cat:{key}{s}",
            )
        )

    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i + 2])

    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def help_cat_keyboard(lang: str, session: str = "") -> InlineKeyboardMarkup:
    """Кнопка назад из категории."""
    s = f":{session}" if session else ""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t("help.btn_back", lang),
            callback_data=f"help:main{s}",
        )
    ]])
