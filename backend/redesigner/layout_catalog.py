"""
Каталог лейаутов: описывает какие плейсхолдеры есть в каждом лейауте каждого стиля,
лимиты по тексту, индекс слайда в master'е.

Формат: STYLE -> LAYOUT_KIND -> {
  "slide_idx": int,  # индекс слайда в master.pptx (0-based)
  "placeholders": {
    "NAME": {
      "max_chars": int,     # максимум символов для хорошего вида
      "required": bool,     # обязательное поле
      "description": str,   # что это
    }
  }
}
"""

STYLES = ["formal", "corporate", "bold"]

LAYOUT_KINDS = [
    "title",        # 0 - обложка
    "section",      # 1 - разделитель секций
    "text_heavy",   # 2 - плотный текст
    "bullets",      # 3 - 5 пунктов
    "two_columns",  # 4 - две колонки
    "stats",        # 5 - 4 числа
    "quote",        # 6 - цитата
    "table",        # 7 - таблица 4×4
    "closing",      # 8 - финал
    "image_text",   # 9 - картинка + текст
    "image_full",   # 10 - full-bleed картинка
]

# Лимиты по символам — проверено на превью
# Базовые, одинаковые для всех 3 стилей (кроме специфики)
LAYOUT_LIMITS = {
    "title": {
        "SUPER_LABEL": {"max": 60, "required": False, "desc": "Малый лейбл над/под заголовком"},
        "TITLE": {"max": 30, "required": True, "desc": "Главный заголовок"},
        "TITLE_ACCENT": {"max": 30, "required": False, "desc": "Акцентная часть (только formal)"},
        "SUBTITLE": {"max": 120, "required": False, "desc": "Подзаголовок"},
        "DECK_LABEL": {"max": 30, "required": False, "desc": "Колонтитул-лейбл"},
        "DECK_SUBTITLE": {"max": 30, "required": False, "desc": "Центр-колонтитул"},
        "YEAR": {"max": 10, "required": False, "desc": "Год/дата"},
    },
    "section": {
        "SECTION_NUM": {"max": 5, "required": False, "desc": "01, 02..."},
        "SECTION_TITLE": {"max": 40, "required": True, "desc": "Название раздела"},
        "SECTION_DESCRIPTION": {"max": 300, "required": False, "desc": "Описание (corporate)"},
        "SECTION_LABEL": {"max": 30, "required": False, "desc": "Kicker над описанием (например 'О РАЗДЕЛЕ')"},
        "DECK_LABEL": {"max": 30, "required": False, "desc": ""},
        "YEAR": {"max": 10, "required": False, "desc": ""},
    },
    "text_heavy": {
        "HEADING": {"max": 60, "required": True, "desc": "Заголовок"},
        "LEAD": {"max": 150, "required": False, "desc": "Подзаголовок-лид"},
        "BODY_TEXT": {"max": 1400, "required": True, "desc": "Основной текст"},
        "DECK_LABEL": {"max": 30, "required": False, "desc": ""},
        "YEAR": {"max": 10, "required": False, "desc": ""},
    },
    "bullets": {
        "HEADING": {"max": 60, "required": True, "desc": "Заголовок"},
        "BULLET_1_NUM": {"max": 5, "required": False, "desc": "Номер пункта 1 (01, 02...)"},
        "BULLET_1_TITLE": {"max": 40, "required": True, "desc": "Заголовок пункта 1"},
        "BULLET_1_TEXT": {"max": 120, "required": False, "desc": "Описание пункта 1"},
        "BULLET_2_NUM": {"max": 5, "required": False, "desc": ""},
        "BULLET_2_TITLE": {"max": 40, "required": False, "desc": ""},
        "BULLET_2_TEXT": {"max": 120, "required": False, "desc": ""},
        "BULLET_3_NUM": {"max": 5, "required": False, "desc": ""},
        "BULLET_3_TITLE": {"max": 40, "required": False, "desc": ""},
        "BULLET_3_TEXT": {"max": 120, "required": False, "desc": ""},
        "BULLET_4_NUM": {"max": 5, "required": False, "desc": ""},
        "BULLET_4_TITLE": {"max": 40, "required": False, "desc": ""},
        "BULLET_4_TEXT": {"max": 120, "required": False, "desc": ""},
        "BULLET_5_NUM": {"max": 5, "required": False, "desc": ""},
        "BULLET_5_TITLE": {"max": 40, "required": False, "desc": ""},
        "BULLET_5_TEXT": {"max": 120, "required": False, "desc": ""},
        "DECK_LABEL": {"max": 30, "required": False, "desc": ""},
        "YEAR": {"max": 10, "required": False, "desc": ""},
    },
    "two_columns": {
        "HEADING": {"max": 60, "required": True, "desc": "Заголовок"},
        "LEFT_LABEL": {"max": 30, "required": False, "desc": "Kicker левой колонки (например 'ДО')"},
        "LEFT_TITLE": {"max": 40, "required": True, "desc": "Левая колонка — заголовок"},
        "LEFT_SUB": {"max": 50, "required": False, "desc": "Левая — подзаголовок"},
        "LEFT_TEXT": {"max": 700, "required": True, "desc": "Левая — текст"},
        "RIGHT_LABEL": {"max": 30, "required": False, "desc": "Kicker правой колонки (например 'ПОСЛЕ')"},
        "RIGHT_TITLE": {"max": 40, "required": True, "desc": "Правая — заголовок"},
        "RIGHT_SUB": {"max": 50, "required": False, "desc": "Правая — подзаголовок"},
        "RIGHT_TEXT": {"max": 700, "required": True, "desc": "Правая — текст"},
        "DECK_LABEL": {"max": 30, "required": False, "desc": ""},
        "YEAR": {"max": 10, "required": False, "desc": ""},
    },
    "stats": {
        "HEADING": {"max": 60, "required": True, "desc": "Заголовок"},
        "SUBTITLE": {"max": 120, "required": False, "desc": "Подзаголовок"},
        "STAT_1_CATEGORY": {"max": 20, "required": False, "desc": "Категория 1"},
        "STAT_1_VALUE": {"max": 10, "required": True, "desc": "Число/значение 1"},
        "STAT_1_LABEL": {"max": 50, "required": False, "desc": "Подпись 1"},
        "STAT_2_CATEGORY": {"max": 20, "required": False, "desc": ""},
        "STAT_2_VALUE": {"max": 10, "required": False, "desc": ""},
        "STAT_2_LABEL": {"max": 50, "required": False, "desc": ""},
        "STAT_3_CATEGORY": {"max": 20, "required": False, "desc": ""},
        "STAT_3_VALUE": {"max": 10, "required": False, "desc": ""},
        "STAT_3_LABEL": {"max": 50, "required": False, "desc": ""},
        "STAT_4_CATEGORY": {"max": 20, "required": False, "desc": ""},
        "STAT_4_VALUE": {"max": 10, "required": False, "desc": ""},
        "STAT_4_LABEL": {"max": 50, "required": False, "desc": ""},
        "DECK_LABEL": {"max": 30, "required": False, "desc": ""},
        "YEAR": {"max": 10, "required": False, "desc": ""},
    },
    "quote": {
        "QUOTE_TEXT": {"max": 250, "required": True, "desc": "Текст цитаты"},
        "QUOTE_AUTHOR": {"max": 40, "required": False, "desc": "Автор"},
        "QUOTE_ROLE": {"max": 50, "required": False, "desc": "Должность/роль"},
        "DECK_LABEL": {"max": 30, "required": False, "desc": ""},
        "YEAR": {"max": 10, "required": False, "desc": ""},
    },
    "table": {
        "HEADING": {"max": 60, "required": True, "desc": "Заголовок"},
        "COL_1_HEADER": {"max": 25, "required": True, "desc": "Колонка 1 - заголовок"},
        "COL_2_HEADER": {"max": 25, "required": True, "desc": ""},
        "COL_3_HEADER": {"max": 25, "required": True, "desc": ""},
        "COL_4_HEADER": {"max": 25, "required": True, "desc": ""},
        "R1_C1": {"max": 40, "required": False, "desc": ""}, "R1_C2": {"max": 40, "required": False, "desc": ""},
        "R1_C3": {"max": 40, "required": False, "desc": ""}, "R1_C4": {"max": 40, "required": False, "desc": ""},
        "R2_C1": {"max": 40, "required": False, "desc": ""}, "R2_C2": {"max": 40, "required": False, "desc": ""},
        "R2_C3": {"max": 40, "required": False, "desc": ""}, "R2_C4": {"max": 40, "required": False, "desc": ""},
        "R3_C1": {"max": 40, "required": False, "desc": ""}, "R3_C2": {"max": 40, "required": False, "desc": ""},
        "R3_C3": {"max": 40, "required": False, "desc": ""}, "R3_C4": {"max": 40, "required": False, "desc": ""},
        "R4_C1": {"max": 40, "required": False, "desc": ""}, "R4_C2": {"max": 40, "required": False, "desc": ""},
        "R4_C3": {"max": 40, "required": False, "desc": ""}, "R4_C4": {"max": 40, "required": False, "desc": ""},
        "DECK_LABEL": {"max": 30, "required": False, "desc": ""},
        "YEAR": {"max": 10, "required": False, "desc": ""},
    },
    "closing": {
        "CLOSING_HEADLINE": {"max": 30, "required": True, "desc": "Финальный заголовок (Спасибо)"},
        "CLOSING_SUBTITLE": {"max": 80, "required": False, "desc": "Подзаголовок"},
        "CONTACTS": {"max": 150, "required": False, "desc": "Контакты"},
    },
    "image_text": {
        "KICKER": {"max": 30, "required": False, "desc": "Маленький лейбл над заголовком"},
        "HEADING": {"max": 60, "required": True, "desc": "Заголовок"},
        "BODY_TEXT": {"max": 600, "required": False, "desc": "Текст под заголовком"},
        "IMAGE": {"max": 0, "required": True, "desc": "Путь к файлу изображения"},
        "DECK_LABEL": {"max": 30, "required": False, "desc": ""},
    },
    "image_full": {
        "KICKER": {"max": 30, "required": False, "desc": "Лейбл над заголовком"},
        "HEADING": {"max": 60, "required": True, "desc": "Главный заголовок"},
        "BODY_TEXT": {"max": 300, "required": False, "desc": "Текст под заголовком"},
        "IMAGE": {"max": 0, "required": True, "desc": "Путь к фоновому изображению"},
        "DECK_LABEL": {"max": 30, "required": False, "desc": ""},
    },
}


def get_layout_info(kind: str) -> dict:
    """Получить описание лейаута."""
    if kind not in LAYOUT_LIMITS:
        raise ValueError(f"Unknown layout kind: {kind}. Available: {list(LAYOUT_LIMITS.keys())}")
    return {
        "slide_idx": LAYOUT_KINDS.index(kind),
        "placeholders": LAYOUT_LIMITS[kind],
    }


def fits_in_layout(content: dict, kind: str) -> tuple[bool, list[str]]:
    """
    Проверяет, влезает ли контент в лейаут.
    Возвращает (влезает?, список проблем).
    """
    info = get_layout_info(kind)
    problems = []
    
    for ph_name, ph_info in info["placeholders"].items():
        if ph_info["required"] and ph_name not in content:
            problems.append(f"Missing required: {ph_name}")
            continue
        if ph_name in content:
            value = str(content[ph_name])
            if ph_info["max"] > 0 and len(value) > ph_info["max"]:
                problems.append(
                    f"{ph_name}: {len(value)} chars > limit {ph_info['max']}"
                )
    
    return len(problems) == 0, problems


def get_style_master_path(style: str) -> str:
    """Путь к master.pptx для стиля."""
    mapping = {
        "formal": "master_style_1_formal.pptx",
        "corporate": "master_style_2_corporate.pptx",
        "bold": "master_style_3_bold.pptx",
    }
    if style not in mapping:
        raise ValueError(f"Unknown style: {style}. Available: {list(mapping.keys())}")
    return mapping[style]
