"""
Claude-классификатор: для каждого слайда автора решает
- какой layout_kind (title/section/bullets/...) подходит
- влезает ли текст целиком
- если нет — как разбить на N слайдов
- распределяет текст по плейсхолдерам
"""
import json
import os
from anthropic import Anthropic

try:
    from .layout_catalog import LAYOUT_KINDS, LAYOUT_LIMITS, fits_in_layout
except ImportError:
    from layout_catalog import LAYOUT_KINDS, LAYOUT_LIMITS, fits_in_layout


def build_layout_description() -> str:
    """Собрать промпт-описание всех лейаутов для Claude."""
    lines = ["Доступные лейауты (выбирай один из них):\n"]
    
    descriptions = {
        "title": "ОБЛОЖКА презентации. Большой заголовок + подзаголовок. Используй ТОЛЬКО для первого слайда.",
        "section": "РАЗДЕЛИТЕЛЬ секции. Короткий заголовок раздела + краткое описание. Используй когда слайд — заголовок большой темы.",
        "text_heavy": "Плотный ТЕКСТ: заголовок + абзац/абзацы. Используй когда на слайде много связного текста.",
        "bullets": "БУЛЛЕТЫ: заголовок + до 5 пронумерованных пунктов. Каждый пункт: короткий заголовок + описание.",
        "two_columns": "ДВЕ КОЛОНКИ: сравнение, параллельные темы. Используй для 'до/после', 'план/факт', 'A/B'.",
        "stats": "СТАТИСТИКА: до 4 крупных чисел с подписями. Используй для слайдов с KPI/метриками.",
        "quote": "ЦИТАТА + автор. Короткая яркая фраза.",
        "table": "ТАБЛИЦА 4×4: шапка + до 4 строк данных. Используй когда контент — табличный.",
        "closing": "ФИНАЛ: 'Спасибо' + контакты. Используй ТОЛЬКО для последнего слайда.",
        "image_text": "КАРТИНКА + ТЕКСТ (рядом). Используй когда на слайде есть изображение и текст.",
        "image_full": "FULL-BLEED изображение на весь слайд с overlay-текстом. Используй для пафосных слайдов-перебивок с картинкой.",
    }
    
    for kind in LAYOUT_KINDS:
        limits = LAYOUT_LIMITS[kind]
        fields = ", ".join(f"{k}(≤{v['max']}симв)" if v['max'] > 0 else k 
                          for k, v in limits.items() if v.get('max', 1) != 0 or k == "IMAGE")
        desc = descriptions.get(kind, "")
        lines.append(f"\n**{kind}** — {desc}")
        lines.append(f"Плейсхолдеры: {fields}")
    
    return "\n".join(lines)


CLASSIFIER_SYSTEM_PROMPT = """Ты — helper для редизайна презентаций. Тебе дают контент слайда из оригинальной презентации. Твоя задача — решить какой лейаут из каталога подходит, и распределить текст автора по плейсхолдерам этого лейаута.

КРИТИЧЕСКИ ВАЖНО:
1. Текст автора НЕЛЬЗЯ сокращать, переписывать, перефразировать. Только копировать ДОСЛОВНО.
2. Если текст не влезает в один слайд (превышает лимиты символов) — разбей на несколько слайдов ТОГО ЖЕ layout_kind, распределив контент по порядку.
3. Не переводи текст на другой язык.
4. Если автор оригинала пишет буллетами/списком — сохрани их как буллеты.
5. Порядок информации не меняется.

ПРАВИЛА ЗАПОЛНЕНИЯ:
- Для bullets layout: ВСЕГДА заполняй BULLET_N_NUM = "01", "02", "03", "04", "05" (ровно двузначные).
- Для неиспользуемых слотов (например только 3 буллета из 5) — не передавай лишние ключи, тогда они не покажутся.
- Для stats — STAT_N_VALUE короткое число/метрика (42%, 1.2B, ₽2.4М), STAT_N_LABEL — расшифровка.
- Для stats — заголовки категорий STAT_N_CATEGORY ЗАГЛАВНЫМИ.
- DECK_LABEL и YEAR — общие колонтитулы, бери из контекста если есть (название презентации, год).

СПЕЦИАЛЬНЫЕ СЛАЙДЫ:
- Если это ПЕРВЫЙ слайд презентации — используй layout "title" (обложка).
- Если это ПОСЛЕДНИЙ слайд — используй "closing" (спасибо/контакты).
- Если на слайде ЕСТЬ таблица (в ввода tables > 0) — используй layout "table", перенеси данные в R1_C1...R4_C4.
- Если на слайде ЕСТЬ картинка — используй либо "image_text" (картинка + рядом текст), либо "image_full" (картинка фоном), в зависимости от того сколько текста.

Отвечай строго в JSON формате:
```json
{
  "slides": [
    {
      "layout_kind": "bullets",
      "content": {
        "HEADING": "Финансовые показатели",
        "BULLET_1_NUM": "01",
        "BULLET_1_TITLE": "Рост выручки",
        "BULLET_1_TEXT": "+18%",
        "BULLET_2_NUM": "02",
        "BULLET_2_TITLE": "...",
        "BULLET_2_TEXT": "..."
      },
      "image_index": null
    }
  ],
  "reasoning": "Кратко почему такой layout и разбивка"
}
```

Поле `image_index` — если в layout нужна картинка, укажи индекс из списка доступных изображений (0-based). Иначе null.

Поле `slides` — массив. Обычно 1 слайд. Может быть 2-3 если контент не влезал в один."""


def classify_slide(slide_info: dict, anthropic_client: Anthropic,
                   is_first: bool = False, is_last: bool = False,
                   total_slides: int = 1,
                   model: str = "claude-sonnet-4-20250514") -> dict:
    """
    Классифицировать один слайд: какой layout, как распределить текст.
    Возвращает {"slides": [...], "reasoning": str}
    """
    # Собрать user-prompt
    position_hint = ""
    if is_first:
        position_hint = " (ЭТО ПЕРВЫЙ СЛАЙД — используй layout 'title')"
    elif is_last:
        position_hint = " (ЭТО ПОСЛЕДНИЙ СЛАЙД — используй layout 'closing')"
    
    lines = [
        f"Слайд #{slide_info['index'] + 1} из {total_slides}{position_hint}.",
        "",
        f"Заголовок-кандидат: {slide_info['title_candidate']!r}",
        "",
        "Текстовые блоки (в порядке появления на слайде):",
    ]
    for i, block in enumerate(slide_info['text_blocks']):
        lines.append(f"  [{i}] {block[:500]}{'...' if len(block) > 500 else ''}")
    
    lines.append("")
    lines.append(f"Кол-во картинок на слайде: {len(slide_info['images'])}")
    lines.append(f"Кол-во таблиц: {len(slide_info['tables'])}")
    lines.append(f"Наличие графика: {slide_info['has_chart']}")
    lines.append(f"Всего символов: {slide_info['total_chars']}")
    
    if slide_info['tables']:
        lines.append("\nТаблицы:")
        for t_idx, table in enumerate(slide_info['tables']):
            lines.append(f"  Таблица {t_idx}: {table['rows']}×{table['cols']}")
            for row in table['data'][:5]:
                lines.append(f"    {row}")
    
    lines.append("")
    lines.append("=" * 40)
    lines.append(build_layout_description())
    lines.append("")
    lines.append("Выбери лейаут(ы) и распредели текст. Отвечай JSON.")
    
    user_prompt = "\n".join(lines)
    
    response = anthropic_client.messages.create(
        model=model,
        max_tokens=4000,
        system=CLASSIFIER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    # Извлечь JSON из ответа
    response_text = response.content[0].text
    # Поиск JSON в ответе (Claude иногда оборачивает в ```json...```)
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
    else:
        json_str = response_text.strip()
    
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as e:
        return {
            "slides": [],
            "reasoning": f"PARSE_ERROR: {str(e)}",
            "raw": response_text[:500],
        }
    
    # Валидация — подставляем пути к изображениям
    for s in result.get("slides", []):
        if s.get("image_index") is not None:
            idx = s["image_index"]
            if idx < len(slide_info.get("images", [])):
                s["content"]["_image_path"] = slide_info["images"][idx]["path"]
    
    return result


def classify_presentation(parsed_data: dict, anthropic_client: Anthropic) -> list[dict]:
    """
    Классифицировать всю презентацию. Возвращает плоский список слайдов для сборки:
    [{"layout_kind": ..., "content": {...}}, ...]
    """
    output_slides = []
    classifications = []
    
    for slide_info in parsed_data["slides"]:
        # Пометить первый слайд как title, последний как closing по умолчанию (Claude может поменять)
        is_first = slide_info["index"] == 0
        is_last = slide_info["index"] == parsed_data["total_slides"] - 1
        
        # Специальные случаи — слайды с chart/SmartArt/media оставляем "как есть"
        if slide_info.get("has_chart") or slide_info.get("has_media"):
            output_slides.append({
                "layout_kind": "_original",  # специальный маркер
                "content": {},
                "source_slide_idx": slide_info["index"],
                "reason": "chart/media — preserved",
            })
            continue
        
        cls = classify_slide(
            slide_info,
            anthropic_client,
            is_first=is_first,
            is_last=is_last,
            total_slides=parsed_data["total_slides"],
        )
        classifications.append(cls)
        
        for s in cls.get("slides", []):
            output_slides.append(s)
    
    return output_slides, classifications
