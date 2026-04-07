"""
Хранилище нормативных документов.
Загружаются один раз, извлекается текст, кешируется.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil

from docx import Document


STORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "compliance_docs"))


def init_store():
    """Создаёт папку хранилища если нет."""
    os.makedirs(STORE_DIR, exist_ok=True)
    os.makedirs(os.path.join(STORE_DIR, "originals"), exist_ok=True)
    os.makedirs(os.path.join(STORE_DIR, "extracted"), exist_ok=True)


def upload_regulatory_doc(docx_path: str, doc_type: str, doc_name: str) -> dict:
    """
    Загружает нормативный документ в хранилище.
    doc_type: "federal_law" | "charter" | "corporate_agreement"
    """
    init_store()

    # Извлекаем текст
    text = _extract_text(docx_path)

    # Считаем хеш для дедупликации
    with open(docx_path, "rb") as f:
        file_hash = hashlib.md5(f.read()).hexdigest()[:12]

    # Сохраняем метаданные
    meta = {
        "doc_type": doc_type,
        "doc_name": doc_name,
        "file_hash": file_hash,
        "paragraphs": len(text),
        "char_count": sum(len(t) for t in text),
    }

    # Сохраняем извлечённый текст
    text_path = os.path.join(STORE_DIR, "extracted", f"{doc_type}.json")
    with open(text_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "text": text}, f, ensure_ascii=False, indent=2)

    # Копируем оригинал
    orig_path = os.path.join(STORE_DIR, "originals", f"{doc_type}.docx")
    shutil.copy2(docx_path, orig_path)

    return meta


def get_regulatory_texts() -> dict:
    """
    Возвращает тексты всех загруженных нормативных документов.
    {
        "federal_law": {"meta": {...}, "text": [...]},
        "charter": {"meta": {...}, "text": [...]},
        "corporate_agreement": {"meta": {...}, "text": [...]},
    }
    """
    init_store()
    extracted_dir = os.path.join(STORE_DIR, "extracted")
    docs: dict = {}

    for filename in os.listdir(extracted_dir):
        if filename.endswith(".json"):
            doc_type = filename.replace(".json", "")
            with open(os.path.join(extracted_dir, filename), "r", encoding="utf-8") as f:
                docs[doc_type] = json.load(f)

    return docs


def get_regulatory_summary() -> list:
    """Список загруженных документов с метаданными."""
    docs = get_regulatory_texts()
    return [
        {
            "doc_type": dtype,
            "doc_name": data["meta"]["doc_name"],
            "paragraphs": data["meta"]["paragraphs"],
            "char_count": data["meta"]["char_count"],
        }
        for dtype, data in docs.items()
    ]


def _extract_text(docx_path: str) -> list[str]:
    """Извлекает текст из DOCX по абзацам."""
    doc = Document(docx_path)
    paragraphs: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    # Таблицы тоже
    for table in doc.tables:
        for row in table.rows:
            row_texts: list[str] = []
            for cell in row.cells:
                if cell.text.strip():
                    row_texts.append(cell.text.strip())
            if row_texts:
                paragraphs.append(" | ".join(row_texts))

    return paragraphs

