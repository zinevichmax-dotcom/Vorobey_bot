"""
Извлечение метаданных из DOCX договора:
- Название, Номер, Дата
- Стороны
"""
import re
from docx import Document


def extract_metadata(docx_path: str) -> dict:
    doc = Document(docx_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()][:50]

    # Для поиска сторон ищем абзац с "именуем" — обычно это преамбула, 1 абзац
    preamble = ""
    for p in paragraphs[:10]:
        if "именуем" in p.lower():
            preamble = p
            break

    full_text = "\n".join(paragraphs)

    return {
        "contract_name": _extract_name(paragraphs),
        "contract_number": _extract_number(full_text),
        "contract_date": _extract_date(full_text),
        "party_1": _extract_party_1(preamble),
        "party_2": _extract_party_2(preamble),
    }


def _extract_name(paragraphs: list[str]) -> str:
    """Название договора = первая короткая строка с ключевым словом."""
    keywords = ["договор", "соглашение", "контракт"]
    for p in paragraphs[:5]:
        p_lower = p.lower()
        if any(k in p_lower for k in keywords) and len(p) < 100:
            # Убираем номер
            name = re.sub(r"№\s*[\w\-/]+.*", "", p).strip()
            # Убираем дату в конце
            name = re.sub(r"от\s+«?\d+.*", "", name).strip()
            # Убираем запятые в конце
            name = name.rstrip(" ,;:-")
            if name:
                if name.isupper():
                    # ДОГОВОР АРЕНДЫ → Договор аренды
                    name = name[0] + name[1:].lower()
                return name
    return "Договор"


def _extract_number(text: str) -> str:
    patterns = [
        r"№\s*([\w\-/]+)",
        r"No\s*([\w\-/]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            num = match.group(1).strip(".,;")
            if 0 < len(num) < 50:
                return num
    return ""


def _extract_date(text: str) -> str:
    # дд.мм.гггг
    match = re.search(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\b", text)
    if match:
        return f"{match.group(1).zfill(2)}.{match.group(2).zfill(2)}.{match.group(3)}"

    # «15» марта 2025 или 15 марта 2025
    months = {
        "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
        "мая": "05", "июня": "06", "июля": "07", "августа": "08",
        "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
    }
    match = re.search(
        r"«?(\d{1,2})»?\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if match:
        day = match.group(1).zfill(2)
        month = months[match.group(2).lower()]
        year = match.group(3)
        return f"{day}.{month}.{year}"

    return ""


def _extract_party_1(preamble: str) -> str:
    """
    Сторона 1 — от начала преамбулы до ', именуем...'
    Работает только с абзацем-преамбулой, не со всем текстом.
    """
    if not preamble:
        return ""

    # Берём всё до первого ", именуем"
    match = re.match(r"^(.+?),\s+именуем", preamble, re.IGNORECASE)
    if not match:
        return ""

    name = match.group(1).strip()

    # Если название слишком длинное — обрезаем по кавычкам (юрлицо заканчивается закрытой кавычкой)
    # ООО «Ромашка» — закрывающая »
    if "»" in name and len(name) > 80:
        name = name[: name.rindex("»") + 1]

    # Базовая санитизация
    name = name.strip(" ,;:-")
    if 3 < len(name) < 200:
        return name
    return ""


def _extract_party_2(preamble: str) -> str:
    """
    Сторона 2 — после 'с одной стороны, и' до ', именуем' или ', с другой'.
    """
    if not preamble:
        return ""

    # Вариант 1: ...с одной стороны, и X, именуем...
    match = re.search(
        r"с\s+одной\s+стороны,?\s+и\s+(.+?),\s+именуем",
        preamble,
        re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip(" ,;:-")
        if 3 < len(name) < 200:
            return name

    # Вариант 2: ...с одной стороны, и X, с другой стороны
    match = re.search(
        r"с\s+одной\s+стороны,?\s+и\s+(.+?),\s+с\s+другой\s+стороны",
        preamble,
        re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip(" ,;:-")
        # Обрезаем по первой запятой с "именуем"/"действующ"
        name = re.split(r",\s+(именуем|действующ)", name)[0]
        name = name.strip(" ,;:-")
        if 3 < len(name) < 200:
            return name

    return ""


# Тест
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1:
        result = extract_metadata(sys.argv[1])
        print(json.dumps(result, indent=2, ensure_ascii=False))
