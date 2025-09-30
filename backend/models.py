# models.py - ОБНОВЛЕННАЯ ВЕРСИЯ
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class ProcessingStatus(str, Enum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing" 
    ANALYZED = "analyzed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class FaceBoundingBox(BaseModel):
    """Модель ограничивающего прямоугольника лица"""
    x: int = Field(..., description="X координата левого верхнего угла")
    y: int = Field(..., description="Y координата левого верхнего угла")
    width: int = Field(..., description="Ширина прямоугольника")
    height: int = Field(..., description="Высота прямоугольника")
    confidence: float = Field(1.0, description="Уверенность детекции")

class VideoUploadResponse(BaseModel):
    """Ответ на загрузку видео"""
    video_id: str = Field(..., description="Уникальный идентификатор видео")
    status: str = Field(..., description="Статус обработки")
    message: str = Field(..., description="Сообщение для пользователя")
    video_info: Optional[Dict] = Field(None, description="Информация о видео")

class AnalysisResult(BaseModel):
    """Результаты анализа видео"""
    video_info: Dict[str, Any]
    faces_by_frame: Dict[str, List[FaceBoundingBox]]
    analysis_settings: Dict[str, Any]

class PreviewRequest(BaseModel):
    """Запрос на генерацию превью"""
    masks: Dict[str, List[FaceBoundingBox]] = Field(..., description="Маски для размытия")
    blur_strength: int = Field(15, ge=1, le=50, description="Сила размытия (1-50)")
    preview_duration: int = Field(10, ge=5, le=30, description="Длительность превью в секундах")

class ProcessRequest(BaseModel):
    """Запрос на обработку видео"""
    masks: Dict[str, List[FaceBoundingBox]] = Field(..., description="Маски для размытия")
    blur_strength: int = Field(15, ge=1, le=50, description="Сила размытия (1-50)")

class StatusResponse(BaseModel):
    """Ответ со статусом обработки"""
    video_id: str
    status: ProcessingStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    message: str
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    """Модель ошибки"""
    error: str
    details: Optional[str] = None
    video_id: Optional[str] = None