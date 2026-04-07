"""
Детектор заинтересованности в сделке.
Собирает персоналии обеих сторон → Claude анализирует по ст.81 ФЗ-208 / ст.45 ФЗ-14.
"""

from __future__ import annotations

import json
import os

import anthropic

from integrations.egrul import get_persons_recursive


def detect_interest(
    inn_a: str,
    inn_b: str,
    board_members_a: list[str] | None = None,
    board_members_b: list[str] | None = None,
    management_board_a: list[str] | None = None,
    management_board_b: list[str] | None = None,
    related_persons: list[dict] | None = None,
) -> dict:
    """
    Проверяет сделку на заинтересованность.

    Параметры:
    - inn_a, inn_b: ИНН/ОГРН обеих сторон
    - board_members_a/b: члены Совета директоров (ФИО)
    - management_board_a/b: члены правления (ФИО)
    - related_persons: связанные лица [{"name": "ФИО", "relation": "супруг директора А"}]

    Возвращает:
    {
        "interested": True/False,
        "persons": [...],
        "approval_required": "...",
        "applicable_law": "...",
        "company_a": {...},
        "company_b": {...},
    }
    """

    # 1. Получаем данные ЕГРЮЛ
    company_a = get_persons_recursive(inn_a, depth=2)
    company_b = get_persons_recursive(inn_b, depth=2)

    if not company_a.get("found"):
        return {"error": f"Сторона A (ИНН {inn_a}) не найдена в ЕГРЮЛ"}
    if not company_b.get("found"):
        return {"error": f"Сторона B (ИНН {inn_b}) не найдена в ЕГРЮЛ"}

    # 2. Формируем карточки персоналий
    card_a = _build_person_card(
        company_a,
        "A",
        board_members=board_members_a,
        management_board=management_board_a,
    )
    card_b = _build_person_card(
        company_b,
        "B",
        board_members=board_members_b,
        management_board=management_board_b,
    )

    # 3. Claude анализирует
    result = _analyze_interest(card_a, card_b, related_persons or [])

    # 4. Добавляем данные компаний в ответ
    result["company_a"] = {
        "name": company_a.get("company", ""),
        "inn": company_a.get("inn", ""),
        "ogrn": company_a.get("ogrn", ""),
        "opf": company_a.get("opf", ""),
    }
    result["company_b"] = {
        "name": company_b.get("company", ""),
        "inn": company_b.get("inn", ""),
        "ogrn": company_b.get("ogrn", ""),
        "opf": company_b.get("opf", ""),
    }

    return result


def _build_person_card(
    company: dict,
    side: str,
    board_members: list | None = None,
    management_board: list | None = None,
) -> str:
    """Формирует текстовую карточку персоналий компании."""
    lines = [
        f"=== СТОРОНА {side}: {company.get('company', 'Неизвестно')} ===",
        f"ИНН: {company.get('inn', '')}",
        f"ОГРН: {company.get('ogrn', '')}",
        f"ОПФ: {company.get('opf', '')}",
        "",
    ]

    # Директор
    director = company.get("director", {}) or {}
    if director.get("name"):
        lines.append("ЕДИНОЛИЧНЫЙ ИСПОЛНИТЕЛЬНЫЙ ОРГАН:")
        lines.append(f"  {director.get('post', 'Директор')}: {director['name']}")
        lines.append("")

    # Учредители — физлица
    founders_p = company.get("founders_persons", []) or []
    if founders_p:
        lines.append("УЧРЕДИТЕЛИ (физические лица):")
        for f in founders_p:
            share = f"доля {f['share_percent']}%" if f.get("share_percent") else ""
            inn_str = f"ИНН {f['inn']}" if f.get("inn") else ""
            lines.append(f"  {f['name']} {share} {inn_str}".strip())
        lines.append("")

    # Учредители — юрлица (с рекурсией)
    founders_c = company.get("founders_companies", []) or []
    if founders_c:
        lines.append("УЧРЕДИТЕЛИ (юридические лица):")
        for f in founders_c:
            share = f"доля {f['share_percent']}%" if f.get("share_percent") else ""
            lines.append(f"  {f['name']} ИНН {f.get('inn', '')} {share}")
            # Раскрытие вложенных
            sub = f.get("sub_persons", {}) or {}
            if sub and sub.get("found"):
                sub_dir = sub.get("director", {}) or {}
                if sub_dir.get("name"):
                    lines.append(f"    → директор: {sub_dir['name']}")
                for sf in sub.get("founders_persons", []) or []:
                    s_share = f"доля {sf['share_percent']}%" if sf.get("share_percent") else ""
                    lines.append(f"    → учредитель: {sf['name']} {s_share}")
        lines.append("")

    # Совет директоров (ручной ввод)
    if board_members:
        lines.append("СОВЕТ ДИРЕКТОРОВ (введены вручную):")
        for name in board_members:
            lines.append(f"  {name}")
        lines.append("")

    # Правление (ручной ввод)
    if management_board:
        lines.append("ПРАВЛЕНИЕ (введены вручную):")
        for name in management_board:
            lines.append(f"  {name}")
        lines.append("")

    return "\n".join(lines)


def _analyze_interest(card_a: str, card_b: str, related_persons: list) -> dict:
    """Claude анализирует персоналии на заинтересованность."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    related_text = ""
    if related_persons:
        related_text = "\nСВЯЗАННЫЕ ЛИЦА (указаны вручную):\n"
        for rp in related_persons:
            related_text += f"  {rp.get('name', '')}: {rp.get('relation', '')}\n"

    prompt = f"""Ты — юрист-эксперт по корпоративному праву РФ.

ЗАДАЧА: Определить наличие заинтересованности в сделке между двумя организациями.

НОРМАТИВНАЯ БАЗА:
- Ст. 81 ФЗ-208 «Об АО»: сделкой с заинтересованностью признаётся сделка, в совершении которой имеется заинтересованность члена совета директоров, единоличного исполнительного органа, члена коллегиального исполнительного органа, лица, являющегося контролирующим лицом общества, либо лица, имеющего право давать обществу обязательные указания.
- Указанные лица признаются заинтересованными, если они, их супруги, родители, дети, полнородные и неполнородные братья и сёстры, усыновители и усыновлённые и (или) подконтрольные им лица:
  а) являются стороной, выгодоприобретателем, посредником или представителем в сделке;
  б) являются контролирующим лицом юрлица, являющегося стороной, выгодоприобретателем, посредником или представителем;
  в) занимают должности в органах управления юрлица, являющегося стороной, выгодоприобретателем, посредником или представителем, а также контролирующего лица такого юрлица.

- Ст. 45 ФЗ-14 «Об ООО»: аналогичные критерии для обществ с ограниченной ответственностью.

ДАННЫЕ СТОРОН СДЕЛКИ:

{card_a}

{card_b}
{related_text}

ИНСТРУКЦИИ:
1. Сравни ВСЕ персоналии обеих сторон: директоры, учредители, члены СД, правление, связанные лица
2. Ищи ТОЧНЫЕ совпадения ФИО и ВОЗМОЖНЫЕ совпадения (однофамильцы — пометь как «требует проверки»)
3. Проверь перекрёстное владение: учредитель A = учредитель B, или учредитель A = директор B, и т.д.
4. Проверь контроль: доля >20% = контролирующее лицо
5. Для связанных лиц (родственники) — проверь их позиции в обеих компаниях
6. Определи какой закон применим (АО → ст.81 ФЗ-208, ООО → ст.45 ФЗ-14) по ОПФ каждой стороны
7. Если заинтересованность найдена — укажи какое одобрение требуется (Совет директоров / Общее собрание)

Верни строго JSON:
{{
    "interested": true/false,
    "confidence": "confirmed|likely|possible|none",
    "persons": [
        {{
            "name": "ФИО",
            "role_in_a": "должность/статус в компании A",
            "role_in_b": "должность/статус в компании B",
            "interest_type": "direct|control|related",
            "basis": "ст.81 п.1 ФЗ-208 / ст.45 п.1 ФЗ-14",
            "note": "пояснение"
        }}
    ],
    "approval_required": "описание какое одобрение нужно и по какому закону",
    "applicable_law": "ст.81-84 ФЗ-208 / ст.45-46 ФЗ-14",
    "warnings": ["предупреждения, однофамильцы, неполные данные"],
    "recommendations": ["рекомендации для дополнительной проверки"]
}}

Только JSON."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(response_text)

    except json.JSONDecodeError:
        return {
            "interested": False,
            "confidence": "none",
            "persons": [],
            "warnings": ["Ошибка разбора ответа AI. Требуется ручная проверка."],
        }
    except Exception as e:
        return {
            "interested": False,
            "confidence": "none",
            "persons": [],
            "warnings": [f"Ошибка API: {str(e)}"],
        }

