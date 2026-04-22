"""
Генератор допсоглашений через Claude API.
Получает список значимых правок → формулирует пункты допсоглашения.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import anthropic


def generate_supplement_agreement(
    changes: list,
    contract_name: str = "Договор",
    contract_number: str = "",
    contract_date: str = "",
    party_1: str = "Сторона 1",
    party_2: str = "Сторона 2",
) -> dict:
    """
    Генерирует текст допсоглашения на основе Track Changes.

    Возвращает:
    {
        "title": "Дополнительное соглашение №...",
        "preamble": "...",
        "clauses": [
            {"num": 1, "text": "Пункт 3.1 Договора изложить в следующей редакции: ..."},
            ...
        ],
        "closing": "..."
    }
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Группируем правки по параграфам
    changes_text = _format_changes_for_prompt(changes)

    prompt = f"""Ты — юрист-документовед. На основе списка правок (Track Changes) к договору
сформулируй пункты дополнительного соглашения.

Исходный документ: {contract_name}
{f'Номер: {contract_number}' if contract_number else ''}
{f'Дата: {contract_date}' if contract_date else ''}
Сторона 1: {party_1}
Сторона 2: {party_2}

Правки из Track Changes:
{changes_text}

Правила:
1. Каждая значимая правка = отдельный пункт допсоглашения
2. Используй стандартные юридические формулировки:
   - "Пункт X.X Договора изложить в следующей редакции: ..."
   - "Пункт X.X Договора дополнить следующим содержанием: ..."
   - "Пункт X.X Договора исключить."
   - "Слова «...» заменить словами «...»"
3. Если правка — замена (удаление + вставка в том же месте), объедини в один пункт
4. Сохраняй точные формулировки из правок, не перефразируй содержание

Верни строго JSON:
{{
    "clauses": [
        {{"num": 1, "text": "формулировка пункта допсоглашения"}},
        ...
    ]
}}

Только JSON, без пояснений, без markdown."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # Парсим JSON
    try:
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(response_text)
    except json.JSONDecodeError:
        data = {"clauses": [{"num": 1, "text": response_text}]}

    # Формируем полный документ
    today = datetime.now().strftime("%d.%m.%Y")
    title = "ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ"
    if contract_number:
        title += f"\nк {_to_dative(contract_name)} № {contract_number}"
    if contract_date:
        title += f" от {contract_date}"

    preamble = (
        f"г. Москва{' ' * 40}{today}\n\n"
        f"{party_1}, с одной стороны, и {party_2}, с другой стороны, "
        f"совместно именуемые «Стороны», заключили настоящее Дополнительное соглашение "
        f"о нижеследующем:"
    )

    closing = (
        "Настоящее Дополнительное соглашение вступает в силу с момента его подписания "
        "обеими Сторонами и является неотъемлемой частью Договора.\n\n"
        "Настоящее Дополнительное соглашение составлено в двух экземплярах, "
        "имеющих одинаковую юридическую силу, по одному для каждой из Сторон.\n\n"
        f"{'_' * 30}{' ' * 10}{'_' * 30}\n"
        f"{party_1}{' ' * (40 - len(party_1))}{party_2}"
    )

    return {
        "title": title,
        "preamble": preamble,
        "clauses": data.get("clauses", []),
        "closing": closing,
    }


def _format_changes_for_prompt(changes: list) -> str:
    """Форматирует правки для промпта."""
    lines: list[str] = []
    for c in changes:
        if c.get("type") == "deletion":
            lines.append(f"УДАЛЕНО (п.{c['paragraph_num']}): «{c['text']}»")
        else:
            lines.append(f"ДОБАВЛЕНО (п.{c['paragraph_num']}): «{c['text']}»")

        if c.get("context"):
            lines.append(f"  Контекст: {c['context'][:80]}")
        lines.append("")

    return "\n".join(lines)


def _to_dative(name: str) -> str:
    """
    Склоняет название договора в дательный падеж.
    'Договор аренды' → 'Договору аренды'.
    Простое правило: меняем первое слово по таблице, остальное не трогаем.
    """
    if not name:
        return name

    words = name.split()
    if not words:
        return name

    first = words[0]
    first_lower = first.lower()

    # Таблица склонений в дательный падеж
    dative_map = {
        "договор": "договору",
        "соглашение": "соглашению",
        "контракт": "контракту",
        "дополнение": "дополнению",
        "приложение": "приложению",
    }

    if first_lower in dative_map:
        replacement = dative_map[first_lower]
        # Сохраняем регистр: если было с большой буквы — вернём с большой
        if first[0].isupper():
            replacement = replacement.capitalize()
        words[0] = replacement

    return " ".join(words)

