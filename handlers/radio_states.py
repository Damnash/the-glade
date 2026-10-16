# handlers/radio_states.py

from aiogram.fsm.state import State, StatesGroup


class RadioTalkState(StatesGroup):
    waiting_for_message = State()
