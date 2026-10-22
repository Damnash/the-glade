# keyboards/clans.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t


def clan_main_keyboard(lang: str, session: str = "") -> InlineKeyboardMarkup:
    s = f":{session}" if session else ""

    rows = [
        [
            InlineKeyboardButton(text=t("clan.btn_members", lang), callback_data=f"clan:members{s}"),
            InlineKeyboardButton(text=t("clan.btn_chat", lang), callback_data=f"clan:chat{s}"),
        ],
        [
            InlineKeyboardButton(text=t("clan.open.btn_toggle_on", lang), callback_data=f"clan:toggle_open:on{s}"),
            InlineKeyboardButton(text=t("clan.open.btn_toggle_off", lang), callback_data=f"clan:toggle_open:off{s}"),
        ],
        [
            InlineKeyboardButton(text=t("clan.btn_map", lang), callback_data=f"clan:map{s}"),
            InlineKeyboardButton(text=t("clan.btn_treasury", lang), callback_data=f"clan:treasury{s}"),
        ],
        [
            InlineKeyboardButton(text=t("upgrade.title", lang), callback_data=f"clan_upgrades:show{s}"),
            InlineKeyboardButton(text=t("upgrade.clan_storage", lang), callback_data=f"clan_storage:show{s}"),
        ],
        [
            InlineKeyboardButton(text=t("clan.btn_invite", lang), callback_data=f"clan:invite_help{s}"),
            InlineKeyboardButton(text=t("clan.btn_leave", lang), callback_data=f"clan:leave{s}"),
        ],
        [
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clan_no_clan_keyboard(lang: str, session: str = "") -> InlineKeyboardMarkup:
    s = f":{session}" if session else ""

    rows = [
        [
            InlineKeyboardButton(text=t("clan.btn_create", lang), callback_data=f"clan:create_help{s}"),
            InlineKeyboardButton(text=t("clan.btn_invites", lang), callback_data=f"clan:invites{s}"),
        ],
        [
            InlineKeyboardButton(text=t("clan.open.btn_list", lang), callback_data=f"clan:open_list{s}"),
        ],
        [
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clan_invites_keyboard(lang: str, invites: list, session: str = "") -> InlineKeyboardMarkup:
    s = f":{session}" if session else ""
    rows = []

    for inv in invites:
        rows.append([
            InlineKeyboardButton(
                text=t("clan.invite_btn", lang, name=inv["clan_name"]),
                callback_data=f"clan:accept:{inv['id']}{s}",
            )
        ])

    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"clan:main{s}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clan_confirm_leave_keyboard(lang: str, session: str = "") -> InlineKeyboardMarkup:
    s = f":{session}" if session else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("clan.confirm_yes", lang), callback_data=f"clan:leave_confirm{s}"),
            InlineKeyboardButton(text=t("clan.confirm_no", lang), callback_data=f"clan:main{s}"),
        ]
    ])

def clan_open_list_keyboard(lang: str, clans: list[dict], session: str = "") -> InlineKeyboardMarkup:
    """Список открытых кланов для вступления."""
    s = f":{session}" if session else ""
    rows = []
    for c in clans[:10]:
        rows.append([
            InlineKeyboardButton(
                text=t("clan.open.row", lang, name=c["name"], n=c["members"]),
                callback_data=f"clan:open:{c['clan_id']}{s}",
            )
        ])
    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"clan:main{s}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clan_open_detail_keyboard(lang: str, clan_id: int, session: str = "") -> InlineKeyboardMarkup:
    """Детали открытого клана — кнопка «Вступить»."""
    s = f":{session}" if session else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("clan.open.join", lang), callback_data=f"clan:join:{clan_id}{s}")],
        [InlineKeyboardButton(text=t("nav.back", lang),   callback_data=f"clan:open_list{s}")],
    ])

