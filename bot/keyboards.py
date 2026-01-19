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
    """Головні категорії стилів (тематики)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💙 Lavstory",
                    callback_data="theme:lavstory"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💛 Для неї",
                    callback_data="theme:for_her"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔥 18+ шаблон",
                    callback_data="theme:adult18"
                )
            ],
        ]
    )


# ===============================
# Клавіатури вибору тем для кожної тематики
# ===============================

def lavstory_themes_kb() -> InlineKeyboardMarkup:
    """Теми для Lavstory"""
    themes = [
        ("💒 Весільний", "vesilnyi"),
        ("💕 Інша подія", "insha_podiya"),
        ("🎂 Річниця", "richnytsia"),
    ]
    rows = [[InlineKeyboardButton(text=label, callback_data=f"category:lavstory:{key}")]
            for label, key in themes]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:styles")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def for_her_themes_kb() -> InlineKeyboardMarkup:
    """Теми для 'Для неї' - всі доступні категорії"""
    themes = [
        ("💼 Бізнес", "biznes"),
        ("🔮 Гороскоп", "horoskop"),
        ("👯 Дружба", "druzhba"),
        ("🎂 День народження", "z_dnem_narodzhennia"),
        ("💪 Здоров'я", "zdorovya"),
        ("📝 Значення імені", "znachennia_imeni"),
        ("📚 Книги", "knyhy"),
        ("💌 Лист", "lyst"),
        ("👗 Мода", "moda"),
        ("🎵 Музика", "muzyka"),
        ("🎓 Навчання", "navchannia"),
        ("✈️ Подорожі", "podorozhi"),
        ("🧠 Психологія", "psykholohiya"),
        ("🍳 Рецепти", "retsepty"),
        ("👨‍👩‍👧 Сім'я", "simya"),
        ("📈 Саморозвиток", "samorozvytok"),
        ("💑 Стосунки", "stosunky"),
        ("💃 Танці", "tantsi"),
        ("🎬 Фільми", "filmy"),
        ("🌟 Універсальні", "universalni"),
    ]
    # Розбиваємо на 2 колонки для кращого вигляду
    rows = []
    for i in range(0, len(themes), 2):
        row = [InlineKeyboardButton(text=themes[i][0], callback_data=f"category:for_her:{themes[i][1]}")]
        if i + 1 < len(themes):
            row.append(InlineKeyboardButton(text=themes[i+1][0], callback_data=f"category:for_her:{themes[i+1][1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:styles")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def adult18_themes_kb() -> InlineKeyboardMarkup:
    """Теми для 18+ (поки що одна)"""
    rows = [
        [InlineKeyboardButton(text="🔥 18+ шаблон", callback_data="category:adult18:adult18_shablon")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:styles")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ===============================
# Клавіатура вибору кількості сторінок
# ===============================
def pages_kb(recommended: int) -> InlineKeyboardMarkup:
    """Клавіатура вибору кількості сторінок з рекомендацією"""
    options = [12, 16, 20, 24, 32, 36, 40, 50]

    rows = []
    for p in options:
        label = f"{p} сторінок"
        if p == recommended:
            label = f"⭐ {p} (рекомендовано)"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"pages:{p}")])

    return InlineKeyboardMarkup(inline_keyboard=rows)
