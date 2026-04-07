"""
Парсер Track Changes из DOCX.
Извлекает вставки (<w:ins>) и удаления (<w:del>) из XML.
Возвращает структурированный список правок.
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET


# Namespace map для OOXML
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def extract_track_changes(docx_path: str) -> dict:
    """
    Извлекает все Track Changes из DOCX файла.
    Возвращает:
    {
        "changes": [
            {
                "id": "1",
                "type": "insertion" | "deletion",
                "author": "Иванов И.И.",
                "date": "2025-01-15T10:30:00Z",
                "text": "изменённый текст",
                "context_before": "текст до правки...",
                "context_after": "...текст после правки",
                "paragraph_num": 5,
            }
        ],
        "total_insertions": 3,
        "total_deletions": 2,
        "authors": ["Иванов И.И.", "Петров П.П."],
    }
    """
    # Распаковываем DOCX (это ZIP)
    with zipfile.ZipFile(docx_path, "r") as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)

    root = tree.getroot()
    body = root.find(".//w:body", NS)
    if body is None:
        return {"changes": [], "total_insertions": 0, "total_deletions": 0, "authors": []}

    changes: list[dict] = []
    authors: set[str] = set()
    para_num = 0

    for para in body.findall(".//w:p", NS):
        para_num += 1
        para_text = _get_para_text(para)

        # --- Вставки ---
        for ins in para.findall(".//w:ins", NS):
            change = _parse_change(ins, "insertion", para_num, para_text)
            if change:
                changes.append(change)
                if change.get("author"):
                    authors.add(change["author"])

        # --- Удаления ---
        for delete in para.findall(".//w:del", NS):
            change = _parse_change(delete, "deletion", para_num, para_text)
            if change:
                changes.append(change)
                if change.get("author"):
                    authors.add(change["author"])

    insertions = [c for c in changes if c["type"] == "insertion"]
    deletions = [c for c in changes if c["type"] == "deletion"]

    return {
        "changes": changes,
        "total_insertions": len(insertions),
        "total_deletions": len(deletions),
        "authors": sorted(authors),
    }


def _parse_change(element, change_type: str, para_num: int, para_text: str) -> dict | None:
    """Парсит один элемент ins или del."""
    change_id = element.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id")
    author = element.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}author", "")
    date = element.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}date", "")

    # Собираем текст из всех runs внутри
    texts: list[str] = []
    if change_type == "deletion":
        # В удалениях текст в <w:delText>
        for dt in element.findall(".//w:delText", NS):
            if dt.text:
                texts.append(dt.text)
    else:
        # Во вставках текст в <w:t>
        for t in element.findall(".//w:t", NS):
            if t.text:
                texts.append(t.text)

    text = "".join(texts).strip()
    if not text:
        return None

    # Контекст: берём текст параграфа
    context = para_text[:100] if para_text else ""

    return {
        "id": change_id,
        "type": change_type,
        "author": author,
        "date": date,
        "text": text,
        "context": context,
        "paragraph_num": para_num,
    }


def _get_para_text(para) -> str:
    """Извлекает полный текст параграфа (включая удалённый)."""
    texts: list[str] = []
    for t in para.findall(".//w:t", NS):
        if t.text:
            texts.append(t.text)
    for dt in para.findall(".//w:delText", NS):
        if dt.text:
            texts.append(dt.text)
    return " ".join(texts)


def filter_significant_changes(changes: list, min_length: int = 2) -> list:
    """
    Фильтрует незначимые правки:
    - Пробелы, запятые, точки
    - Изменения форматирования (пустой текст)
    - Слишком короткие (1 символ, если не цифра)
    """
    significant: list[dict] = []
    noise_patterns = re.compile(r"^[\s\.,;:\-–—]+$")

    for change in changes:
        text = (change.get("text") or "").strip()

        # Пропускаем пустые
        if not text:
            continue

        # Пропускаем пунктуацию/пробелы
        if noise_patterns.match(text):
            continue

        # Пропускаем слишком короткие (кроме цифр)
        if len(text) < min_length and not text.isdigit():
            continue

        significant.append(change)

    return significant


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Использование: python docx_track_changes.py договор.docx")
        raise SystemExit(1)

    result = extract_track_changes(sys.argv[1])
    significant = filter_significant_changes(result["changes"])

    print(f"Всего правок: {len(result['changes'])}")
    print(f"Значимых: {len(significant)}")
    print(f"Авторы: {result['authors']}")
    print()
    for c in significant:
        print(f"  [{c['type']}] п.{c['paragraph_num']}: \"{c['text'][:60]}\" (автор: {c['author']})")

