# 🗺️ Frame Mapping — Як план маппиться на InDesign фрейми

## Концепція

Кожен фрейм в InDesign шаблоні має **Script Label** — унікальний ідентифікатор.
`compose_plan.json` містить список `placements`, де кожен елемент вказує:
- `label` — Script Label фрейму
- `photo` — шлях до фото
- `fit` — тип заповнення (fill, proportional, fit)

## Структура compose_plan.json

```json
{
  "meta": {
    "job_id": "20250130_143052_abc123",
    "template": "C:/Templates/love_story_16.idml",
    "output_dir": "C:/Jobs/abc123/output"
  },
  
  "placements": [
    {
      "label": "COVER_IMAGE",
      "photo": "C:/Jobs/abc123/input/photo_001.jpg",
      "fit": "fill"
    },
    {
      "label": "PAGE_01_IMG_01",
      "photo": "C:/Jobs/abc123/input/photo_002.jpg",
      "fit": "proportional"
    }
  ],
  
  "texts": {
    "COVER_TITLE": "Our Love Story",
    "COVER_SUB": "Найкращі моменти разом"
  }
}
```

## Конвенція назв Script Labels

### Image Frames

| Label Pattern | Опис | Приклад |
|---------------|------|---------|
| `COVER_IMAGE` | Головне фото обкладинки | Одне на журнал |
| `COVER_IMAGE_BG` | Фонове фото обкладинки | Опціонально |
| `PAGE_XX_IMG_YY` | Фото на сторінці XX, позиція YY | `PAGE_01_IMG_01` |
| `SPREAD_XX_IMG_YY` | Фото на розвороті XX | `SPREAD_02_IMG_01` |
| `BACK_IMAGE` | Фото задньої сторінки | Одне на журнал |

### Text Frames

| Label Pattern | Опис | Приклад |
|---------------|------|---------|
| `COVER_TITLE` | Заголовок обкладинки | "Our Love Story" |
| `COVER_SUB` | Підзаголовок | "Найкращі моменти" |
| `CLIENT_NAME` | Ім'я клієнта | "Анна і Максим" |
| `PAGE_XX_TXT_YY` | Текст на сторінці | Підписи до фото |
| `LETTER_TEXT` | Текст листа | Опціонально |
| `DATE_TEXT` | Дата | Автозаповнення |

## Типи заповнення (fit)

| Тип | InDesign аналог | Опис |
|-----|-----------------|------|
| `fill` | Fill Proportionally | Заповнює фрейм, може обрізати |
| `proportional` | Fit Content Proportionally | Вписує без обрізки |
| `fit` | Fit Content to Frame | Розтягує (може деформувати) |
| `center` | Center Content | Центрує без масштабування |

## Як працює JSX скрипт

```javascript
// Псевдокод compose.jsx

// 1. Читаємо план
var plan = readJSON("compose_plan.json");

// 2. Відкриваємо шаблон
var doc = app.open(plan.meta.template);

// 3. Для кожного placement
for each (var p in plan.placements) {
    // Шукаємо фрейм по label
    var frame = findFrameByLabel(doc, p.label);
    
    if (frame && p.photo) {
        // Вставляємо фото
        frame.place(File(p.photo));
        
        // Застосовуємо fit
        if (p.fit === "fill") {
            frame.fit(FitOptions.FILL_PROPORTIONALLY);
        } else {
            frame.fit(FitOptions.PROPORTIONALLY);
        }
        
        frame.fit(FitOptions.CENTER_CONTENT);
    }
}

// 4. Оновлюємо тексти
for (var label in plan.texts) {
    var textFrame = findFrameByLabel(doc, label);
    if (textFrame) {
        textFrame.contents = plan.texts[label];
    }
}

// 5. Експортуємо PDF
doc.exportFile(ExportFormat.PDF_TYPE, outputPath);
```

## Приклад шаблону для 16 сторінок

```
Сторінка 1 (обкладинка):
  - COVER_IMAGE (повний розмір)
  - COVER_TITLE (текст)
  - COVER_SUB (текст)

Сторінки 2-3 (розворот 1):
  - PAGE_01_IMG_01 (лівий)
  - PAGE_01_IMG_02 (правий)

Сторінки 4-5 (розворот 2):
  - SPREAD_02_IMG_01 (на весь розворот)

Сторінки 6-7 (розворот 3):
  - PAGE_03_IMG_01
  - PAGE_03_IMG_02
  - PAGE_03_IMG_03

... і так далі ...

Сторінка 16 (задня):
  - BACK_IMAGE
  - CLIENT_NAME (опціонально)
```

## Як додати Script Label в InDesign

1. Відкрий шаблон в InDesign
2. Виділи фрейм (image або text)
3. **Window → Utilities → Script Label**
4. Введи назву (напр. `COVER_IMAGE`)
5. Enter
6. Збережи документ

### Порада
Для перевірки labels можна використати скрипт:

```javascript
// list_labels.jsx
var doc = app.activeDocument;
var items = doc.allPageItems;

for (var i = 0; i < items.length; i++) {
    if (items[i].label !== "") {
        $.writeln(items[i].label + " → " + items[i].constructor.name);
    }
}
```

## Troubleshooting

### Фото не вставляється
- Перевір, що label існує в шаблоні
- Перевір, що шлях до фото абсолютний
- Перевір права доступу до файлу

### Текст не оновлюється
- Переконайся, що фрейм — TextFrame, а не графічний
- Перевір label (регістр важливий!)

### PDF не експортується
- Перевір, що output_dir існує
- Перевір PDF Export Preset

