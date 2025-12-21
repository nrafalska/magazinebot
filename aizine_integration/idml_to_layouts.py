# -*- coding: utf-8 -*-
"""
IDML → JSON layouts extractor
--------------------------------
Витягає структуру сторінок із IDML:
- фото-фрейми (Rectangles із Graphic)
- текстові фрейми (TextFrames)
- позиції, розміри, labels
- сторінки (Page)
- spreads (Spread)

Запуск:
    python -m aizine_integration.idml_to_layouts --all
або
    python -m aizine_integration.idml_to_layouts --idml path.idml --template lavstory/vesilnyi
"""

import zipfile
import json
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def parse_bounds(bounds):
    """GeometricBounds: top left bottom right"""
    try:
        t, l, b, r = [float(x) for x in bounds.split()]
        return {
            "top": t,
            "left": l,
            "bottom": b,
            "right": r,
            "width": r - l,
            "height": b - t
        }
    except:
        return None


def extract_idml(idml_path: Path, template_key: str, out_json: Path):
    pages_data = []

    with zipfile.ZipFile(idml_path, 'r') as z:
        for name in z.namelist():
            if "Spreads/Spread" in name and name.endswith(".xml"):
                xml_bytes = z.read(name)
                root = ET.fromstring(xml_bytes)

                spread_id = Path(name).stem

                # Збираємо елементи сторінок
                for page in root.findall(".//Page"):
                    page_id = page.attrib.get("Self")
                    page_bounds = parse_bounds(page.attrib.get("GeometricBounds", ""))

                    photos = []
                    texts = []

                    # Фото-фрейми
                    for rect in page.findall(".//Rectangle"):
                        gb = rect.attrib.get("GeometricBounds")
                        if not gb:
                            continue
                        bounds = parse_bounds(gb)

                        # Перевіряємо чи в середині є <Image> або <Graphic>
                        graphic = rect.find(".//Image")
                        if graphic is None:
                            graphic = rect.find(".//Graphic")

                        if graphic is not None:
                            label = rect.attrib.get("XMLContent") or \
                                    (rect.find(".//Properties") is not None and rect.find(".//Properties").find("Label"))
                            photos.append({
                                "bounds": bounds,
                                "label": label if isinstance(label, str) else None
                            })

                    # Текстові фрейми
                    for tf in page.findall(".//TextFrame"):
                        gb = tf.attrib.get("GeometricBounds")
                        if not gb:
                            continue
                        bounds = parse_bounds(gb)

                        label = tf.attrib.get("XMLContent") or None
                        texts.append({
                            "bounds": bounds,
                            "label": label
                        })

                    pages_data.append({
                        "page_id": page_id,
                        "spread": spread_id,
                        "bounds": page_bounds,
                        "photo_slots": photos,
                        "text_slots": texts
                    })

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({
        "template": template_key,
        "pages": pages_data
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[OK] Saved: {out_json}")


def extract_all():
    base = Path("data/templates")
    idml_files = list(base.rglob("*.idml"))

    print(f"Знайдено IDML файлів: {len(idml_files)}")

    for fp in idml_files:
        # обрізаємо шлях: templates\<theme>\<category>\*.idml
        rel = fp.relative_to(base)
        theme = rel.parts[0]
        category = rel.parts[1]

        template_key = f"{theme}/{category}"

        out_file = Path("data/layouts") / f"{theme}_{category}.json"

        extract_idml(fp, template_key, out_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--idml")
    parser.add_argument("--template")
    parser.add_argument("--out")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.all:
        extract_all()
    else:
        if not args.idml or not args.template:
            print("Використання:\n"
                  "python -m aizine_integration.idml_to_layouts --idml path.idml --template lavstory/vesilnyi")
            exit(1)

        out = Path(args.out) if args.out else Path("layout.json")
        extract_idml(Path(args.idml), args.template, out)
