# handlers/season_cmd.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from db.players import get_lang
from services.season_manager import get_season_info
from core.bot_helpers import command_reply


async def cmd_season(message: Message):
    """/сезон — информация о сезоне."""
    lang = get_lang(message.from_user.id)

    info = get_season_info()

    text = (
        f"📅 <b>{t('season.title', lang)}</b>\n\n"
        + t("season.line", lang,
            season=info["season_id"],
            day=info["day"],
            total=info["total_days"]) + "\n"
        + t("season.days_left", lang, days=info["days_left"]) + "\n"
        + t("season.layers", lang, n=info["layers_unlocked"]) + "\n\n"
        + t("season.hint", lang)
    )

    await command_reply(text)

    # Вернуть контекст
    from handlers.location_render import send_current_context
    await send_current_context(message, message.from_user.id)

    # command_reply импортируется в шапке файла
