"""
Главный оркестратор редизайна.
redesign(input_pptx, style, output_pptx) — всё в одну функцию.
"""
import os
import tempfile
from anthropic import Anthropic

try:
    from .pptx_parser import parse_pptx
    from .slide_classifier import classify_presentation
    from .slide_builder import build_presentation
except ImportError:
    from pptx_parser import parse_pptx
    from slide_classifier import classify_presentation
    from slide_builder import build_presentation


def redesign(
    input_pptx_path: str,
    style: str,
    output_pptx_path: str,
    anthropic_api_key: str | None = None,
    work_dir: str | None = None,
) -> dict:
    """
    Полный pipeline редизайна.
    
    Args:
        input_pptx_path: исходная презентация
        style: "formal" | "corporate" | "bold"
        output_pptx_path: куда сохранить результат
        anthropic_api_key: ключ API
        work_dir: рабочая папка (tmp/ если None)
    
    Returns:
        {
            "success": bool,
            "output_path": str,
            "input_slides": int,
            "output_slides": int,
            "reasoning_log": list,
            "warnings": list,
        }
    """
    warnings = []
    
    # Подготовка рабочей папки
    if work_dir is None:
        work_dir = tempfile.mkdtemp(prefix="redesign_")
    os.makedirs(work_dir, exist_ok=True)
    images_dir = os.path.join(work_dir, "images")
    
    # 1. Парсинг
    try:
        parsed = parse_pptx(input_pptx_path, images_dir)
    except Exception as e:
        return {
            "success": False,
            "error": f"Parser failed: {e}",
            "warnings": warnings,
        }
    
    if parsed["total_slides"] == 0:
        return {
            "success": False,
            "error": "Empty presentation",
        }
    
    # 2. Классификация
    api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "ANTHROPIC_API_KEY not set",
        }
    client = Anthropic(api_key=api_key)
    
    try:
        slides_spec, classifications = classify_presentation(parsed, client)
    except Exception as e:
        return {
            "success": False,
            "error": f"Classifier failed: {e}",
            "warnings": warnings,
        }
    
    # 2.5. Sanity-check: downgrade image layouts без картинки → text_heavy
    for spec in slides_spec:
        kind = spec.get("layout_kind")
        content = spec.get("content", {})
        if kind in ("image_text", "image_full"):
            img_path = content.get("_image_path")
            if not img_path or not os.path.exists(img_path):
                # Картинка не доступна — даунгрейд на text_heavy
                spec["layout_kind"] = "text_heavy"
                # Маппим поля image_* → text_heavy поля
                if "HEADING" not in content:
                    content["HEADING"] = content.get("KICKER", "")
                if "BODY_TEXT" in content and "LEAD" not in content:
                    content["LEAD"] = content.pop("KICKER", "")
                warnings.append(f"Slide downgraded: {kind} → text_heavy (no image)")
    
    # 3. Сборка
    try:
        build_presentation(
            slides_spec=slides_spec,
            style=style,
            output_path=output_pptx_path,
            source_pptx_path=input_pptx_path,
        )
    except Exception as e:
        return {
            "success": False,
            "error": f"Builder failed: {e}",
            "warnings": warnings,
        }
    
    # Статистика
    kinds_count = {}
    for s in slides_spec:
        k = s.get("layout_kind", "?")
        kinds_count[k] = kinds_count.get(k, 0) + 1
    
    return {
        "success": True,
        "output_path": output_pptx_path,
        "input_slides": parsed["total_slides"],
        "output_slides": len(slides_spec),
        "layout_distribution": kinds_count,
        "reasoning_log": [c.get("reasoning", "") for c in classifications],
        "warnings": warnings,
    }


if __name__ == "__main__":
    # Тест на Muted презе
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/refs/4_muted.pptx"
    style = sys.argv[2] if len(sys.argv) > 2 else "formal"
    output = f"/tmp/redesigned_{style}.pptx"
    
    result = redesign(input_file, style, output)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
