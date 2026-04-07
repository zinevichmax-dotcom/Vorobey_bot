"""
Проверка документа на соответствие нормативным документам через Claude.
"""

from __future__ import annotations

import json
import os

import anthropic

from compliance.document_store import _extract_text, get_regulatory_texts


def check_compliance(document_path: str) -> dict:
    """
    Проверяет документ на соответствие ФЗ, Уставу, Корп. договору.

    Возвращает:
    {
        "approved": True/False,
        "verdict": "ОДОБРЕНО" / "НЕ ОДОБРЕНО",
        "summary": "Краткое резюме",
        "violations": [
            {
                "document_clause": "п.3.1 проверяемого договора",
                "regulatory_reference": "ст.15 ФЗ / п.7.2 Устава",
                "description": "Описание нарушения",
                "severity": "critical" | "warning" | "info",
                "recommendation": "Рекомендация по исправлению",
            }
        ],
        "notes": ["Общие замечания"],
    }
    """
    # Извлекаем текст проверяемого документа
    doc_text = _extract_text(document_path)

    # Загружаем нормативные документы
    regulatory = get_regulatory_texts()

    if not regulatory:
        return {
            "approved": False,
            "verdict": "ПРОВЕРКА НЕВОЗМОЖНА",
            "summary": "Нормативные документы не загружены. Загрузите ФЗ, Устав и Корпоративный договор.",
            "violations": [],
            "notes": [],
        }

    # Формируем промпт
    prompt = _build_prompt(doc_text, regulatory)

    # Отправляем в Claude
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # Парсим ответ
    try:
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(response_text)
    except json.JSONDecodeError:
        result = {
            "approved": False,
            "verdict": "ОШИБКА АНАЛИЗА",
            "summary": response_text[:500],
            "violations": [],
            "notes": ["Не удалось разобрать ответ AI. Требуется ручная проверка."],
        }

    return result


def _build_prompt(doc_text: list, regulatory: dict) -> str:
    """Собирает промпт для Claude."""

    reg_sections: list[str] = []
    for doc_type, data in regulatory.items():
        name = data["meta"]["doc_name"]
        text = "\n".join(data["text"][:200])  # Лимит: первые 200 абзацев
        type_label = {
            "federal_law": "ФЕДЕРАЛЬНЫЙ ЗАКОН",
            "charter": "УСТАВ",
            "corporate_agreement": "КОРПОРАТИВНЫЙ ДОГОВОР",
        }.get(doc_type, doc_type.upper())

        reg_sections.append(f"=== {type_label}: {name} ===\n{text}")

    regulatory_text = "\n\n".join(reg_sections)
    document_text = "\n".join(doc_text[:300])  # Лимит

    return f"""Ты — юрист-эксперт по корпоративному праву РФ.

ЗАДАЧА: Проверить проверяемый документ на соответствие нормативным документам.
Дать или не дать одобрение. При отказе — подробная справка с указанием конкретных нарушений.

НОРМАТИВНЫЕ ДОКУМЕНТЫ:
{regulatory_text}

ПРОВЕРЯЕМЫЙ ДОКУМЕНТ:
{document_text}

ИНСТРУКЦИИ:
1. Проверь каждое существенное условие проверяемого документа на соответствие КАЖДОМУ нормативному документу
2. Для каждого нарушения укажи:
   - Какой пункт проверяемого документа нарушает
   - Какую норму (статью/пункт) какого нормативного документа
   - В чём конкретно нарушение
   - severity: "critical" (блокирует одобрение), "warning" (требует внимания), "info" (рекомендация)
   - Рекомендацию по исправлению
3. Документ одобряется ТОЛЬКО если нет critical нарушений
4. Будь конкретен: ссылайся на точные пункты и статьи

Верни строго JSON:
{{
    "approved": true/false,
    "verdict": "ОДОБРЕНО" или "НЕ ОДОБРЕНО",
    "summary": "Краткое резюме проверки в 2-3 предложения",
    "violations": [
        {{
            "document_clause": "конкретный пункт проверяемого документа",
            "regulatory_reference": "ст./п. нормативного документа",
            "description": "описание нарушения",
            "severity": "critical|warning|info",
            "recommendation": "как исправить"
        }}
    ],
    "notes": ["общие замечания если есть"]
}}

Только JSON, без markdown, без пояснений вне JSON."""

