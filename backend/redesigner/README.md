# Redesigner — модуль редизайна PPTX

Превращает «некрасивую» PPTX в одну из 3 профессиональных стилей.

## Структура

```
redesigner/
├── __init__.py           # публичный API: from redesigner import redesign
├── orchestrator.py       # главная функция redesign()
├── pptx_parser.py        # извлечение контента из входной PPTX
├── slide_classifier.py   # Claude решает какой layout + разбивка
├── slide_builder.py      # копирует layout из master + подставляет текст
├── layout_catalog.py     # 11 лейаутов × лимиты символов
├── test_builder.py       # unit-тест сборщика (без API)
├── masters/
│   ├── master_style_1_formal.pptx
│   ├── master_style_2_corporate.pptx
│   └── master_style_3_bold.pptx
└── README.md
```

## Установка

1. Распаковать в `backend/redesigner/` твоего репо.
2. Установить зависимости (должны быть уже в `backend/requirements.txt`):
   ```
   python-pptx
   anthropic
   lxml
   ```
3. Убедиться что `masters/` внутри `redesigner/` (или переопределить через env `REDESIGNER_MASTERS_DIR`).

## Использование из Python

```python
from redesigner import redesign

result = redesign(
    input_pptx_path="/path/to/input.pptx",
    style="formal",            # "formal" | "corporate" | "bold"
    output_pptx_path="/path/to/output.pptx",
    # anthropic_api_key=None,  # возьмёт из env ANTHROPIC_API_KEY
)

if result["success"]:
    print(f"Готово! {result['input_slides']} → {result['output_slides']} слайдов")
    print(f"Распределение: {result['layout_distribution']}")
    if result["warnings"]:
        print(f"Предупреждения: {result['warnings']}")
else:
    print(f"Ошибка: {result['error']}")
```

## Интеграция в FastAPI

В `backend/main.py`:

```python
from fastapi import UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import os, tempfile

from redesigner import redesign


@app.post("/redesign/pptx")
async def redesign_pptx(
    file: UploadFile = File(...),
    style: str = Form(...),
):
    if style not in ("formal", "corporate", "bold"):
        raise HTTPException(400, "Invalid style")
    
    if not file.filename.lower().endswith(".pptx"):
        raise HTTPException(400, "Only .pptx files supported")
    
    tmpdir = tempfile.mkdtemp(prefix="redesign_")
    input_path = os.path.join(tmpdir, file.filename)
    with open(input_path, "wb") as f:
        f.write(await file.read())
    
    output_path = os.path.join(tmpdir, f"redesigned_{style}.pptx")
    
    result = redesign(input_path, style, output_path)
    
    if not result.get("success"):
        raise HTTPException(500, result.get("error", "Unknown error"))
    
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"redesigned_{style}_{file.filename}",
    )


@app.get("/redesign/styles")
async def get_styles():
    """Список стилей для UI."""
    return {
        "styles": [
            {
                "id": "formal",
                "name": "Формальный",
                "description": "Классика. Для судов, меморандумов.",
                "colors": ["#253278", "#F8EFE5"],
                "font": "Inter",
            },
            {
                "id": "corporate",
                "name": "Корпоративный",
                "description": "Чистый с градиентами. Для клиентов.",
                "colors": ["#24629A", "#E8A46B"],
                "font": "Lato + Source Serif",
            },
            {
                "id": "bold",
                "name": "Современный",
                "description": "Тёмный контраст. Для питчей.",
                "colors": ["#000000", "#2D8FCF"],
                "font": "Kollektif",
            },
        ]
    }
```

## Как работает pipeline

```
input.pptx
    ↓
[1] pptx_parser.py
    - Извлекает текст из каждого слайда
    - Сохраняет картинки в temp-dir как отдельные файлы
    - Детектит таблицы, графики, SmartArt
    ↓
[2] slide_classifier.py (Claude Sonnet 4)
    - Для каждого слайда решает какой layout_kind подходит
    - Распределяет текст автора ДОСЛОВНО по плейсхолдерам
    - Если не влезает — разбивает 1 слайд автора → N слайдов output
    ↓
[2.5] orchestrator: sanity-check
    - image_text/image_full без картинки → даунгрейд на text_heavy
    ↓
[3] slide_builder.py
    - Открывает master.pptx выбранного стиля
    - Для каждого слайда из spec'а копирует соотв. layout из master
    - Подставляет плейсхолдеры {HEADING} → реальный текст
    - Чистые плейсхолдеры удаляет
    - Заменяет картинку-placeholder на реальную
    ↓
output.pptx
```

## Поведение со сложным контентом

| Содержимое слайда автора | Что делаем |
|---|---|
| Текст + заголовок | Классифицируем (title/section/bullets/text_heavy/...) |
| Буллеты 3-5 штук | layout `bullets` |
| Буллеты > 5 штук | Разбиваем на несколько слайдов `bullets` |
| Большая таблица | layout `table` (сжато до 4×4) или копируем как есть |
| Изображение + текст | layout `image_text` |
| Только изображение | layout `image_full` |
| Диаграмма (chart) | Слайд сохраняется как есть (`_original`), без редизайна |
| SmartArt | Копируется как есть |
| Видео/аудио | Копируется как есть |

## Ограничения

- Анимации и переходы не сохраняются (это и не нужно — редизайн=статика)
- Точное воспроизведение кастомных графиков в новом стиле не делаем
- Текст ДОСЛОВНО сохраняется — если автор пишет на иврите, редизайн на иврите

## Время и цена

- Парсинг: < 1 сек
- Claude classify: 2-3 сек/слайд (Sonnet 4)
- Сборка: < 1 сек
- **Итого для 10 слайдов: ~30 сек, ~$0.12**

## Тестирование

Unit-тест сборщика (не требует API):
```bash
cd redesigner
REDESIGNER_MASTERS_DIR=./masters python3 test_builder.py
```

Должно вывести:
```
Results: 33 passed, 0 failed
Partial bullets: PASS
Multi-slide: PASS
```

## Известные ограничения версии

1. Shadow background на overlay-image может слегка отличаться между LibreOffice и PowerPoint
2. Шрифт Kollektif (Стиль 3) не установлен по умолчанию — PowerPoint подставит дефолтный. На сервере рекомендуется поставить шрифт или перейти на похожий bold-gothic
3. Первый запуск на реальной презе заказчика может показать кейсы которые надо довести — промпт классификатора живой
