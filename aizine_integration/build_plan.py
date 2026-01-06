import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ===== Configuration =====

BASE_DIR = Path(os.getenv("MAGAZINEBOT_DIR", Path(__file__).parent.parent))
JOBS_DIR = Path(os.getenv("JOBS_DIR", BASE_DIR / "jobs"))
TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", BASE_DIR / "data" / "templates"))
CONFIG_DIR = BASE_DIR / "data" / "config"


def log(msg: str, verbose: bool):
    """Prints when verbose=True (ASCII only)"""
    if verbose:
        print("[debug] " + msg)


def load_templates_map(verbose=False) -> dict:
    map_path = CONFIG_DIR / "templates_map.json"

    log(f"Loading templates map from {map_path}", verbose)

    if map_path.exists():
        with open(map_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            log("Loaded templates_map keys: " + str(list(data.keys())), verbose)
            return data

    log("templates_map.json not found, using default", verbose)

    # fallback на випадок, якщо json відсутній
    return {
        "custom": {
            "default": "data/templates/adult18/adult18.indd"
        }
    }


def get_template_path(theme: str, category: str | None, pages: int, verbose=False) -> Path | None:
    templates_map = load_templates_map(verbose)

    log(f"Requested theme={theme}, category={category}, pages={pages}", verbose)

    theme_block = templates_map.get(theme)
    if not theme_block:
        log(f"Theme '{theme}' not found in templates_map.json", verbose)
        return None

    # Випадок theme -> { "default": "data/templates/..." }
    if isinstance(theme_block, dict) and "default" in theme_block:
        return BASE_DIR / theme_block["default"]

    templates_list = theme_block if isinstance(theme_block, list) else []

    # exact category + pages
    if category:
        for item in templates_list:
            if item.get("name") == category and item.get("pages") == pages:
                log(f"Matched exact category-pages template: {item['path']}", verbose)
                return BASE_DIR / item["path"]

    # match by pages only
    for item in templates_list:
        if item.get("pages") == pages:
            log(f"Matched pages-only template: {item['path']}", verbose)
            return BASE_DIR / item["path"]

    # fallback
    if templates_list:
        log(f"Falling back to first template: {templates_list[0]['path']}", verbose)
        return BASE_DIR / templates_list[0]["path"]

    log("No matching template found", verbose)
    return None


def analyze_photos(input_dir: Path, verbose=False) -> list[dict]:
    photos = []
    supported_ext = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

    if not input_dir.exists():
        log(f"Input photo directory not found: {input_dir}", verbose)
        return photos

    log(f"Scanning photos in {input_dir}", verbose)

    for file_path in sorted(input_dir.iterdir()):
        if file_path.suffix.lower() not in supported_ext:
            continue

        photo_info = {
            "path": str(file_path.absolute()),
            "filename": file_path.name,
        }

        try:
            from PIL import Image
            with Image.open(file_path) as img:
                w, h = img.size
                photo_info["width"] = w
                photo_info["height"] = h

                ratio = h / w if w else 1
                if ratio > 1.2:
                    photo_info["orientation"] = "vertical"
                elif ratio < 0.8:
                    photo_info["orientation"] = "horizontal"
                else:
                    photo_info["orientation"] = "square"

        except Exception:
            photo_info["orientation"] = "unknown"

        photos.append(photo_info)

    log(f"Found {len(photos)} photos", verbose)
    return photos


def calculate_pages_for_photos(photo_count: int, verbose=False) -> int:
    """
    Розраховує кількість сторінок на основі кількості фото.
    - 1 фото на обкладинку
    - до 3 фото на внутрішню сторінку
    - 1 фото на задню обкладинку
    - Мінімум 4 сторінки, завжди парне число
    """
    if photo_count <= 0:
        return 4

    # Cover = 1, Back = 1, решта = internal
    internal_photos = max(0, photo_count - 2)

    # До 3 фото на сторінку
    internal_pages = (internal_photos + 2) // 3  # ceil division

    # Cover (1) + internal + back (1)
    total = 1 + internal_pages + 1

    # Мінімум 4 сторінки
    if total < 4:
        total = 4

    # Парне число для друку
    if total % 2 != 0:
        total += 1

    log(f"Photos: {photo_count} -> Pages: {total}", verbose)
    return total


def generate_placements(photos: list[dict], pages: int, verbose=False) -> tuple[list[dict], int]:
    """
    Генерує placements та повертає (placements, actual_pages).
    """
    placements = []
    if not photos:
        return placements, 4

    log("Generating placements", verbose)

    # 1) Обкладинка — беремо перше вертикальне, або перше фото
    vertical = [p for p in photos if p.get("orientation") == "vertical"]
    cover_photo = vertical[0] if vertical else photos[0]

    placements.append({
        "label": "COVER_IMAGE",
        "photo": cover_photo["path"],
        "filename": cover_photo["filename"],
        "fit": "fill",
    })

    # 2) Внутрішні сторінки
    remaining = [p for p in photos if p["filename"] != cover_photo["filename"]]

    page_num = 1
    img_num = 1

    # Простий greedy-алгоритм: до 3 фото на сторінку
    core = remaining[:-1] if len(remaining) > 1 else remaining
    for photo in core:
        placements.append({
            "label": f"PAGE_{page_num:02d}_IMG_{img_num:02d}",
            "photo": photo["path"],
            "filename": photo["filename"],
            "fit": "proportional",
        })

        img_num += 1
        if img_num > 3:
            img_num = 1
            page_num += 1

    # 3) Останнє фото — на задню обкладинку (якщо лишилось)
    if remaining:
        back_photo = remaining[-1]
        placements.append({
            "label": "BACK_IMAGE",
            "photo": back_photo["path"],
            "filename": back_photo["filename"],
            "fit": "fill",
        })

    # Розраховуємо реальну кількість сторінок
    actual_pages = calculate_pages_for_photos(len(photos), verbose)

    log(f"Generated {len(placements)} placements for {actual_pages} pages", verbose)
    return placements, actual_pages


# ==========================
# TEXT GENERATOR
# ==========================
def generate_texts(theme: str, client_name: str) -> dict:
    titles = {
        "lavstory": "Our Love Story",
        "for_her": "For Her",
        "adult18": "Private Collection",
        "custom": client_name or "Magazine",
    }

    subtitles = {
        "lavstory": "Best Moments",
        "for_her": "",
        "adult18": "",
        "custom": "",
    }

    return {
        "COVER_TITLE": titles.get(theme, client_name or "Magazine"),
        "COVER_SUB": subtitles.get(theme, ""),
        "CLIENT_NAME": client_name,
    }


def build_plan(job_id=None, job_path: Path | None = None, verbose=False) -> dict:
    """Будує compose_plan.json на основі meta/meta.json + фото"""

    # ===== Визначаємо папку job =====
    if job_path:
        job_dir = Path(job_path)
    else:
        job_dir = JOBS_DIR / job_id

    if not job_dir.exists():
        raise FileNotFoundError(f"Job not found: {job_dir}")

    # ===== Читаємо META (meta.json) =====
    meta_path = job_dir / "meta" / "meta.json"
    if not meta_path.exists():
        # fallback на стару назву job.json
        old_meta = job_dir / "meta" / "job.json"
        if old_meta.exists():
            meta_path = old_meta
        else:
            raise FileNotFoundError(f"meta.json not found: {meta_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        job_meta = json.load(f)

    theme = job_meta.get("theme") or job_meta.get("brief", {}).get("theme") or "custom"
    category = job_meta.get("category") or job_meta.get("brief", {}).get("category")
    pages = job_meta.get("pages") or job_meta.get("brief", {}).get("pages", 16)
    client_name = job_meta.get("client_name") or job_meta.get("brief", {}).get("client_name", "")

    log(f"Meta loaded: theme={theme}, category={category}, pages={pages}", verbose)

    # ===== Вибір шаблону =====
    template_path = get_template_path(theme, category, pages, verbose)
    if not template_path:
        raise FileNotFoundError(
            f"Template not found for theme={theme}, category={category}, pages={pages}"
        )

    # ===== Аналіз фото =====
    input_dir = job_dir / "input"
    photos = analyze_photos(input_dir, verbose)
    if not photos:
        raise ValueError("No photos found in input folder")

    placements, actual_pages = generate_placements(photos, pages, verbose)
    texts = generate_texts(theme, client_name)

    # Використовуємо реальну кількість сторінок на основі фото
    final_pages = actual_pages
    log(f"Final page count: {final_pages} (based on {len(photos)} photos)", verbose)

    # ===== Формуємо план =====
    plan = {
        "meta": {
            "job_id": job_id or job_dir.name,
            "generated_at": datetime.now().isoformat(),
            "theme": theme,
            "category": category,
            "pages": final_pages,
            "client_name": client_name,
            "template": str(template_path.absolute()),
            "output_dir": str((job_dir / "output").absolute()),
        },
        "placements": placements,
        "texts": texts,
    }

    out_path = job_dir / "meta" / "compose_plan.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print("Plan saved:", out_path)
    print("Template:", template_path.name)
    print("Photos:", len(photos))
    print("Placements:", len(placements))

    return plan


def main():
    parser = argparse.ArgumentParser(description="Build compose_plan.json from meta.json")
    parser.add_argument("-JobId", "--job-id")
    parser.add_argument("--job-path")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if not args.job_id and not args.job_path:
        parser.error("You must specify --job-id or --job-path")

    try:
        plan = build_plan(
            job_id=args.job_id,
            job_path=Path(args.job_path) if args.job_path else None,
            verbose=args.verbose,
        )

        if args.verbose:
            print(json.dumps(plan, ensure_ascii=False, indent=2))

        sys.exit(0)

    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
