# handlers/maps_states.py

from aiogram.fsm.state import State, StatesGroup


class CreateMapState(StatesGroup):
    waiting_for_name = State()


class RenameMapState(StatesGroup):
    waiting_for_name = State()
