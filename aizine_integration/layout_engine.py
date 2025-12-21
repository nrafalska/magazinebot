import json
from pathlib import Path
import random

LAYOUTS_DIR = Path("data/layouts")


def load_all_layouts():
    layouts = {}
    for file in LAYOUTS_DIR.glob("*.json"):
        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        layouts[file.stem] = data
    return layouts


def choose_layouts(theme: str, pages_count: int, photos_count: int):
    """Вибирає сторінки з JSON-Layout файлів автоматично"""

    layouts = load_all_layouts()

    # фільтруємо по темі
    items = [l for name, l in layouts.items() if name.startswith(theme)]
    if not items:
        raise ValueError(f"No layouts found for theme '{theme}'")

    chosen = []
    remaining_photos = photos_count

    # обираємо COVER
    cover = [p for p in items[0]["pages"] if "cover" in p["type"].lower()]
    if cover:
        chosen.append(cover[0])
        if "photo_slots" in cover[0]:
            remaining_photos -= len(cover[0]["photo_slots"])

    # обираємо інші сторінки
    pool = items[0]["pages"]

    for p in pool:
        if len(chosen) >= pages_count:
            break

        # не додаємо 2-гу обкладинку
        if "cover" in p["type"].lower():
            continue

        chosen.append(p)

        if "photo_slots" in p:
            remaining_photos -= len(p["photo_slots"])

        if remaining_photos <= 0:
            break

    return chosen


def build_page_plan(selected_pages, photos):
    plan = []
    photo_index = 0

    for page in selected_pages:
        page_item = {
            "page_id": page["id"],
            "type": page["type"],
            "images": [],
            "texts": [],
        }

        # вставляємо фото
        for slot in page.get("photo_slots", []):
            if photo_index >= len(photos):
                break
            page_item["images"].append({
                "file": photos[photo_index],
                "slot": slot
            })
            photo_index += 1

        # текстові поля
        for slot in page.get("text_slots", []):
            page_item["texts"].append(slot)

        plan.append(page_item)

    return plan
