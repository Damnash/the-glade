# handlers/time_cmd.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from core.daycycle import get_current_phase, get_phase_spec, get_time_str
from db.players import get_lang
from core.bot_helpers import command_reply


async def cmd_time(message: Message):
    """/время — текущее время суток."""
    lang = get_lang(message.from_user.id)

    phase = get_current_phase()
    spec = get_phase_spec(phase)
    time_str = get_time_str()

    text = (
        f"{t('time.cmd.title', lang)}\n\n"
        + t("time.cmd.line", lang, time=time_str) + "\n"
        + t("time.cmd.phase", lang,
            phase=f"{spec['icon']} {t(spec['key'], lang)}") + "\n\n"
        + t("time.cmd.hint", lang)
    )

    await command_reply(text)

    # Вернуть контекст
    from handlers.location_render import send_current_context
    await send_current_context(message, message.from_user.id)

    # command_reply импортируется в шапке файла
