# handlers/pvp.py

import random

from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from services.event_log import add_event, cleanup_old_events
from db.players import get_player, get_lang, find_by_name
from services.pvp import (
    attempt_steal, attack_player, kill_player,
    challenge_duel, resolve_duel,
    check_pvp_possible, PvPError,
)
from db.pvp import get_pending_duel_for, get_duel, set_duel_status
from keyboards.pvp import duel_response_keyboard


# ============ Команды ============

async def cmd_steal(message: Message, bot: Bot):
    """/украсть <ник>."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("pvp.steal_usage", lang))
        return

    try:
        result = attempt_steal(user_id, parts[1].strip())
    except PvPError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    if not result["success"]:
        await message.answer(t("pvp.steal_failed", lang, chance=int(result["chance"] * 100)))
        return

    if result.get("empty"):
        await message.answer(t("pvp.steal_empty", lang))
        return

    if result["stolen"] == "tokens":
        await message.answer(t("pvp.steal_tokens", lang, qty=result["qty"]))
    else:
        item_name = t(f"item.{result['stolen']}.name", lang)
        await message.answer(t("pvp.steal_item", lang, item=item_name))


async def cmd_attack(message: Message, bot: Bot):
    """/атаковать <ник>."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("pvp.attack_usage", lang))
        return

    nick = parts[1].strip()

    try:
        result = attack_player(user_id, nick)
    except PvPError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(
        t("pvp.attack_hit", lang, name=result["victim_name"], dmg=result["damage"])
    )

    # Уведомление жертве
    try:
        victim_lang = get_lang(result["victim_id"])
        await bot.send_message(
            chat_id=result["victim_id"],
            text=t("pvp.attacked_you", victim_lang,
                   dmg=result["damage"], hp=result["victim_hp"]),
        )
    except Exception:
        pass

    # Лог жертве (важное)
    try:
        add_event(result["victim_id"], "attacked_by",
                  t("log.attacked_by", get_lang(result["victim_id"]), name=player["display_name"] or player["username"]),
                  severity="important")
        cleanup_old_events(result["victim_id"])
    except Exception:
        pass

    # Если умер — убийство
    if result["victim_dead"]:
        attacker = get_player(user_id)
        section_id = attacker.get("maze_section")
        layer = attacker.get("maze_layer", 1)

        loot = kill_player(user_id, result["victim_id"], section_id, layer)

        # Логи
        try:
            add_event(user_id, "killed",
                      t("log.killed", lang, name=result["victim_name"]), severity="important")
            cleanup_old_events(user_id)
            add_event(result["victim_id"], "died",
                      t("log.died", get_lang(result["victim_id"])), severity="important")
            cleanup_old_events(result["victim_id"])
        except Exception:
            pass

        await message.answer(
            t("pvp.kill_success", lang,
              name=result["victim_name"],
              tokens=loot["tokens"],
              items=loot["items"])
        )

        # Уведомление всем
        try:
            from db.connection import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM players WHERE user_id != ?", (user_id,))
            all_players = cur.fetchall()
            conn.close()

            attacker_name = attacker["display_name"] or attacker["username"]
            for (uid,) in all_players:
                try:
                    ulang = get_lang(uid)
                    await bot.send_message(
                        chat_id=uid,
                        text=t("pvp.kill_broadcast", ulang, name=attacker_name),
                    )
                except Exception:
                    pass
        except Exception:
            pass


async def cmd_duel(message: Message, bot: Bot):
    """/дуэль <ник> [ставка]."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(t("pvp.duel_usage", lang))
        return

    nick = parts[1]
    stake = 0
    if len(parts) >= 3:
        try:
            stake = int(parts[2])
            if stake < 0:
                stake = 0
        except ValueError:
            stake = 0

    try:
        result = challenge_duel(user_id, nick, stake)
    except PvPError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(
        t("pvp.duel_sent", lang, name=result["opponent_name"], stake=stake)
    )

    # Уведомление противнику
    opponent_id = result["opponent_id"]
    try:
        opponent_lang = get_lang(opponent_id)
        text = t("pvp.duel_received", opponent_lang,
                 name=result["challenger_name"], stake=stake)

        kb = duel_response_keyboard(opponent_lang, result["duel_id"])
        await bot.send_message(chat_id=opponent_id, text=text, reply_markup=kb)
    except Exception:
        pass


# ============ Дуэль — ответ ============

async def on_duel_accept(callback: CallbackQuery, bot: Bot):
    """Принять дуэль."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    duel_id = int(callback.data.split(":")[2])
    duel = get_duel(duel_id)

    if not duel or duel["opponent_id"] != user_id or duel["status"] != "pending":
        await callback.answer(t("pvp.err.duel_not_found", lang), show_alert=True)
        return

    # Случайный победитель (пока без боя)
    winner_id = random.choice([duel["challenger_id"], duel["opponent_id"]])

    try:
        result = resolve_duel(duel_id, winner_id)
    except PvPError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    await callback.message.edit_text(
        t("pvp.duel_resolved", lang,
          winner=result["winner_name"],
          loser=result["loser_name"],
          stake=result["stake"])
    )

    # Уведомление обоим
    loser_id = duel["challenger_id"] if winner_id == duel["opponent_id"] else duel["opponent_id"]
    try:
        w_lang = get_lang(winner_id)
        await bot.send_message(chat_id=winner_id,
                                text=t("pvp.duel_won", w_lang, stake=result["stake"]))
    except Exception:
        pass

    try:
        l_lang = get_lang(loser_id)
        await bot.send_message(chat_id=loser_id,
                                text=t("pvp.duel_lost", l_lang, stake=result["stake"]))
    except Exception:
        pass

    await callback.answer()


async def on_duel_decline(callback: CallbackQuery, bot: Bot):
    """Отклонить дуэль."""
    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    duel_id = int(callback.data.split(":")[2])
    duel = get_duel(duel_id)

    if not duel or duel["opponent_id"] != user_id or duel["status"] != "pending":
        await callback.answer(t("pvp.err.duel_not_found", lang), show_alert=True)
        return

    set_duel_status(duel_id, "declined")

    await callback.message.edit_text(t("pvp.duel_declined", lang))

    # Уведомление вызывающему
    try:
        c_lang = get_lang(duel["challenger_id"])
        await bot.send_message(
            chat_id=duel["challenger_id"],
            text=t("pvp.duel_declined_by_opponent", c_lang),
        )
    except Exception:
        pass

    await callback.answer()


# ============ PvP флаг (v1.1) ============

async def cmd_pvp_flag(message: Message):
    """/pvp_flag — включить PvP флаг на 24 часа."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    from db.pvp import (
        has_pvp_flag, set_pvp_flag, get_pvp_flag_time_left,
    )
    from core.time_utils import humanize_seconds

    if has_pvp_flag(user_id):
        left = get_pvp_flag_time_left(user_id)
        await message.answer(t("pvp.flag_already", lang, time=humanize_seconds(left, lang)))
        return

    set_pvp_flag(user_id)
    await message.answer(t("pvp.flag_set", lang, hours=24))


# ============ PvP флаг: UI (v1.1) ============

async def show_pvp_flag(callback: CallbackQuery):
    """Показать экран PvP-флага."""
    from core.bot_helpers import check_session, edit_main, make_bot
    from db.pvp import has_pvp_flag, get_pvp_flag_time_left
    from core.time_utils import humanize_seconds
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from core.maze_current import get_current_season, get_season_day

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    season = get_current_season()
    day = get_season_day(season)

    has = has_pvp_flag(user_id)
    time_left = get_pvp_flag_time_left(user_id) if has else 0
    time_str = humanize_seconds(time_left, lang)

    if day >= 80:
        text = t("pvp.flag_mandatory", lang)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("nav.back", lang), callback_data="nav:back"),
        ]])
    else:
        status = t("pvp.flag_status_on", lang, time=time_str) if has else t("pvp.flag_status_off", lang)

        lines = [
            "⚔️ <b>" + t("pvp.flag_title", lang) + "</b>",
            "",
            status,
            "",
            t("pvp.flag_help", lang),
        ]
        text = "\n".join(lines)

        session = player.get("current_session", "")
        s = f":{session}" if session else ""

        if has:
            btn = InlineKeyboardButton(
                text=t("pvp.btn_disable", lang),
                callback_data=f"pvp:flag_off{s}",
            )
        else:
            btn = InlineKeyboardButton(
                text=t("pvp.btn_enable", lang),
                callback_data=f"pvp:flag_on{s}",
            )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [btn],
            [InlineKeyboardButton(text=t("nav.back", lang), callback_data=f"nav:back{s}")],
        ])

    from core.bot_helpers import edit_main, make_bot
    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def on_pvp_flag_toggle(callback: CallbackQuery):
    """Включить/выключить флаг."""
    from core.bot_helpers import check_session, refresh_main
    from db.pvp import has_pvp_flag, set_pvp_flag, clear_pvp_flag

    user_id = callback.from_user.id
    player = get_player(user_id)
    if not player:
        return

    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    # pvp:flag_on / pvp:flag_off
    if "flag_on" in callback.data:
        set_pvp_flag(user_id)
        await callback.answer(t("pvp.flag_set", lang, hours=24))
    else:
        clear_pvp_flag(user_id)
        await callback.answer(t("pvp.flag_removed", lang))

    # Перерисовать экран
    await show_pvp_flag(callback)
