# handlers/clan_upgrades.py
#
# UI для апгрейдов клана и склада.

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from core.bot_helpers import check_session, edit_main, make_bot
from db.players import get_player
from db.clans import (
    get_player_clan, get_clan, get_clan_members,
    get_storage, get_upgrade_level, get_all_upgrades,
)
from services.clans import get_clan_bonuses, upgrade_clan, ClanError
from content.clan_upgrades import CLAN_UPGRADES, get_upgrade, get_next_level


# ============ Склад клана ============

def _render_storage(lang: str, clan_id: int, session: str) -> tuple[str, InlineKeyboardMarkup]:
    """Рендер склада клана."""
    items = get_storage(clan_id)
    s = f":{session}" if session else ""

    lines = [f"🏗️ <b>{t('upgrade.clan_storage', lang)}</b>", ""]

    if not items:
        lines.append(f"<i>{t('upgrade.clan_storage_empty', lang)}</i>")
    else:
        for item in items:
            name = t(f"item.{item['item_key']}.name", lang)
            lines.append(f"  • {name} × {item['quantity']}")

    rows = [[
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"clan:main{s}")
    ]]

    return ("\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows))


async def show_clan_storage(callback: CallbackQuery):
    """Показать склад клана."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    clan = get_player_clan(user_id)
    if not clan:
        await callback.answer(t("upgrade.no_clan", lang), show_alert=True)
        return

    session = player.get("current_session", "")
    text, kb = _render_storage(lang, clan["clan_id"], session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


# ============ Апгрейды ============

def _render_upgrades(lang: str, clan_id: int, session: str) -> tuple[str, InlineKeyboardMarkup]:
    """Рендер всех апгрейдов."""
    s = f":{session}" if session else ""
    levels = get_all_upgrades(clan_id)

    lines = [f"<b>{t('upgrade.title', lang)}</b>", ""]
    rows = []

    for key, spec in CLAN_UPGRADES.items():
        level = levels.get(key, 0)
        icon = spec["icon"]
        name = t(spec["name_key"], lang)

        if level >= spec["max_level"]:
            status = f"<b>{name}</b> — {t('upgrade.max', lang)}"
            lines.append(status)
        else:
            next_level = level + 1
            cost = spec["costs"][next_level]
            cost_parts = []
            for k, v in cost.items():
                if k == "tokens":
                    cost_parts.append(f"🪙 ×{v}")
                else:
                    cost_parts.append(f"{t(f'item.{k}.name', lang)} ×{v}")
            cost_str = ", ".join(cost_parts)
            lines.append(f"<b>{name}</b> — ур. {level}")
            lines.append(f"  → {cost_str}")

        # Кнопка апгрейда
        if level < spec["max_level"]:
            next_level = level + 1
            rows.append([
                InlineKeyboardButton(
                    text=f"{icon} {t('upgrade.btn_upgrade', lang, level=next_level)}",
                    callback_data=f"clan_upgrade:do:{key}{s}",
                )
            ])

    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"clan:main{s}")
    ])

    return ("\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows))


async def show_clan_upgrades(callback: CallbackQuery):
    """Показать список апгрейдов клана."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    clan = get_player_clan(user_id)
    if not clan:
        await callback.answer(t("upgrade.no_clan", lang), show_alert=True)
        return

    session = player.get("current_session", "")
    text, kb = _render_upgrades(lang, clan["clan_id"], session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_upgrade_click(callback: CallbackQuery):
    """Попытка апгрейда."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    clan = get_player_clan(user_id)
    if not clan:
        await callback.answer(t("upgrade.no_clan", lang), show_alert=True)
        return

    # clan_upgrade:do:KEY:session
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    upgrade_key = parts[2]

    try:
        result = upgrade_clan(clan["clan_id"], upgrade_key)
    except ClanError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    spec = get_upgrade(upgrade_key)
    name = t(spec["name_key"], lang) if spec else upgrade_key

    await callback.answer(
        t("upgrade.success", lang, name=name, level=result["new_level"]),
        show_alert=True,
    )

    # Перерисовать
    session = player.get("current_session", "")
    text, kb = _render_upgrades(lang, clan["clan_id"], session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
