# handlers/eat.py

from aiogram.types import Message

from core.i18n import t
from db.players import get_lang
from services.eat import eat, EatError


async def cmd_eat(message: Message):
    lang = get_lang(message.from_user.id)
    
    try:
        await message.delete()
    except Exception:
        pass

    try:
        result = eat(message.from_user.id)
    except EatError as e:
        await message.answer(t(e.key, lang, **e.kwargs))
        return

    await message.answer(t("eat.done", lang, food=result["food"]))