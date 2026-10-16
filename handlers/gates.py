# handlers/gates.py

from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from core.i18n import t
from core.maze_current import get_current_season
from db.players import get_player, get_lang
from services.achievements import try_open_gates, get_gates_info
from core.bot_helpers import make_bot


async def cmd_gates(message: Message):
    """/врата — попытка открыть Врата."""
    user_id = message.from_user.id
    player = get_player(user_id)
    lang = get_lang(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    # Уже открыты?
    info = get_gates_info()
    if info["is_open"]:
        await message.answer(t("gates.already_open", lang))
        return

    # Пытаемся открыть
    result = try_open_gates(user_id)

    if not result:
        # Причины
        season = get_current_season()
        from db.keys import has_player_key

        # Все ли ключи?
        missing = []
        for k in [1, 2, 3, 4, 5]:
            if not has_player_key(season, user_id, k):
                missing.append(k)

        if missing:
            keys_str = ", ".join(t(f"key.{k}.name", lang) for k in missing)
            await message.answer(t("gates.missing_keys", lang, keys=keys_str))
            return

        # Не в центре
        if player.get("maze_layer", 0) == 0:
            await message.answer(t("gates.not_in_maze", lang))
            return

        from db.maze_map import get_section
        section = get_section(season, player.get("maze_layer", 1), player.get("maze_section"))
        if not section or section["type"] != "center":
            await message.answer(t("gates.not_in_center", lang))
            return

        # Не хватает игроков
        from core.season import get_tier_config
        tier = get_tier_config()
        await message.answer(
            t("gates.not_enough_players", lang, need=tier.get("players_at_gates", 1))
        )
        return

    # Победа!
    from db.players import get_player as _gp

    winner_names = []
    for wid in result["winners"]:
        w = _gp(wid)
        if w:
            winner_names.append(w["display_name"] or w["username"])

    text = (
        f"🌟 <b>{t('gates.victory_title', lang)}</b>\n\n"
        + t("gates.victory_text", lang) + "\n\n"
        + t("gates.winners", lang, names=", ".join(winner_names)) + "\n\n"
        + t("gates.victory_final", lang)
    )

    await message.answer(text)

    # Всем игрокам
    from aiogram import Bot
    from config import BOT_TOKEN
    from db.connection import get_conn

    bot = make_bot()
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM players WHERE user_id != ?", (user_id,))
        all_players = cur.fetchall()
        conn.close()

        for (uid,) in all_players:
            try:
                ulang = get_lang(uid)
                await bot.send_message(
                    chat_id=uid,
                    text=t("gates.broadcast", ulang, names=", ".join(winner_names)),
                )
            except Exception:
                pass
    finally:
        await bot.session.close()
