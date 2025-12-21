"""
MagazineBot Configuration
Завантажує налаштування з .env файлу
"""

import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv

# Завантажуємо .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


@dataclass
class Config:
    """Конфігурація бота"""

    # Telegram
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_chat_id: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

    # InDesign
    indesign_path: str = os.getenv(
        "INDESIGN_PATH",
        r"C:\Program Files\Adobe\Adobe InDesign 2024\InDesign.exe",
    )

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    templates_dir: Path = Path(os.getenv("TEMPLATES_DIR", "")) or base_dir / "data" / "templates"
    jobs_dir: Path = Path(os.getenv("JOBS_DIR", "")) or base_dir / "jobs"
    aizine_dir: Path = Path(os.getenv("AIZINE_DIR", "")) or base_dir / "scripts"

    # Limits
    max_photos: int = int(os.getenv("MAX_PHOTOS", "50"))
    generation_timeout: int = int(os.getenv("GENERATION_TIMEOUT", "300"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self):
        """Створюємо папки якщо не існують"""
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        """Перевіряє конфігурацію, повертає список помилок"""
        errors: list[str] = []

        if not self.bot_token:
            errors.append("BOT_TOKEN не встановлено")

        if not self.admin_chat_id:
            errors.append("ADMIN_CHAT_ID не встановлено")

        if not Path(self.indesign_path).exists():
            errors.append(f"InDesign не знайдено: {self.indesign_path}")

        return errors


# Глобальний інстанс (важливо: саме settings)
settings = Config()


# Теми журналів
THEMES = {
    "love_story": "💕 Love Story",
    "family": "👨‍👩‍👧‍👦 Family",
    "wedding": "💒 Wedding",
    "18_plus": "🔞 18+",
    "custom": "✨ Custom",
}

# Кількість сторінок
PAGE_OPTIONS = [12, 16, 20, 24]


# Статуси замовлення
class JobStatus:
    PENDING = "pending"         # Очікує обробки
    COLLECTING = "collecting"   # Збір фото
    PROCESSING = "processing"   # Генерація
    COMPLETED = "completed"     # Готово
    FAILED = "failed"           # Помилка
    CANCELLED = "cancelled"     # Скасовано


# Повідомлення бота (українською)
MESSAGES = {
    "welcome": (
        "👋 Вітаю! Я MagazineBot.\n\n"
        "Я допоможу створити твій унікальний журнал з фото.\n\n"
        "Натисни /start щоб почати."
    ),
    "new_order": (
        "📖 Новий журнал\n\n"
        "Обери тему журналу:"
    ),
    "select_pages": (
        "📄 Скільки сторінок?\n\n"
        "Рекомендовано: мінімум 3-4 фото на розворот."
    ),
    "enter_name": (
        "✍️ Введи назву журналу або імена:\n\n"
        "Наприклад: «Анна і Максим» або «Our Love Story»"
    ),
    "upload_photos": (
        "📷 Тепер надішли фото для журналу.\n\n"
        "• Можеш надсилати по одному або групою\n"
        "• Мінімум: {min_photos} фото\n"
        "• Максимум: {max_photos} фото\n\n"
        "Коли завантажиш усі — натисни «✅ Готово»"
    ),
    "photo_received": "📷 Отримано: {count}/{max} фото",
    "not_enough_photos": (
        "⚠️ Замало фото!\n\n"
        "Для {pages} сторінок потрібно мінімум {min_photos} фото.\n"
        "Зараз: {count}"
    ),
    "processing": (
        "⏳ Генерую твій журнал...\n\n"
        "Це займе 1–3 хвилини. Я напишу, коли буде готово!"
    ),
    "completed": (
        "🎉 Твій журнал готовий!\n\n"
        "📖 {title}\n"
        "📄 {pages} сторінок\n"
        "📷 {photo_count} фото\n\n"
        "Дякую, що скористався MagazineBot! 💕"
    ),
    "error": (
        "😔 Щось пішло не так.\n\n"
        "Помилка: {error}\n\n"
        "Спробуй ще раз або напиши адміну."
    ),
    "cancelled": "❌ Замовлення скасовано.",
    "admin_new_order": (
        "🆕 Нове замовлення!\n\n"
        "ID: `{job_id}`\n"
        "Клієнт: @{username} ({telegram_id})\n"
        "Тема: {theme}\n"
        "Сторінок: {pages}\n"
        "Фото: {photo_count}\n\n"
        "Статус: {status}"
    ),
}
