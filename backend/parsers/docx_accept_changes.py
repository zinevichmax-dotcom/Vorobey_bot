"""
Извлечение текста из DOCX с принятыми Track Changes.
Удаляет <w:del> (удалённое), включает <w:ins> (вставленное) как обычный текст.
Используется для compliance: проверяем финальную версию документа.
"""

import re
import zipfile
import xml.etree.ElementTree as ET


NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_MAP = {"w": NS}


def extract_text_with_accepted_changes(docx_path: str) -> str:
    """
    Применяет все Track Changes и возвращает финальный текст документа.
    """
    with zipfile.ZipFile(docx_path, "r") as z:
        with z.open("word/document.xml") as f:
            content = f.read()

    # Убираем все блоки <w:del>...</w:del> (удалённый текст)
    content_str = content.decode("utf-8")
    content_str = re.sub(
        r"<w:del\b[^>]*>.*?</w:del>",
        "",
        content_str,
        flags=re.DOTALL,
    )

    # Парсим очищенный XML
    root = ET.fromstring(content_str.encode("utf-8"))

    # Извлекаем весь текст (теперь <w:ins> остались, поскольку внутри них есть <w:t>)
    paragraphs = []
    for p in root.iter(f"{{{NS}}}p"):
        texts = []
        for t in p.iter(f"{{{NS}}}t"):
            if t.text:
                texts.append(t.text)
        para_text = "".join(texts).strip()
        if para_text:
            paragraphs.append(para_text)

    return "\n".join(paragraphs)

