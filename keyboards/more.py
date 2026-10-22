# keyboards/more.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t


def more_keyboard(lang: str, session: str = "") -> InlineKeyboardMarkup:
    """Подменю «Ещё»: журнал, дневник, ключи, PvP."""
    s = f":{session}" if session else ""
    rows = [
        [
            InlineKeyboardButton(text=t("journal.btn", lang), callback_data=f"journal:show:menu{s}"),
            InlineKeyboardButton(text=t("diary.btn", lang),   callback_data=f"diary:show{s}"),
        ],
        [
            InlineKeyboardButton(text=t("keys.btn", lang),    callback_data=f"keys:show{s}"),
            InlineKeyboardButton(text="⚔️ PvP",              callback_data=f"pvp:flag{s}"),
        ],
        [
            InlineKeyboardButton(text=t("clan.title", lang),  callback_data=f"clan:main{s}"),
            InlineKeyboardButton(text=t("nav.back", lang),    callback_data=f"nav:back{s}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
