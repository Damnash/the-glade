# utils/decorators.py

from functools import wraps

from aiogram.types import Message

from config import ADMIN_IDS


def admin_only(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("⛔ Access denied.")
            return
        return await func(message, *args, **kwargs)
    return wrapper