"""
API сервер.
POST /normalize/pptx — загрузить PPTX, получить нормализованный.
POST /normalize/docx — загрузить DOCX, получить нормализованный.
"""

from __future__ import annotations

import os
import shutil
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from ai.agreement_generator import generate_supplement_agreement
from builders.agreement_builder import build_agreement_docx
from normalizers.pptx_normalizer import normalize_pptx
from parsers.docx_track_changes import extract_track_changes, filter_significant_changes

app = FastAPI(title="Vorobey Bot — Document Normalizer")

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # На проде заменить на домен
    allow_methods=["*"],
    allow_headers=["*"],
)

# Папка для временных файлов
UPLOAD_DIR = "/tmp/vorobey_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/normalize/pptx")
async def normalize_pptx_endpoint(file: UploadFile = File(...)):
    """Загрузи PPTX — получи нормализованный."""

    # Валидация
    if not (file.filename or "").endswith(".pptx"):
        raise HTTPException(400, "Только .pptx файлы")

    # Сохраняем входной файл
    job_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(UPLOAD_DIR, f"{job_id}_input.pptx")
    output_path = os.path.join(UPLOAD_DIR, f"{job_id}_output.pptx")

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Нормализуем
    try:
        normalize_pptx(input_path, output_path)
    except Exception as e:
        raise HTTPException(500, f"Ошибка обработки: {str(e)}")

    # Отдаём файл
    return FileResponse(
        output_path,
        filename=f"normalized_{file.filename}",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate/supplement")
async def generate_supplement_endpoint(
    file: UploadFile = File(...),
    contract_name: str = "Договор",
    contract_number: str = "",
    contract_date: str = "",
    party_1: str = "Сторона 1",
    party_2: str = "Сторона 2",
):
    """
    Загрузи DOCX с Track Changes → получи допсоглашение.
    """
    if not (file.filename or "").endswith(".docx"):
        raise HTTPException(400, "Только .docx файлы")

    # Сохраняем входной файл
    job_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(UPLOAD_DIR, f"{job_id}_contract.docx")
    output_path = os.path.join(UPLOAD_DIR, f"{job_id}_supplement.docx")

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 1. Извлекаем правки
    try:
        result = extract_track_changes(input_path)
    except Exception as e:
        raise HTTPException(500, f"Ошибка парсинга Track Changes: {str(e)}")

    # 2. Фильтруем незначимые
    significant = filter_significant_changes(result["changes"])

    if not significant:
        raise HTTPException(
            400,
            "В документе не найдены значимые правки (Track Changes). "
            "Убедитесь, что документ содержит режим правок.",
        )

    # 3. Генерируем допсоглашение через Claude
    try:
        agreement = generate_supplement_agreement(
            changes=significant,
            contract_name=contract_name,
            contract_number=contract_number,
            contract_date=contract_date,
            party_1=party_1,
            party_2=party_2,
        )
    except Exception as e:
        raise HTTPException(500, f"Ошибка генерации: {str(e)}")

    # 4. Собираем DOCX
    try:
        build_agreement_docx(agreement, output_path)
    except Exception as e:
        raise HTTPException(500, f"Ошибка сборки документа: {str(e)}")

    return FileResponse(
        output_path,
        filename=f"supplement_{file.filename}",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
