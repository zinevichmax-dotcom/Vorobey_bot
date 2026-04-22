"""
Snippet для вставки в backend/main.py.

Эндпоинт: POST /redesign/pptx
  - file: UploadFile (pptx)
  - style: str ("formal"/"corporate"/"bold")
  
Возвращает: StreamingResponse с новым .pptx
"""
# В backend/main.py добавить:

import os
import tempfile
from fastapi import UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from redesigner import redesign


@app.post("/redesign/pptx")
async def redesign_pptx(
    file: UploadFile = File(...),
    style: str = Form(...),
):
    """
    Редизайн PPTX в один из 3 стилей.
    style: "formal" | "corporate" | "bold"
    """
    if style not in ("formal", "corporate", "bold"):
        raise HTTPException(400, "Invalid style. Use: formal, corporate, bold")
    
    if not file.filename.lower().endswith(".pptx"):
        raise HTTPException(400, "Only .pptx files supported")
    
    # Сохранить загрузку во временный файл
    tmpdir = tempfile.mkdtemp(prefix="redesign_in_")
    input_path = os.path.join(tmpdir, file.filename)
    with open(input_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Выходной файл
    output_path = os.path.join(tmpdir, f"redesigned_{style}.pptx")
    
    # Запустить pipeline
    result = redesign(
        input_pptx_path=input_path,
        style=style,
        output_pptx_path=output_path,
    )
    
    if not result.get("success"):
        raise HTTPException(500, result.get("error", "Unknown error"))
    
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"redesigned_{style}_{file.filename}",
    )
