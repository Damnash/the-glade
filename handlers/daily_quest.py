# handlers/daily_quest.py
#
# UI для ежедневного квеста: показать, завершить.

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from core.bot_helpers import check_session, edit_main, make_bot
from db.players import get_player, update_player_fields
from services.daily_quests import (
    ensure_today_quest, get_today_quest, try_complete, format_reward,
)
from content.daily_quests import get_quest


def _render_quest(lang: str, rec: dict, session: str) -> tuple[str, InlineKeyboardMarkup]:
    """Сформировать текст + клавиатуру для квеста."""
    quest = get_quest(rec["quest_key"])
    if not quest:
        return (t("dq.no_quest", lang), _back_kb(lang, session))

    s = f":{session}" if session else ""
    icon = quest.get("icon", "📋")
    title = t(quest["title_key"], lang)
    desc = t(quest["desc_key"], lang)
    progress = rec["progress"]
    need = rec["need"]
    status = rec["status"]
    reward = quest.get("reward", {})

    lines = [
        f"<b>{t('dq.title', lang)}</b>",
        "",
        f"{icon} <b>{title}</b>",
        f"<i>{desc}</i>",
        "",
    ]

    if status == "active":
        lines.append(t("dq.progress_line", lang, progress=progress, need=need))
    elif status == "complete":
        lines.append(t("dq.progress_line", lang, progress=progress, need=need) + " ✅")
    elif status == "rewarded":
        lines.append(t("dq.already_completed", lang))

    lines.append("")
    lines.append(t("dq.reward_line", lang, reward=format_reward(reward, lang)))

    rows = []
    if status == "complete":
        rows.append([
            InlineKeyboardButton(
                text=t("dq.btn_complete", lang),
                callback_data=f"daily_quest:complete{s}",
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text=t("dq.btn_close", lang),
            callback_data=f"nav:back{s}",
        )
    ])

    return ("\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows))


def _back_kb(lang: str, session: str) -> InlineKeyboardMarkup:
    s = f":{session}" if session else ""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("dq.btn_close", lang), callback_data=f"nav:back{s}")
    ]])


async def show_daily_quest(callback: CallbackQuery):
    """Показать ежедневный квест."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # Авто-выдача, если нет
    rec = ensure_today_quest(user_id)
    session = player.get("current_session", "")

    text, kb = _render_quest(lang, rec, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_daily_quest_complete(callback: CallbackQuery):
    """Завершить квест и получить награду."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    result = try_complete(user_id)
    if not result:
        await callback.answer(t("dq.already_completed", lang), show_alert=True)
        return

    quest = result["quest"]
    reward = result["reward"]
    reward_str = format_reward(reward, lang)

    await callback.answer(
        t("dq.completed", lang, reward=reward_str),
        show_alert=True,
    )

    # Перерисовать (уже rewarded)
    player = get_player(user_id)
    rec = get_today_quest(user_id)
    session = player.get("current_session", "")
    text, kb = _render_quest(lang, rec, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
