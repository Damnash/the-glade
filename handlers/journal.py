# handlers/journal.py

from aiogram.filters import Command
from aiogram.types import Message

from core.i18n import t
from db.players import get_player, get_lang
from services.event_log import get_recent_events


async def cmd_journal(message: Message):
    """/journal — история событий (чат, радио, клан, бой, находки)."""
    user_id = message.from_user.id
    lang = get_lang(user_id)
    player = get_player(user_id)

    if not player:
        await message.answer(t("start.need_start", lang))
        return

    events = get_recent_events(user_id, limit=50)
    if not events:
        await message.answer(t("journal.empty", lang))
        return

    lines = [f"📖 <b>{t('journal.header', lang)}</b>\n"]
    for e in events:
        lines.append(e["text"])

    await message.answer("\n".join(lines))
