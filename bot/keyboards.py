# bot/keyboards.py
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def photos_done_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Досить, далі")],
            [KeyboardButton(text="❌ Скасувати")],
        ],
        resize_keyboard=True
    )


def styles_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💙 Lavstory",
                    callback_data="style:lavstory_insha_podiya"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💛 Для неї / Універсальні",
                    callback_data="style:for_her_universalni"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔥 18+ шаблон",
                    callback_data="style:adult18_default"
                )
            ],
        ]
    )


# ===============================
# Клавіатура вибору кількості сторінок
# ===============================
def pages_kb(recommended: int) -> InlineKeyboardMarkup:
    options = [12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 60]

    rows = []
    for p in options:
        label = f"{p} сторінок"
        if p == recommended:
            label = f"⭐ {p} рекомендовано"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"pages:{p}")])

    return InlineKeyboardMarkup(inline_keyboard=rows)
