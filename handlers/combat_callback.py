# handlers/combat_callback.py

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core.i18n import t
from db.players import get_player
from keyboards.combat import combat_keyboard
from core.bot_helpers import make_bot
from services.combat import (
    get_active_combat, start_combat, end_combat,
    player_attack, player_defend, player_flee,
    give_victory_rewards, CombatError,
)


def render_combat(lang: str, combat: dict, player: dict) -> str:
    """Текст боя."""
    from content.monsters import get_monster
    monster = get_monster(combat["monster_type"])

    monster_hp = combat["monster_hp"]
    monster_max = combat["monster_max_hp"]

    ratio = monster_hp / monster_max if monster_max > 0 else 0
    bar_filled = int(ratio * 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)

    text = (
        "⚔️ <b>" + t(monster['name_key'], lang) + "</b>\n\n"
        "<i>" + t(monster['desc_key'], lang) + "</i>\n\n"
        "👹 HP: " + str(monster_hp) + "/" + str(monster_max) + "\n"
        "[" + bar + "]\n\n"
        "❤️ Твоё HP: " + str(player['hp']) + "/100\n"
        "⚡ Энергия: " + str(player['energy']) + "/100"
    )
    return text


async def show_combat(callback: CallbackQuery, user_id: int, lang: str):
    """Показать бой."""
    from core.bot_helpers import edit_main, make_bot
    from config import BOT_TOKEN
    from aiogram import Bot

    combat = get_active_combat(user_id)
    if not combat:
        await callback.answer(t("combat.no_combat", lang), show_alert=True)
        return

    player = get_player(user_id)
    session = player.get("current_session", "")
    text = render_combat(lang, combat, player)
    kb = combat_keyboard(lang, session)

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)
    finally:
        await bot.session.close()
    await callback.answer()


async def start_combat_ui(callback: CallbackQuery, user_id: int, monster_type: str,
                          section_id: str, layer: int):
    """Начать бой."""
    start_combat(user_id, monster_type, section_id, layer)
    player = get_player(user_id)
    await show_combat(callback, user_id, player["language"])


# ============ Действия ============

async def on_attack(callback: CallbackQuery):
    from core.bot_helpers import check_session, refresh_main, edit_main
    from config import BOT_TOKEN
    from aiogram import Bot

    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    try:
        result = player_attack(user_id)
    except CombatError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    if result.get("victory"):
        combat = get_active_combat(user_id)
        monster_type = combat["monster_type"] if combat else "young"
        rewards = give_victory_rewards(user_id, monster_type)

        reward_lines = []
        icons = {"tokens": "🪙", "meat": "🥩", "metal": "⚙️", "fragment": "🗺️"}
        for k, v in result.get("rewards", {}).items():
            reward_lines.append(f"{icons.get(k, k)} +{v}")

        text = (
            "🏆 <b>" + t('combat.victory', lang) + "</b>\n\n"
            + t('combat.victory_rewards', lang) + "\n"
            + "\n".join(reward_lines)
        )

        session = player.get("current_session", "")
        s = f":{session}" if session else ""
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("combat.btn_continue", lang),
                                  callback_data=f"maze:back{s}")
        ]])

        bot = make_bot()
        try:
            await edit_main(bot, user_id, text, kb)
        finally:
            await bot.session.close()
        await callback.answer(t("combat.won", lang))
        return

    counter = result.get("counter", {})
    if counter.get("player_dead"):
        await _handle_death(callback, user_id, lang)
        return

    await callback.answer(
        t("combat.attack_result", lang,
          dmg=result["player_damage"],
          counter=counter.get("damage", 0))
    )
    await show_combat(callback, user_id, lang)


async def on_defend(callback: CallbackQuery):
    from core.bot_helpers import check_session
    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    try:
        result = player_defend(user_id)
    except CombatError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    if result.get("player_dead"):
        await _handle_death(callback, user_id, lang)
        return

    await callback.answer(t("combat.defend_result", lang, dmg=result["monster_damage"]))
    await show_combat(callback, user_id, lang)


async def on_flee(callback: CallbackQuery):
    from core.bot_helpers import check_session, refresh_main
    from config import BOT_TOKEN
    from aiogram import Bot

    user_id = callback.from_user.id
    player = get_player(user_id)
    lang = player["language"]

    if not check_session(user_id, callback.data):
        await callback.answer(t("log.stale", lang), show_alert=True)
        return

    try:
        result = player_flee(user_id)
    except CombatError as e:
        await callback.answer(t(e.key, lang, **e.kwargs), show_alert=True)
        return

    if result.get("success"):
        await callback.answer(t("combat.fled", lang), show_alert=True)
        bot = make_bot()
        try:
            await refresh_main(bot, user_id)
        finally:
            await bot.session.close()
        return

    counter = result.get("counter", {})
    if counter.get("player_dead"):
        await _handle_death(callback, user_id, lang)
        return

    await callback.answer(t("combat.flee_failed", lang, dmg=counter.get("damage", 0)), show_alert=True)
    await show_combat(callback, user_id, lang)


async def _handle_death(callback, user_id, lang):
    """Смерть."""
    from services.death import die_in_maze, random_death_message, random_global_death_message
    from core.bot_helpers import edit_main
    from config import BOT_TOKEN
    from aiogram import Bot

    try:
        die_in_maze(user_id)
    except Exception:
        pass

    personal = random_death_message(lang)
    text = (
        "💀 <b>" + t('death.title', lang) + "</b>\n\n"
        "<i>" + personal + "</i>\n\n"
        + t('death.respawn_info', lang)
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("death.btn_respawn", lang), callback_data="nav:back")
    ]])

    bot = make_bot()
    try:
        await edit_main(bot, user_id, text, kb)

        # Уведомление всем
        from db.connection import get_conn

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id, language FROM players WHERE user_id != ?", (user_id,))
        all_players = cur.fetchall()
        conn.close()

        for uid, ulang in all_players:
            try:
                await bot.send_message(chat_id=uid, text=random_global_death_message(ulang))
            except Exception:
                pass
    finally:
        await bot.session.close()
