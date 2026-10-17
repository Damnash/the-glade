# keyboards/pvp.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t


def pvp_actions_keyboard(lang: str, target_user_id: int) -> InlineKeyboardMarkup:
    # NOTE: not used yet — handlers for pvp:steal/attack/duel not implemented
    """Действия против игрока."""
    rows = [
        [
            InlineKeyboardButton(
                text=t("pvp.btn_steal", lang),
                callback_data=f"pvp:steal:{target_user_id}",
            ),
            InlineKeyboardButton(
                text=t("pvp.btn_attack", lang),
                callback_data=f"pvp:attack:{target_user_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=t("pvp.btn_duel", lang),
                callback_data=f"pvp:duel:{target_user_id}",
            ),
            InlineKeyboardButton(
                text=t("nav.back", lang),
                callback_data="nav:back",
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def duel_response_keyboard(lang: str, duel_id: int) -> InlineKeyboardMarkup:
    """Принять/отклонить дуэль."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("pvp.btn_accept_duel", lang),
                callback_data=f"duel:accept:{duel_id}",
            ),
            InlineKeyboardButton(
                text=t("pvp.btn_decline_duel", lang),
                callback_data=f"duel:decline:{duel_id}",
            ),
        ]
    ])
