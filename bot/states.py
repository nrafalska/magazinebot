# bot/states.py
from aiogram.fsm.state import StatesGroup, State


class MagazineFSM(StatesGroup):
    # 1) Користувач надсилає фото
    waiting_photos = State()

    # 2) Користувач обирає стиль (Lavstory / Для неї / 18+)
    waiting_style = State()

    # 3) Бот пропонує кількість сторінок → юзер обирає
    waiting_pages = State()

    # 4) Генерація журналу (InDesign)
    processing = State()
