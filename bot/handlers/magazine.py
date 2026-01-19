# ============================================
#   AIZINE MagazineBot — magazine.py (v2)
#   With theme selection, page count, spreads
# ============================================

import asyncio
import json
import uuid
import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile

from bot.config import settings
from bot.states import MagazineFSM
from bot.keyboards import (
    photos_done_kb,
    styles_kb,
    lavstory_themes_kb,
    for_her_themes_kb,
    adult18_themes_kb,
    pages_kb,
)

from orchestrator.run_job import (
    run_build_plan,
    run_indesign,
    verify_output,
    make_zip,
)

router = Router()
logger = logging.getLogger(__name__)


# =============================
# JOB DIRECTORIES
# =============================
def create_dirs(job_id: str):
    root = settings.jobs_dir / job_id
    paths = {
        "root": root,
        "input": root / "input",
        "meta": root / "meta",
        "output": root / "output",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


# =============================
# META JSON
# =============================
def write_job_json(job_dirs, job_id, theme: str, category: str, pages: int, user: str, photo_count: int = 0):
    """Створює job.json перед запуском пайплайна."""

    meta = {
        "job_id": job_id,
        "theme": theme,
        "category": category,
        "pages": pages,
        "photo_count": photo_count,
        "client_name": user,
    }

    with (job_dirs["meta"] / "job.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# =============================
# PIPELINE
# =============================
def run_pipeline(job_id: str) -> Path:
    """Запускає весь процес створення журналу."""
    plan_path = run_build_plan(job_id)
    run_indesign(str(plan_path))

    # 🔥 ВИПРАВЛЕНО: verify_output повертає тільки PDF
    pdf = verify_output(job_id)

    make_zip(job_id)
    return pdf


# =============================
# /start
# =============================
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(MagazineFSM.waiting_photos)

    await message.answer(
        "👋 Привіт!\n"
        "Надішли мені 1–50 фото (можна альбомами).\n"
        "Коли завершиш — натисни «✅ Досить, далі».",
        reply_markup=photos_done_kb(),
    )


# =============================
# UNIVERSAL PHOTO SAVER
# =============================
async def save_photo(message: Message, state: FSMContext):
    """Зберігає одне фото у jobs/<id>/input/"""

    data = await state.get_data()
    job_id = data.get("job_id")

    if not job_id:
        job_id = f"{message.from_user.id}_{uuid.uuid4().hex[:6]}"
        job_dirs = create_dirs(job_id)
        await state.update_data(
            job_id=job_id,
            job_dirs={k: str(v) for k, v in job_dirs.items()},
            photos=[],
        )
        data = await state.get_data()  # refresh data after update

    job_dirs = {k: Path(v) for k, v in data["job_dirs"].items()}
    photos = data.get("photos", [])

    if len(photos) >= settings.max_photos:
        await message.answer(
            f"⚠️ Досягнуто ліміт {settings.max_photos} фото.\n"
            "Натисни «✅ Досить, далі», щоб продовжити."
        )
        return

    file = None
    ext = ".jpg"

    if message.photo:
        file = message.photo[-1]
    elif message.document:
        if not (message.document.mime_type or "").startswith("image"):
            return
        file = message.document
        ext = Path(message.document.file_name or "").suffix or ".jpg"

    if not file:
        return

    # Use UUID to avoid race condition with albums (media groups)
    unique_id = uuid.uuid4().hex[:8]
    dest = job_dirs["input"] / f"photo_{unique_id}{ext}"
    await message.bot.download(file, destination=dest)

    photos.append(dest.name)
    await state.update_data(photos=photos)

    logger.info("Saved photo %s (total=%s)", dest.name, len(photos))

    await message.answer(
        f"📸 Фото прийнято ({len(photos)}/{settings.max_photos})",
        reply_markup=photos_done_kb(),
    )


# =============================
# PHOTO HANDLER
# =============================
@router.message(
    StateFilter(MagazineFSM.waiting_photos),
    F.photo | F.document,
)
async def handle_photo(message: Message, state: FSMContext):
    logger.info(
        "Got content: photo=%s doc=%s media_group_id=%s",
        bool(message.photo),
        bool(message.document),
        message.media_group_id,
    )
    await save_photo(message, state)


# =============================
# BUTTON: "ДОСИТЬ"
# =============================
@router.message(
    StateFilter(MagazineFSM.waiting_photos),
    F.text.contains("Досить"),
)
async def done_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("photos"):
        await message.answer("Спочатку надішли хоч одне фото 🙂")
        return

    await state.set_state(MagazineFSM.waiting_style)
    await message.answer("✨ Обери тематику:", reply_markup=styles_kb())


# =============================
# STEP 2: CHOOSE THEME CATEGORY (Lavstory / For Her / 18+)
# =============================
@router.callback_query(
    StateFilter(MagazineFSM.waiting_style),
    F.data.startswith("theme:"),
)
async def chosen_theme_category(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    theme = callback.data.split(":", 1)[1]  # lavstory / for_her / adult18
    await state.update_data(theme=theme)

    # Показуємо теми для вибраної тематики
    await state.set_state(MagazineFSM.waiting_theme)

    if theme == "lavstory":
        await callback.message.edit_text("💙 Обери тему Lavstory:", reply_markup=lavstory_themes_kb())
    elif theme == "for_her":
        await callback.message.edit_text("💛 Обери тему:", reply_markup=for_her_themes_kb())
    else:  # adult18
        await callback.message.edit_text("🔥 Обери тему 18+:", reply_markup=adult18_themes_kb())


# =============================
# BACK BUTTON → Return to styles
# =============================
@router.callback_query(
    StateFilter(MagazineFSM.waiting_theme, MagazineFSM.waiting_pages),
    F.data == "back:styles",
)
async def back_to_styles(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(MagazineFSM.waiting_style)
    await callback.message.edit_text("✨ Обери тематику:", reply_markup=styles_kb())


# =============================
# STEP 3: CHOOSE SPECIFIC THEME (category)
# =============================
@router.callback_query(
    StateFilter(MagazineFSM.waiting_theme),
    F.data.startswith("category:"),
)
async def chosen_category(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # category:lavstory:insha_podiya -> theme=lavstory, category=insha_podiya
    parts = callback.data.split(":")
    theme = parts[1]
    category = parts[2]

    await state.update_data(theme=theme, category=category)

    # Розраховуємо рекомендовану кількість сторінок
    data = await state.get_data()
    photo_count = len(data.get("photos", []))

    # Рекомендація: photo_count округлене до найближчого доступного
    options = [12, 16, 20, 24, 32, 36, 40, 50]
    recommended = min(options, key=lambda x: abs(x - photo_count)) if photo_count > 0 else 16

    await state.set_state(MagazineFSM.waiting_pages)
    await callback.message.edit_text(
        f"📄 Обери кількість сторінок:\n"
        f"(У тебе {photo_count} фото)",
        reply_markup=pages_kb(recommended)
    )


# =============================
# STEP 4: CHOOSE PAGE COUNT → START PIPELINE
# =============================
@router.callback_query(
    StateFilter(MagazineFSM.waiting_pages),
    F.data.startswith("pages:"),
)
async def chosen_pages(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    pages = int(callback.data.split(":", 1)[1])
    data = await state.get_data()

    job_id = data["job_id"]
    job_dirs = {k: Path(v) for k, v in data["job_dirs"].items()}
    username = callback.from_user.full_name
    photo_count = len(data.get("photos", []))
    theme = data.get("theme", "adult18")
    category = data.get("category", "adult18_shablon")

    write_job_json(job_dirs, job_id, theme, category, pages, username, photo_count)

    await state.set_state(MagazineFSM.processing)
    await callback.message.edit_text("⏳ Генерую журнал… це займе 1–3 хвилини")

    async def task():
        try:
            pdf = await asyncio.to_thread(run_pipeline, job_id)

            # Надсилаємо превью по розворотах
            await send_spreads_preview(callback, pdf)

            # Потім надсилаємо повний PDF
            await callback.message.answer_document(
                FSInputFile(str(pdf)),
                caption="📕 Повний PDF журналу:",
            )

            # Надсилаємо INDD для редагування
            indd = pdf.with_suffix(".indd")
            if indd.exists():
                await callback.message.answer_document(
                    FSInputFile(str(indd)),
                    caption="📝 INDD файл для редагування:",
                )

        except Exception as e:
            logger.exception("Magazine generation failed", exc_info=e)
            await callback.message.answer(f"😔 Сталася помилка: {e}")
        finally:
            await state.clear()

    asyncio.create_task(task())
    await asyncio.sleep(0.1)


# =============================
# SEND SPREADS PREVIEW
# =============================
async def send_spreads_preview(callback: CallbackQuery, pdf_path: Path):
    """Надсилає превью журналу по розворотах (2 сторінки)."""
    try:
        from pdf2image import convert_from_path

        output_dir = pdf_path.parent
        spreads_dir = output_dir / "spreads"
        spreads_dir.mkdir(exist_ok=True)

        # Конвертуємо PDF в зображення
        pages = convert_from_path(str(pdf_path), dpi=150)

        if not pages:
            logger.warning("No pages converted from PDF")
            return

        await callback.message.answer("📖 Превью по розворотах:")

        # Створюємо розвороти (по 2 сторінки)
        spread_num = 1
        i = 0

        while i < len(pages):
            if i == 0:
                # Перша сторінка (обкладинка) - окремо
                spread_path = spreads_dir / f"spread_{spread_num:02d}.jpg"
                pages[0].save(str(spread_path), "JPEG", quality=85)
                await callback.message.answer_photo(
                    FSInputFile(str(spread_path)),
                    caption=f"📄 Обкладинка"
                )
                i += 1
                spread_num += 1
            elif i == len(pages) - 1:
                # Остання сторінка (задня обкладинка) - окремо
                spread_path = spreads_dir / f"spread_{spread_num:02d}.jpg"
                pages[i].save(str(spread_path), "JPEG", quality=85)
                await callback.message.answer_photo(
                    FSInputFile(str(spread_path)),
                    caption=f"📄 Задня обкладинка"
                )
                i += 1
                spread_num += 1
            else:
                # Внутрішні сторінки - по 2 (розворот)
                from PIL import Image

                left_page = pages[i]
                right_page = pages[i + 1] if i + 1 < len(pages) - 1 else None

                if right_page:
                    # Об'єднуємо 2 сторінки в розворот
                    width = left_page.width + right_page.width
                    height = max(left_page.height, right_page.height)
                    spread = Image.new("RGB", (width, height), "white")
                    spread.paste(left_page, (0, 0))
                    spread.paste(right_page, (left_page.width, 0))

                    spread_path = spreads_dir / f"spread_{spread_num:02d}.jpg"
                    spread.save(str(spread_path), "JPEG", quality=85)
                    await callback.message.answer_photo(
                        FSInputFile(str(spread_path)),
                        caption=f"📖 Розворот {spread_num - 1} (стор. {i + 1}-{i + 2})"
                    )
                    i += 2
                else:
                    # Непарна сторінка
                    spread_path = spreads_dir / f"spread_{spread_num:02d}.jpg"
                    left_page.save(str(spread_path), "JPEG", quality=85)
                    await callback.message.answer_photo(
                        FSInputFile(str(spread_path)),
                        caption=f"📄 Сторінка {i + 1}"
                    )
                    i += 1
                spread_num += 1

            # Невелика затримка щоб не перевантажувати Telegram
            await asyncio.sleep(0.3)

    except ImportError:
        logger.warning("pdf2image not installed, skipping spreads preview")
        await callback.message.answer("📕 Журнал готовий! (превью розворотів недоступне)")
    except Exception as e:
        logger.warning(f"Failed to generate spreads preview: {e}")
        await callback.message.answer("📕 Журнал готовий!")
