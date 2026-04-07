"""
Клиент ЕГРЮЛ через DaData API.
Поиск организаций по ИНН/ОГРН, извлечение персоналий.
"""

from __future__ import annotations

import os

import requests


DADATA_FIND_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
DADATA_SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"


def get_api_key() -> str:
    key = os.environ.get("DADATA_API_KEY")
    if not key:
        raise ValueError(
            "DADATA_API_KEY не задан. " "Получите ключ на https://dadata.ru и добавьте в .env"
        )
    return key


def find_by_inn_or_ogrn(query: str) -> dict:
    """Поиск организации по ИНН или ОГРН. Возвращает структурированные данные."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {get_api_key()}",
    }
    response = requests.post(DADATA_FIND_URL, json={"query": query}, headers=headers, timeout=30)
    response.raise_for_status()

    suggestions = response.json().get("suggestions", [])
    if not suggestions:
        return {"found": False, "query": query}

    return _parse_company(suggestions[0])


def search_by_name(name: str, count: int = 5) -> list[dict]:
    """Поиск организаций по названию."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {get_api_key()}",
    }
    response = requests.post(
        DADATA_SUGGEST_URL,
        json={"query": name, "count": count},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return [_parse_company(s) for s in response.json().get("suggestions", [])]


def get_persons(inn_or_ogrn: str) -> dict:
    """
    Извлекает всех персоналий организации для проверки заинтересованности.
    Возвращает:
    {
        "company": "ООО Ромашка",
        "inn": "...",
        "ogrn": "...",
        "director": {"name": "...", "post": "..."},
        "founders": [{"name": "...", "inn": "...", "share_percent": ...}],
        "founder_companies": [{"name": "...", "inn": "...", "share_percent": ...}],
    }
    """
    data = find_by_inn_or_ogrn(inn_or_ogrn)
    if not data.get("found"):
        return data

    # Разделяем учредителей на физлиц и юрлиц
    founders_persons: list[dict] = []
    founders_companies: list[dict] = []

    for f in data.get("founders", []):
        share_pct = None
        share_data = f.get("share", {}) or {}
        if share_data:
            if share_data.get("type") == "PERCENT":
                share_pct = share_data.get("value")
            elif share_data.get("numerator") and share_data.get("denominator"):
                share_pct = round(share_data["numerator"] / share_data["denominator"] * 100, 2)

        entry = {
            "name": f.get("name", ""),
            "inn": f.get("inn", ""),
            "share_percent": share_pct,
        }

        # Если у учредителя есть ОГРН — это юрлицо
        if f.get("ogrn"):
            entry["ogrn"] = f["ogrn"]
            founders_companies.append(entry)
        else:
            founders_persons.append(entry)

    return {
        "found": True,
        "company": data.get("name_short", ""),
        "company_full": data.get("name_full", ""),
        "inn": data.get("inn", ""),
        "ogrn": data.get("ogrn", ""),
        "type": data.get("type", ""),
        "opf": data.get("opf", ""),
        "director": data.get("management", {}),
        "founders_persons": founders_persons,
        "founders_companies": founders_companies,
        "address": data.get("address", ""),
        "status": data.get("status", ""),
    }


def get_persons_recursive(inn_or_ogrn: str, depth: int = 2) -> dict:
    """
    Извлекает персоналий с рекурсивным раскрытием учредителей-юрлиц.
    depth=2: раскрываем юрлиц-учредителей на 2 уровня.
    """
    base = get_persons(inn_or_ogrn)
    if not base.get("found"):
        return base

    if depth <= 0:
        return base

    # Рекурсивно раскрываем учредителей-юрлиц
    expanded_companies: list[dict] = []
    for fc in base.get("founders_companies", []):
        if fc.get("inn"):
            sub = get_persons_recursive(fc["inn"], depth=depth - 1)
            fc["sub_persons"] = sub
        expanded_companies.append(fc)

    base["founders_companies"] = expanded_companies
    return base


def _parse_company(suggestion: dict) -> dict:
    """Парсит ответ DaData."""
    data = suggestion.get("data", {}) or {}
    management = data.get("management", {}) or {}
    address = data.get("address", {}) or {}
    state = data.get("state", {}) or {}
    opf = data.get("opf", {}) or {}
    name_data = data.get("name", {}) or {}

    founders: list[dict] = []
    for f in data.get("founders") or []:
        if not f:
            continue
        founders.append(
            {
                "name": f.get("name", ""),
                "inn": f.get("inn", ""),
                "ogrn": f.get("ogrn", ""),
                "share": f.get("share", {}) or {},
            }
        )

    return {
        "found": True,
        "name_short": name_data.get("short_with_opf", suggestion.get("value", "")),
        "name_full": name_data.get("full_with_opf", ""),
        "inn": data.get("inn", ""),
        "ogrn": data.get("ogrn", ""),
        "kpp": data.get("kpp", ""),
        "opf": opf.get("full", ""),
        "type": data.get("type", ""),
        "address": address.get("unrestricted_value", address.get("value", "")),
        "management": {
            "name": management.get("name", ""),
            "post": management.get("post", ""),
        },
        "founders": founders,
        "status": state.get("status", ""),
    }

