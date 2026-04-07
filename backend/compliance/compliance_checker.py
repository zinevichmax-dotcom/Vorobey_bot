"""
Трёхпроходная проверка compliance.
Проход 1: ФЗ-208 + документ
Проход 2: ФЗ-14 + Устав + документ
Проход 3: Корп. договор + документ
Merge: объединение результатов в единую справку.

Все документы проверяются ПОЛНОСТЬЮ, без обрезки.
"""

from __future__ import annotations

import json
import os

import anthropic
from docx import Document

from compliance.document_store import (
    PASS_GROUPS,
    VALID_DOC_TYPES,
    get_docs_for_pass,
    get_regulatory_texts,
)


def check_compliance(document_path: str) -> dict:
    """
    Проверяет документ на соответствие всем нормативным документам.
    Выполняет 3 прохода + merge.
    """
    # Извлекаем текст проверяемого документа
    doc_text = _extract_document_text(document_path)

    if not doc_text:
        return _error_result("Не удалось извлечь текст из документа.")

    # Проверяем наличие НПА
    all_docs = get_regulatory_texts()
    if not all_docs:
        return _error_result(
            "Нормативные документы не загружены. "
            "Загрузите ФЗ-208, ФЗ-14, Устав и Корпоративный договор."
        )

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # === ТРИ ПРОХОДА ===
    pass_results: list[dict] = []

    for pass_num in sorted(PASS_GROUPS.keys()):
        pass_docs = get_docs_for_pass(pass_num)
        if not pass_docs:
            continue

        result = _run_pass(client, pass_num, pass_docs, doc_text)
        pass_results.append(result)

    # === MERGE ===
    final = _merge_results(client, pass_results, doc_text)

    return final


def _run_pass(client, pass_num: int, pass_docs: dict, doc_text: str) -> dict:
    """Один проход проверки."""

    # Собираем тексты НПА для этого прохода
    regulatory_sections: list[str] = []
    doc_names: list[str] = []

    for doc_type, data in pass_docs.items():
        label = data["meta"].get("doc_type_label", doc_type)
        name = data["meta"]["doc_name"]
        doc_names.append(f"{label}: {name}")

        # ПОЛНЫЙ текст, без обрезки
        full_text = "\n".join(data["text"])
        regulatory_sections.append(
            f"{'=' * 60}\n" f"{label}: {name}\n" f"{'=' * 60}\n" f"{full_text}"
        )

    regulatory_text = "\n\n".join(regulatory_sections)

    prompt = f"""Ты — юрист-эксперт по корпоративному праву РФ.

ЗАДАЧА: Проверить документ на соответствие нормативным документам.

НОРМАТИВНЫЕ ДОКУМЕНТЫ (проход {pass_num}/3 — {', '.join(doc_names)}):

{regulatory_text}

{'=' * 60}
ПРОВЕРЯЕМЫЙ ДОКУМЕНТ:
{'=' * 60}

{doc_text}

ИНСТРУКЦИИ:
1. Проверь КАЖДОЕ существенное условие проверяемого документа на соответствие предоставленным нормативным документам
2. Для каждого нарушения укажи:
   - document_clause: какой пункт проверяемого документа нарушает
   - regulatory_reference: какую статью/пункт какого нормативного документа (с точным номером)
   - description: в чём конкретно нарушение
   - severity: "critical" (блокирует одобрение), "warning" (требует внимания), "info" (рекомендация)
   - recommendation: как исправить
3. Будь КОНКРЕТЕН: ссылайся на точные пункты, статьи, абзацы
4. Если нарушений по данным нормативным документам нет — так и скажи

Верни строго JSON:
{{
    "pass_num": {pass_num},
    "regulatory_docs_checked": {json.dumps(doc_names, ensure_ascii=False)},
    "violations": [
        {{
            "document_clause": "конкретный пункт",
            "regulatory_reference": "ст./п. нормативного документа",
            "description": "описание",
            "severity": "critical|warning|info",
            "recommendation": "как исправить"
        }}
    ],
    "notes": ["замечания если есть"]
}}

Только JSON."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()

        # Парсим JSON
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(response_text)

    except json.JSONDecodeError:
        return {
            "pass_num": pass_num,
            "regulatory_docs_checked": doc_names,
            "violations": [],
            "notes": [f"Ошибка парсинга ответа AI для прохода {pass_num}"],
            "raw_response": response_text[:500] if "response_text" in locals() else "",
        }
    except Exception as e:
        return {
            "pass_num": pass_num,
            "regulatory_docs_checked": doc_names,
            "violations": [],
            "notes": [f"Ошибка API при проходе {pass_num}: {str(e)}"],
        }


def _merge_results(client, pass_results: list, doc_text: str) -> dict:
    """Объединяет результаты трёх проходов в единую справку."""

    # Собираем все нарушения
    all_violations: list[dict] = []
    all_notes: list[str] = []
    all_docs_checked: list[str] = []

    for result in pass_results:
        all_violations.extend(result.get("violations", []))
        all_notes.extend(result.get("notes", []))
        all_docs_checked.extend(result.get("regulatory_docs_checked", []))

    # Определяем вердикт
    has_critical = any(v.get("severity") == "critical" for v in all_violations)

    # Если нарушений мало — не нужен дополнительный merge через Claude
    if len(all_violations) <= 10:
        return {
            "approved": not has_critical,
            "verdict": "НЕ ОДОБРЕНО" if has_critical else "ОДОБРЕНО",
            "summary": _generate_summary(all_violations, all_docs_checked),
            "violations": all_violations,
            "notes": all_notes,
            "passes_completed": len(pass_results),
            "regulatory_docs_checked": all_docs_checked,
        }

    # Много нарушений — просим Claude объединить и дедуплицировать
    try:
        merge_prompt = f"""Объедини результаты проверки документа из {len(pass_results)} проходов.

Все найденные нарушения:
{json.dumps(all_violations, ensure_ascii=False, indent=2)}

Задачи:
1. Удали дубликаты (одно нарушение могло быть найдено в разных проходах)
2. Объедини связанные нарушения
3. Отсортируй: critical → warning → info
4. Сформулируй краткое резюме (2-3 предложения)

Верни JSON:
{{
    "approved": true/false,
    "verdict": "ОДОБРЕНО" или "НЕ ОДОБРЕНО",
    "summary": "резюме",
    "violations": [уникальные нарушения],
    "notes": ["замечания"]
}}

Только JSON."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": merge_prompt}],
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]

        merged = json.loads(response_text)
        merged["passes_completed"] = len(pass_results)
        merged["regulatory_docs_checked"] = all_docs_checked
        return merged

    except Exception:
        # Fallback: просто объединяем без дедупликации
        return {
            "approved": not has_critical,
            "verdict": "НЕ ОДОБРЕНО" if has_critical else "ОДОБРЕНО",
            "summary": _generate_summary(all_violations, all_docs_checked),
            "violations": all_violations,
            "notes": all_notes + ["Автоматическая дедупликация не выполнена"],
            "passes_completed": len(pass_results),
            "regulatory_docs_checked": all_docs_checked,
        }


def _generate_summary(violations: list, docs_checked: list) -> str:
    """Генерирует краткое резюме без Claude."""
    critical = sum(1 for v in violations if v.get("severity") == "critical")
    warning = sum(1 for v in violations if v.get("severity") == "warning")
    info = sum(1 for v in violations if v.get("severity") == "info")

    parts = [f"Проверка выполнена по {len(docs_checked)} нормативным документам."]

    if not violations:
        parts.append("Нарушений не выявлено.")
    else:
        parts.append(f"Выявлено: {critical} критических, {warning} предупреждений, {info} информационных замечаний.")

    if critical > 0:
        parts.append("Документ НЕ МОЖЕТ быть одобрен до устранения критических нарушений.")
    else:
        parts.append("Критических нарушений нет, документ может быть одобрен.")

    return " ".join(parts)


def _extract_document_text(document_path: str) -> str:
    """Извлекает текст из проверяемого документа (DOCX или ODT)."""
    ext = os.path.splitext(document_path)[1].lower()

    if ext == ".docx":
        doc = Document(document_path)
        paragraphs: list[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_texts = [c.text.strip() for c in row.cells if c.text.strip()]
                if row_texts:
                    paragraphs.append(" | ".join(row_texts))
        return "\n".join(paragraphs)

    if ext == ".odt":
        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(document_path, "r") as z:
            with z.open("content.xml") as f:
                tree = ET.parse(f)
        root = tree.getroot()
        texts: list[str] = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                texts.append(elem.text.strip())
            if elem.tail and elem.tail.strip():
                texts.append(elem.tail.strip())
        return "\n".join(texts)

    raise ValueError(f"Неподдерживаемый формат: {ext}")


def _error_result(message: str) -> dict:
    """Возвращает результат-ошибку."""
    return {
        "approved": False,
        "verdict": "ПРОВЕРКА НЕВОЗМОЖНА",
        "summary": message,
        "violations": [],
        "notes": [],
        "passes_completed": 0,
        "regulatory_docs_checked": [],
    }

