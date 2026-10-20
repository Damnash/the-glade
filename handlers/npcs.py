# handlers/npcs.py

from aiogram import Bot
from aiogram.types import CallbackQuery

from core.i18n import t
from content.npcs import NPCS
from db.players import get_player
from keyboards.npcs import npc_talk_keyboard
from core.bot_helpers import make_bot


async def on_talk_to_npc(callback: CallbackQuery):
    """Показать диалог с NPC."""
    from core.bot_helpers import check_session, edit_main
    from config import BOT_TOKEN

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # npc:talk:frypan:session
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    npc_key = parts[2]

    npc = NPCS.get(npc_key)
    if not npc:
        await callback.answer("NPC not found.", show_alert=True)
        return

    if player["location"] != npc["location"]:
        await callback.answer("Ты не рядом.", show_alert=True)
        return

    # Story tracking — разговор с NPC
    try:
        from services.story import track_event
        track_event(user_id, "talk_npc", {"npc": npc_key})
    except Exception:
        pass

    # Выбрать вариант диалога по состоянию игрока
    from content.npcs import get_npc_dialog_key
    # first_visit: если у игрока ещё нет истории с этим NPC (упрощённо — intro_done)
    try:
        from db.connection import get_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM npc_visits WHERE user_id = ? AND npc_key = ?", (user_id, npc_key))
        is_first_visit = cur.fetchone() is None
        conn.close()
    except Exception:
        is_first_visit = False
    dialog_key = get_npc_dialog_key(npc_key, player, is_first_visit=is_first_visit)
    dialog = t(dialog_key, lang)
    text = "<b>" + t(npc['name_key'], lang) + "</b>\n\n" + dialog

    # Слух (20% шанс)
    try:
        import random
        from content.rumors import RUMORS, RUMOR_CHANCE
        rumor_keys = RUMORS.get(npc_key, [])
        if rumor_keys and random.random() < RUMOR_CHANCE:
            rumor_key = random.choice(rumor_keys)
            rumor_text = t(rumor_key, lang)
            if rumor_text and rumor_text != rumor_key:
                text += "\n\n💬 <i>" + rumor_text + "</i>"
    except Exception:
        pass

    # Пометить, что игрок уже говорил с NPC (для first_visit)
    try:
        from db.connection import get_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO npc_visits (user_id, npc_key) VALUES (?, ?)
        """, (user_id, npc_key))
        conn.commit()
        conn.close()
    except Exception:
        pass

    session = player.get("current_session", "")
    kb = npc_talk_keyboard(lang, npc_key, npc["actions"], session)

    # Секрет Терезы — по одному при каждом разговоре (до 10)
    if npc_key == "teresa":
        try:
            from content.teresa_secrets import TERESA_SECRETS
            from db.connection import get_conn
            _conn = get_conn()
            try:
                _cur = _conn.cursor()
                _cur.execute("SELECT COUNT(*) FROM npc_visits WHERE user_id = ? AND npc_key = 'teresa'", (user_id,))
                _visits = _cur.fetchone()[0]
            finally:
                _conn.close()

            # Секрет показываем начиная со 2-го визита (1-й — приветствие)
            _secret_idx = max(0, _visits - 1)
            if _secret_idx < len(TERESA_SECRETS):
                _secret_key = TERESA_SECRETS[_secret_idx]
                _secret_text = t(_secret_key, lang)
                if _secret_text and _secret_text != _secret_key:
                    text += "\n\n🌙 <b>Секрет:</b> <i>" + _secret_text + "</i>"

                    # В журнал: 10-й секрет — important, остальные — chat
                    try:
                        from services.event_log import add_event, cleanup_old_events
                        _sev = "important" if (_secret_idx + 1) == 10 else "chat"
                        add_event(user_id, "teresa_secret",
                                  f"🌙 Секрет Терезы ({_secret_idx + 1}/10): {_secret_text}",
                                  severity=_sev)
                        cleanup_old_events(user_id)
                    except Exception:
                        pass
                    try:
                        from services.diary import add_diary_auto
                        add_diary_auto(user_id, "teresa_secret",
                                       n=_secret_idx + 1, text=_secret_text)
                    except Exception:
                        pass

                    # Благословение — раз в 3 секрета
                    if (_secret_idx + 1) % 3 == 0:
                        try:
                            from services.buffs import add_buff
                            add_buff(user_id, "blessed")
                        except Exception:
                            pass
        except Exception as e:
            import logging
            logging.warning(f"[teresa_secret] {e}")

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_npc_action(callback: CallbackQuery):
    """Действие NPC."""
    from core.bot_helpers import check_session
    from config import BOT_TOKEN

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # npc:frypan:trade_food:session
    parts = callback.data.split(":")
    if len(parts) < 3:
        return

    npc_key = parts[1]
    action = parts[2]

    npc = NPCS.get(npc_key)
    if not npc:
        return

    if player["location"] != npc["location"]:
        await callback.answer("Ты не рядом.", show_alert=True)
        return

    # Действия
    if npc_key == "frypan" and action == "trade_food":
        await _frypan_buy(callback, user_id, lang)
    elif npc_key == "jeff" and action == "heal":
        await _jeff_heal(callback, user_id, lang)
    elif npc_key == "jeff" and action == "buy_bandage":
        await _jeff_buy_bandage(callback, user_id, lang)
    elif npc_key == "chuck" and action == "hint":
        await _chuck_hint(callback, user_id, lang)
    elif npc_key == "frypan" and action == "hint":
        await _npc_hint(callback, user_id, lang, "frypan")
    elif npc_key == "jeff" and action == "hint":
        await _npc_hint(callback, user_id, lang, "jeff")
    elif npc_key == "minho" and action == "hint":
        await _npc_hint(callback, user_id, lang, "minho")
    elif npc_key == "winston" and action == "hint":
        await _npc_hint(callback, user_id, lang, "winston")
    elif npc_key == "alby" and action == "hint":
        await _npc_hint(callback, user_id, lang, "alby")
    elif npc_key == "minho" and action == "show_map":
        await _minho_map(callback, user_id, lang)
    elif npc_key == "clint" and action == "craft":
        await _clint_craft(callback, user_id, lang)
    elif npc_key == "clint" and action.startswith("craft_"):
        await _clint_do_craft(callback, user_id, lang)
    elif npc_key == "alby" and action == "talk":
        await _alby_quests(callback, user_id, lang)
    elif npc_key == "alby" and action.startswith("quest_"):
        await _alby_start_quest(callback, user_id, lang)
    elif npc_key == "gally" and action.startswith("respond_"):
        await _gally_respond(callback, user_id, lang)
    elif npc_key == "winston" and action == "talk":
        await _winston_trade(callback, user_id, lang)
    elif npc_key == "winston" and action == "trade":
        await _winston_trade(callback, user_id, lang)
    elif npc_key == "winston" and action.startswith("trade_"):
        await _winston_do_trade(callback, user_id, lang)
    elif npc_key == "frypan" and action == "bring_meat":
        await _frypan_bring_meat(callback, user_id, lang)
    elif npc_key == "winston" and action == "bring_water":
        await _winston_bring_water(callback, user_id, lang)
    elif npc_key == "newt" and action == "talk":
        await callback.answer(t("npc.newt.dialog", lang), show_alert=True)
    elif npc_key == "teresa" and action == "talk":
        await callback.answer(t("npc.teresa.dialog", lang), show_alert=True)
    elif action == "story":
        from handlers.story import show_story_menu
        from core.bot_helpers import make_bot

        bot = make_bot()
        try:
            await show_story_menu(callback, bot, npc_key)
        finally:
            await bot.session.close()
        return

    else:
        await callback.answer(t("npc.not_implemented", lang), show_alert=True)


# ============ Действия ============

async def _frypan_buy(callback, user_id, lang):
    from core.bot_helpers import edit_main
    from db.players import get_player, update_player_fields
    from config import BOT_TOKEN
    from aiogram import Bot

    player = get_player(user_id)
    cost = 2
    food = 5

    if player.get("tokens", 0) < cost:
        await callback.answer(t("npc.frypan.no_tokens", lang, cost=cost), show_alert=True)
        return

    new_food = min(player["food"] + food, player.get("max_food", 10))
    update_player_fields(user_id, {
        "tokens": player["tokens"] - cost,
        "food": new_food,
    })

    await callback.answer(t("npc.frypan.bought", lang, food=food, cost=cost), show_alert=True)

    # Обновить главное
    from core.bot_helpers import refresh_main
    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def _jeff_heal(callback, user_id, lang):
    from db.players import get_player, update_player_fields
    from core.bot_helpers import refresh_main
    from config import BOT_TOKEN
    from aiogram import Bot

    player = get_player(user_id)
    cost = 5
    heal = 30

    if player["hp"] >= 100:
        await callback.answer(t("npc.jeff.already_healthy", lang), show_alert=True)
        return

    if player.get("tokens", 0) < cost:
        await callback.answer(t("npc.jeff.no_tokens", lang, cost=cost), show_alert=True)
        return

    update_player_fields(user_id, {
        "tokens": player["tokens"] - cost,
        "hp": min(100, player["hp"] + heal),
    })

    await callback.answer(t("npc.jeff.healed", lang, hp=heal, cost=cost), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def _npc_hint(callback, user_id, lang, npc_key):
    """Подсказка от NPC.
    - Чак: по очереди (5).
    - Остальные: одна подсказка (потом «уже говорил»).
    """
    from content.npc_hints import NPC_HINTS
    from db.connection import get_conn

    hints = NPC_HINTS.get(npc_key, [])
    if not hints:
        await callback.answer(t("npc.not_implemented", lang), show_alert=True)
        return

    # Сколько раз игрок уже говорил с NPC
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM npc_visits WHERE user_id = ? AND npc_key = ?",
            (user_id, npc_key),
        )
        visits = cur.fetchone()[0]
    finally:
        conn.close()

    # Индекс подсказки: для Чака — visits-1 (первый визит → 0)
    # Для остальных — 0 всегда, но проверяем, говорил ли уже
    if npc_key == "chuck":
        idx = max(0, visits - 1)
    else:
        idx = 0

    if idx >= len(hints):
        # Все подсказки кончились
        await callback.answer(t("npc.hint.all_done", lang), show_alert=True)
        return

    # Для не-Чака: если уже говорил (visits > 1) — «уже говорил»
    if npc_key != "chuck" and visits > 1:
        await callback.answer(t("npc.hint.already", lang), show_alert=True)
        return

    hint_key = hints[idx]
    await callback.answer(t(hint_key, lang), show_alert=True)


async def _chuck_hint(callback, user_id, lang):
    await _npc_hint(callback, user_id, lang, "chuck")


async def _minho_map(callback, user_id, lang):
    from core.maze_current import get_current_season
    from db.maze_state import get_map_status

    season = get_current_season()
    status = get_map_status(season, 1)

    if not status["sections"]:
        await callback.answer(t("npc.minho.no_map", lang), show_alert=True)
        return

    await callback.answer(
        t("npc.minho.map_info", lang, d=status["discovered"], t=status["total"]),
        show_alert=True,
    )


async def _clint_craft(callback, user_id, lang):
    from core.bot_helpers import edit_main
    from services.npc_actions import CRAFT_RECIPES
    from config import BOT_TOKEN
    from aiogram import Bot
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    player = get_player(user_id)
    session = player.get("current_session", "")
    s = f":{session}" if session else ""

    rows = []
    for key, recipe in CRAFT_RECIPES.items():
        name = t(recipe["name_key"], lang)
        rows.append([
            InlineKeyboardButton(
                text=f"{name} × {recipe['result_qty']} — {recipe['tokens']} 🪙",
                callback_data=f"npc:clint:craft_{key}{s}",
            )
        ])

    rows.append([
        InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"npc:talk:clint{s}")
    ])

    text = "🔨 <b>" + t('npc.clint.name', lang) + "</b>\n\n" + t('npc.clint.craft_menu', lang)
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def _clint_do_craft(callback, user_id, lang):
    from services.npc_actions import craft, NPCActionError
    from core.bot_helpers import refresh_main
    from config import BOT_TOKEN
    from aiogram import Bot

    parts = callback.data.split(":")
    action = parts[2]  # craft_knife
    recipe_key = action.replace("craft_", "")

    try:
        result = craft(user_id, recipe_key)
    except NPCActionError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    item_name = t(f"item.{result['item']}.name", lang)
    await callback.answer(
        t("npc.clint.crafted", lang, item=item_name, qty=result["qty"], cost=result["cost"]),
        show_alert=True,
    )

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def _alby_quests(callback, user_id, lang):
    from core.bot_helpers import edit_main
    from services.npc_actions import get_active_quest, SIMPLE_QUESTS, try_complete_quest
    from config import BOT_TOKEN
    from aiogram import Bot
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    player = get_player(user_id)
    session = player.get("current_session", "")
    s = f":{session}" if session else ""

    # Попытка завершить
    completed = try_complete_quest(user_id)
    if completed:
        await callback.answer(
            t("npc.alby.quest_completed", lang, reward=completed["reward"]),
            show_alert=True,
        )

    active = get_active_quest(user_id)

    if active:
        spec = SIMPLE_QUESTS.get(active["quest_key"], {})
        name = t(spec.get("name_key", "?"), lang)
        text = (
            "<b>" + t('npc.alby.name', lang) + "</b>\n\n"
            + t("npc.alby.active_quest", lang,
                name=name, progress=active["progress"], need=active["need"])
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"npc:talk:alby{s}")
        ]])
    else:
        rows = []
        for key, quest in SIMPLE_QUESTS.items():
            rows.append([
                InlineKeyboardButton(
                    text=t(quest["name_key"], lang),
                    callback_data=f"npc:alby:quest_{key}{s}",
                )
            ])
        rows.append([
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"npc:talk:alby{s}")
        ])
        text = "<b>" + t('npc.alby.name', lang) + "</b>\n\n" + t('npc.alby.quests_menu', lang)
        kb = InlineKeyboardMarkup(inline_keyboard=rows)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def _alby_start_quest(callback, user_id, lang):
    from services.npc_actions import start_quest, NPCActionError
    from core.bot_helpers import refresh_main
    from config import BOT_TOKEN
    from aiogram import Bot

    parts = callback.data.split(":")
    action = parts[2]  # quest_fragments_3
    quest_key = action.replace("quest_", "")

    try:
        start_quest(user_id, quest_key)
    except NPCActionError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    await callback.answer(t("npc.alby.quest_started", lang), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def _gally_respond(callback, user_id, lang):
    from services.npc_actions import gally_respond, NPCActionError
    from core.bot_helpers import refresh_main
    from config import BOT_TOKEN
    from aiogram import Bot

    parts = callback.data.split(":")
    action = parts[2]  # respond_rude
    response = action.replace("respond_", "")

    try:
        result = gally_respond(user_id, response)
    except NPCActionError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    if result["type"] == "silent":
        await callback.answer(t("npc.gally.silent", lang), show_alert=True)
    elif result["type"] == "rude":
        await callback.answer(t("npc.gally.hit_you", lang, dmg=result["damage"]), show_alert=True)
    elif result["type"] == "fight_win":
        await callback.answer(t("npc.gally.fight_win", lang, reward=result["reward"]), show_alert=True)
    elif result["type"] == "fight_lose":
        await callback.answer(t("npc.gally.fight_lose", lang, dmg=result["damage"]), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def _winston_trade(callback, user_id, lang):
    from core.bot_helpers import edit_main
    from config import BOT_TOKEN
    from aiogram import Bot
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    player = get_player(user_id)
    session = player.get("current_session", "")
    s = f":{session}" if session else ""

    rows = [
        [
            InlineKeyboardButton(text=t("npc.winston.trade_food", lang),
                                  callback_data=f"npc:winston:trade_food_to_tokens{s}"),
            InlineKeyboardButton(text=t("npc.winston.trade_water", lang),
                                  callback_data=f"npc:winston:trade_water_to_tokens{s}"),
        ],
        [
            InlineKeyboardButton(text=t("npc.winston.buy_food", lang),
                                  callback_data=f"npc:winston:trade_tokens_to_food{s}"),
            InlineKeyboardButton(text=t("npc.winston.buy_water", lang),
                                  callback_data=f"npc:winston:trade_tokens_to_water{s}"),
        ],
        [
            InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"npc:talk:winston{s}")
        ],
    ]

    text = "<b>" + t('npc.winston.name', lang) + "</b>\n\n" + t('npc.winston.trade_menu', lang)
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def _winston_do_trade(callback, user_id, lang):
    from services.npc_actions import winston_trade, NPCActionError
    from core.bot_helpers import refresh_main
    from config import BOT_TOKEN
    from aiogram import Bot

    parts = callback.data.split(":")
    action = parts[2]  # trade_food_to_tokens
    trade_key = action.replace("trade_", "")

    try:
        winston_trade(user_id, trade_key)
    except NPCActionError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    await callback.answer(t("npc.winston.traded", lang), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def _jeff_buy_bandage(callback, user_id, lang):
    """Купить бинт у Джеффа за 3 жетона."""
    from db.players import get_player, update_player_fields
    from db.inventory import add_item
    from core.bot_helpers import refresh_main, make_bot

    player = get_player(user_id)
    cost = 3

    if player.get("tokens", 0) < cost:
        await callback.answer(t("npc.jeff.no_tokens", lang, cost=cost), show_alert=True)
        return

    update_player_fields(user_id, {"tokens": player["tokens"] - cost})
    add_item(user_id, "bandage", 1)

    await callback.answer(t("npc.jeff.bought_bandage", lang, cost=cost), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()

async def _frypan_bring_meat(callback, user_id, lang):
    """Сдать мясо Фрайпану (для ежедневного квеста)."""
    from core.bot_helpers import refresh_main, make_bot
    from services.npc_actions import bring_to_npc, NPCActionError

    try:
        result = bring_to_npc(user_id, "frypan", "meat", qty=1)
    except NPCActionError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    # Сообщение
    if result["quest_completed"]:
        await callback.answer(t("npc.bring_quest_complete", lang), show_alert=True)
    elif result["progress_updated"]:
        await callback.answer(t("npc.bring_progress", lang), show_alert=True)
    else:
        await callback.answer(t("npc.bring_ok", lang), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()


async def _winston_bring_water(callback, user_id, lang):
    """Сдать воду Уинстону (для ежедневного квеста)."""
    from core.bot_helpers import refresh_main, make_bot
    from services.npc_actions import bring_to_npc, NPCActionError

    try:
        result = bring_to_npc(user_id, "winston", "water_flask", qty=1)
    except NPCActionError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    if result["quest_completed"]:
        await callback.answer(t("npc.bring_quest_complete", lang), show_alert=True)
    elif result["progress_updated"]:
        await callback.answer(t("npc.bring_progress", lang), show_alert=True)
    else:
        await callback.answer(t("npc.bring_ok", lang), show_alert=True)

    bot = make_bot()
    try:
        await refresh_main(bot, user_id)
    finally:
        await bot.session.close()

