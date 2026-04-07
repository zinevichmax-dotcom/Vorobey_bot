"""
Claude API: классифицирует элементы слайда когда имена шейпов не дают ответа.
Определяет: что заголовок, что тело, что подпись.
Также может сократить/переписать текст если слишком длинный.
"""

from __future__ import annotations

import json
import os

import anthropic


def classify_slide_elements(slide_data: dict) -> list[dict]:
    """
    Отправляет JSON слайда в Claude.
    Получает классификацию каждого текстового блока.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    prompt = f"""Вот JSON-структура одного слайда презентации.
Для каждого текстового shape определи его роль: title, subtitle, body, caption, или other.
Верни JSON массив: [{{"shape_id": ..., "role": "..."}}]

Только JSON, без пояснений.

Слайд:
{json.dumps(slide_data, indent=2, default=str, ensure_ascii=False)}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text

    # Парсим JSON из ответа
    try:
        clean = response_text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(clean)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def improve_text(text: str, role: str, max_chars: int = 200) -> str:
    """
    Если текст слишком длинный для слайда — сокращает.
    role: title | body | caption
    """
    if len(text) <= max_chars:
        return text

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    prompt = f"""Сократи этот текст для слайда презентации.
Роль текста: {role}
Максимум символов: {max_chars}
Сохрани смысл, убери воду.
Верни только сокращённый текст, без пояснений.

Текст:
{text}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()
