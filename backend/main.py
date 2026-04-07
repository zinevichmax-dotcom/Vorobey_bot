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
from builders.compliance_report_builder import build_compliance_report
from builders.diff_report_builder import build_diff_report
from compliance.compliance_checker import check_compliance
from compliance.document_store import get_regulatory_summary, upload_regulatory_doc
from normalizers.pptx_normalizer import normalize_pptx
from parsers.docx_diff import compare_documents
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


@app.post("/compare/docx")
async def compare_documents_endpoint(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    format: str = "docx",  # "docx" или "json"
):
    """
    Загрузи 2 DOCX файла → получи отчёт о различиях.
    format=docx → DOCX с выделенными различиями
    format=json → JSON со списком изменений
    """
    if not (file_a.filename or "").endswith(".docx") or not (file_b.filename or "").endswith(".docx"):
        raise HTTPException(400, "Оба файла должны быть .docx")

    job_id = str(uuid.uuid4())[:8]
    path_a = os.path.join(UPLOAD_DIR, f"{job_id}_a.docx")
    path_b = os.path.join(UPLOAD_DIR, f"{job_id}_b.docx")
    output_path = os.path.join(UPLOAD_DIR, f"{job_id}_diff_report.docx")

    with open(path_a, "wb") as f:
        shutil.copyfileobj(file_a.file, f)
    with open(path_b, "wb") as f:
        shutil.copyfileobj(file_b.file, f)

    # Сравниваем
    try:
        diff_result = compare_documents(path_a, path_b)
    except Exception as e:
        raise HTTPException(500, f"Ошибка сравнения: {str(e)}")

    # JSON формат
    if format == "json":
        return diff_result

    # DOCX формат
    try:
        build_diff_report(
            diff_result,
            output_path,
            name_a=file_a.filename,
            name_b=file_b.filename,
        )
    except Exception as e:
        raise HTTPException(500, f"Ошибка генерации отчёта: {str(e)}")

    return FileResponse(
        output_path,
        filename=f"diff_{file_a.filename}_vs_{file_b.filename}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.post("/compliance/upload-regulatory")
async def upload_regulatory_endpoint(
    file: UploadFile = File(...),
    doc_type: str = "federal_law",
    doc_name: str = "Документ",
):
    """
    Загрузить нормативный документ (ФЗ, Устав или Корп. договор).
    doc_type: federal_law | charter | corporate_agreement
    """
    if not (file.filename or "").endswith(".docx"):
        raise HTTPException(400, "Только .docx файлы")
    if doc_type not in ("federal_law", "charter", "corporate_agreement"):
        raise HTTPException(400, "doc_type: federal_law | charter | corporate_agreement")

    job_id = str(uuid.uuid4())[:8]
    temp_path = os.path.join(UPLOAD_DIR, f"{job_id}_{doc_type}.docx")

    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        meta = upload_regulatory_doc(temp_path, doc_type, doc_name)
    except Exception as e:
        raise HTTPException(500, f"Ошибка загрузки: {str(e)}")

    return {"status": "uploaded", "meta": meta}


@app.get("/compliance/regulatory-docs")
async def list_regulatory_docs():
    """Список загруженных нормативных документов."""
    return get_regulatory_summary()


@app.post("/compliance/check")
async def check_compliance_endpoint(
    file: UploadFile = File(...),
    format: str = "docx",
):
    """
    Проверить документ на соответствие загруженным НПА.
    format=docx → справка DOCX
    format=json → JSON с вердиктом
    """
    if not (file.filename or "").endswith(".docx"):
        raise HTTPException(400, "Только .docx файлы")

    job_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(UPLOAD_DIR, f"{job_id}_check.docx")
    output_path = os.path.join(UPLOAD_DIR, f"{job_id}_compliance_report.docx")

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Проверяем
    try:
        result = check_compliance(input_path)
    except Exception as e:
        raise HTTPException(500, f"Ошибка проверки: {str(e)}")

    if format == "json":
        return result

    # Собираем DOCX
    try:
        build_compliance_report(result, output_path, document_name=file.filename or "документ")
    except Exception as e:
        raise HTTPException(500, f"Ошибка генерации справки: {str(e)}")

    return FileResponse(
        output_path,
        filename=f"compliance_{file.filename}",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
