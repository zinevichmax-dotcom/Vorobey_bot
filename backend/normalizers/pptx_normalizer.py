"""
Нормализатор PPTX: берёт существующий файл и выравнивает.
- Единые шрифты
- Единые размеры заголовков/тела
- Единая цветовая палитра
- Выравнивание позиций по сетке
- Единые отступы
"""

from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt


# === КОНФИГ СТИЛЯ ===
# Заказчик может потом заменить на свои корпоративные
STYLE: dict = {
    # Шрифты
    "font_title": "Calibri",
    "font_body": "Calibri",

    # Размеры (Pt)
    "size_title": Pt(28),
    "size_subtitle": Pt(18),
    "size_body": Pt(14),
    "size_caption": Pt(11),

    # Цвета
    "color_title": RGBColor(0x1A, 0x1A, 0x2E),  # тёмно-синий
    "color_body": RGBColor(0x33, 0x33, 0x33),  # тёмно-серый
    "color_accent": RGBColor(0x2E, 0x75, 0xB6),  # синий акцент

    # Отступы от краёв слайда (EMU)
    "margin_left": Inches(0.8),
    "margin_top_title": Inches(0.6),
    "margin_top_body": Inches(1.8),
    "content_width": Inches(8.4),  # для 10" слайда

    # Межстрочный интервал
    "line_spacing": Pt(20),
}


def normalize_pptx(input_path: str, output_path: str, style: dict | None = None) -> dict:
    """
    Нормализует презентацию.
    Возвращает отчёт: что изменено.
    """
    if style is None:
        style = STYLE

    prs = Presentation(input_path)
    report: dict = {"slides_processed": 0, "changes": []}

    for i, slide in enumerate(prs.slides):
        slide_changes: list[str] = []

        for shape in slide.shapes:
            # --- Нормализация текста ---
            if shape.has_text_frame:
                shape_type = _classify_shape(shape)

                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        slide_changes.extend(_normalize_run(run, shape_type, style))

                # Выравнивание позиции шейпа
                slide_changes.extend(_normalize_position(shape, shape_type, style))

            # --- Нормализация таблиц ---
            if shape.has_table:
                slide_changes.extend(_normalize_table(shape, style))

        if slide_changes:
            report["changes"].append({"slide": i + 1, "changes": slide_changes})
        report["slides_processed"] = i + 1

    prs.save(output_path)
    return report


def _classify_shape(shape) -> str:
    """Определяет роль текстового блока."""
    name = (shape.name or "").lower()
    if "title" in name:
        return "title"
    if "subtitle" in name:
        return "subtitle"

    # Эвристика: если текст крупный и короткий — заголовок
    if shape.has_text_frame:
        text = (shape.text_frame.text or "").strip()
        if len(text) < 80 and shape.top < Inches(2):
            return "title"

    return "body"


def _normalize_run(run, shape_type: str, style: dict) -> list[str]:
    """Нормализует один run текста. Возвращает список изменений."""
    changes: list[str] = []

    # Шрифт
    target_font = style["font_title"] if shape_type == "title" else style["font_body"]
    if run.font.name != target_font:
        old = run.font.name
        run.font.name = target_font
        changes.append(f"font: {old} → {target_font}")

    # Размер
    size_map = {
        "title": style["size_title"],
        "subtitle": style["size_subtitle"],
        "body": style["size_body"],
        "caption": style["size_caption"],
    }
    target_size = size_map.get(shape_type, style["size_body"])
    if run.font.size != target_size:
        old = run.font.size
        run.font.size = target_size
        changes.append(f"size: {old} → {target_size}")

    # Цвет
    target_color = style["color_title"] if shape_type == "title" else style["color_body"]
    try:
        current = run.font.color.rgb
        if current != target_color:
            run.font.color.rgb = target_color
            changes.append(f"color: {current} → {target_color}")
    except Exception:
        run.font.color.rgb = target_color
        changes.append(f"color: set → {target_color}")

    return changes


def _normalize_position(shape, shape_type: str, style: dict) -> list[str]:
    """Выравнивает позицию шейпа по сетке."""
    changes: list[str] = []

    if shape_type == "title":
        target_left = style["margin_left"]
        target_top = style["margin_top_title"]
        target_width = style["content_width"]

        if abs(shape.left - target_left) > Inches(0.2):
            shape.left = target_left
            changes.append("title: aligned left")
        if abs(shape.top - target_top) > Inches(0.3):
            shape.top = target_top
            changes.append("title: aligned top")
        if abs(shape.width - target_width) > Inches(0.5):
            shape.width = target_width
            changes.append("title: width normalized")

    elif shape_type == "body":
        target_left = style["margin_left"]
        target_width = style["content_width"]

        if abs(shape.left - target_left) > Inches(0.3):
            shape.left = target_left
            changes.append("body: aligned left")
        if abs(shape.width - target_width) > Inches(0.5):
            shape.width = target_width
            changes.append("body: width normalized")

    return changes


def _normalize_table(shape, style: dict) -> list[str]:
    """Нормализует таблицу: шрифты, размеры."""
    table = shape.table

    for row in table.rows:
        for cell in row.cells:
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    if run.font.name != style["font_body"]:
                        run.font.name = style["font_body"]
                    if run.font.size != style["size_body"]:
                        run.font.size = style["size_body"]
                    run.font.color.rgb = style["color_body"]

    return ["table: fonts and colors normalized"]


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[1].replace(".pptx", "_normalized.pptx")
        report = normalize_pptx(input_file, output_file)
        print(json.dumps(report, indent=2, default=str, ensure_ascii=False))
        print(f"\nСохранено: {output_file}")
    else:
        print("Использование: python pptx_normalizer.py файл.pptx")
