# handlers/story.py

from aiogram import Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from content.story import STORY_QUESTS, STORY_STAGES
from db.players import get_player, update_player_fields
from db.story import get_quest_status, get_active_quests
from services.story import (
    get_available_quests, get_active_quests_for,
    start_quest, check_quest_progress, complete_quest,
    StoryError,
)


async def show_story_menu(callback: CallbackQuery, bot: Bot, giver: str):
    """Показать сюжетные квесты от NPC."""
    from core.bot_helpers import check_session, edit_main

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    available = get_available_quests(user_id, giver)
    active = get_active_quests_for(user_id, giver)

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    rows = []

    # Активные
    for a in active:
        quest = a["quest"]
        title = t(quest["title_key"], lang)
        progress = f"{a['progress']}/{a['need']}"
        rows.append([
            InlineKeyboardButton(
                text=f"⏳ {title} ({progress})",
                callback_data=f"story:check:{giver}:{a['key']}{s}",
            )
        ])

    # Доступные
    for qkey in available:
        quest = STORY_QUESTS[qkey]
        title = t(quest["title_key"], lang)
        rows.append([
            InlineKeyboardButton(
                text=f"📜 {title}",
                callback_data=f"story:start:{giver}:{qkey}{s}",
            )
        ])

    # Назад
    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"npc:talk:{giver}{s}")
    ])

    text = f"📖 <b>{t('story.title', lang)}</b>\n\n{t('story.giver_intro.' + giver, lang)}"

    if not available and not active:
        text += "\n\n<i>" + t("story.no_quests", lang) + "</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await edit_main(bot, user_id, text, kb)
    await callback.answer()


async def on_story_start(callback: CallbackQuery, bot: Bot):
    """Начать сюжетный квест."""
    from core.bot_helpers import check_session, edit_main

    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # story:start:alby:first_step:session
    parts = callback.data.split(":")
    if len(parts) < 4:
        return
    giver = parts[2]
    quest_key = parts[3]

    try:
        quest = start_quest(user_id, quest_key)
    except StoryError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    title = t(quest["title_key"], lang)
    desc = t(quest["desc_key"], lang)

    await callback.answer(
        t("story.started", lang, title=title),
        show_alert=True,
    )

    # Показать квест
    await show_quest_detail(callback, bot, giver, quest_key)


async def show_quest_detail(callback: CallbackQuery, bot: Bot, giver: str, quest_key: str):
    """Детали квеста."""
    from core.bot_helpers import edit_main

    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    quest = STORY_QUESTS.get(quest_key)
    if not quest:
        return

    title = t(quest["title_key"], lang)
    desc = t(quest["desc_key"], lang)

    check = check_quest_progress(user_id, quest_key)

    text = (
        f"📜 <b>{title}</b>\n\n"
        f"{desc}\n\n"
        f"<i>Прогресс: {check['progress']}/{check['need']}</i>"
    )

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    rows = []

    if check["done"]:
        rows.append([
            InlineKeyboardButton(
                text=t("story.btn_complete", lang),
                callback_data=f"story:complete:{giver}:{quest_key}{s}",
            )
        ])

    rows.append([
        InlineKeyboardButton(text=t("story.btn_back", lang), callback_data=f"story:menu:{giver}{s}")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await edit_main(bot, user_id, text, kb)
    await callback.answer()


async def on_story_check(callback: CallbackQuery, bot: Bot):
    """Проверить квест."""
    from core.bot_helpers import check_session

    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # story:check:alby:first_step:session
    parts = callback.data.split(":")
    if len(parts) < 4:
        return
    giver = parts[2]
    quest_key = parts[3]

    await show_quest_detail(callback, bot, giver, quest_key)


async def on_story_complete(callback: CallbackQuery, bot: Bot):
    """Завершить квест."""
    from core.bot_helpers import check_session, edit_main
    from config import BOT_TOKEN

    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # story:complete:alby:first_step:session
    parts = callback.data.split(":")
    if len(parts) < 4:
        return
    giver = parts[2]
    quest_key = parts[3]

    try:
        result = complete_quest(user_id, quest_key)
    except StoryError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    quest = result["quest"]
    reward = result["reward"]

    # Текст
    lines = [
        f"🏆 <b>{t('story.completed', lang)}</b>",
        f"<i>{t(quest['title_key'], lang)}</i>",
        "",
    ]

    if reward.get("tokens"):
        lines.append(f"🪙 +{reward['tokens']}")
    if reward.get("resource"):
        for k, v in reward["resource"].items():
            name = t(f"item.{k}.name", lang)
            lines.append(f"{name} +{v}")
    if result.get("achievement"):
        ach = t(f"ach.{result['achievement']}.name", lang)
        lines.append(f"🏅 {t('story.new_achievement', lang)}: {ach}")

    text = "\n".join(lines)

    session = player.get("current_session", "")
    s = ":" + session if session else ""

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("story.btn_back", lang), callback_data=f"story:menu:{giver}{s}")
    ]])

    await edit_main(bot, user_id, text, kb)
    await callback.answer()


async def on_story_menu(callback: CallbackQuery, bot: Bot):
    """Меню сюжетных квестов."""
    # story:menu:alby:session
    parts = callback.data.split(":")
    giver = parts[2] if len(parts) > 2 else "alby"
    await show_story_menu(callback, bot, giver)
