"""
Модуль редизайна PPTX.
Публичный API: redesign(input_path, style, output_path) -> dict
"""
from .orchestrator import redesign

__all__ = ["redesign"]
