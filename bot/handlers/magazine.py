# ============================================
#   AIZINE MagazineBot — magazine.py (FINAL)
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
from bot.keyboards import photos_done_kb, styles_kb

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
def write_job_json(job_dirs, job_id, style_key, user):
    """Створює job.json перед запуском пайплайна."""

    if style_key == "lavstory_insha_podiya":
        theme = "lavstory"
        category = "insha_podiya"
    elif style_key == "for_her_universalni":
        theme = "for_her"
        category = "universalni"
    else:
        theme = "adult18"
        category = "adult18_shablon"

    meta = {
        "job_id": job_id,
        "theme": theme,
        "category": category,
        "pages": 16,
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
    else:
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

    dest = job_dirs["input"] / f"photo_{len(photos) + 1:03d}{ext}"
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
    await message.answer("✨ Обери стиль:", reply_markup=styles_kb())


# =============================
# CHOOSE STYLE → START PIPELINE
# =============================
@router.callback_query(
    StateFilter(MagazineFSM.waiting_style),
    F.data.startswith("style:"),
)
async def chosen_style(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    style_key = callback.data.split(":", 1)[1]
    data = await state.get_data()

    job_id = data["job_id"]
    job_dirs = {k: Path(v) for k, v in data["job_dirs"].items()}
    username = callback.from_user.full_name

    write_job_json(job_dirs, job_id, style_key, username)

    await state.set_state(MagazineFSM.processing)
    await callback.message.answer("Генерую журнал… це займе 1–3 хвилини ⏳")

    async def task():
        try:
            pdf = await asyncio.to_thread(run_pipeline, job_id)
            await callback.message.answer_document(
                FSInputFile(str(pdf)),
                caption="Готово! 📕",
            )
        except Exception as e:
            logger.exception("Magazine generation failed", exc_info=e)
            await callback.message.answer(f"😔 Сталася помилка: {e}")
        finally:
            await state.clear()

    asyncio.create_task(task())
    await asyncio.sleep(0.1)
