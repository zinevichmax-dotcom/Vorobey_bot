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

from normalizers.pptx_normalizer import normalize_pptx

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
