# temp_storage.py - ОБНОВЛЕННАЯ ВЕРСИЯ
import os
import shutil
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from models import ProcessingStatus

class TempStorage:
    """Управление временными файлами для веб-версии"""
    
    def __init__(self, base_temp_dir: str = "web_temp_uploads"):
        self.base_temp_dir = base_temp_dir
        self.sessions: Dict[str, Dict] = {}
        
        # Создаем базовую директорию
        os.makedirs(self.base_temp_dir, exist_ok=True)
        
        # Запускаем очистку старых файлов
        self._cleanup_old_files()
    
    def generate_video_id(self) -> str:
        """Генерирует уникальный идентификатор видео"""
        return str(uuid.uuid4())
    
    def create_session(self, video_id: str, original_filename: str) -> str:
        """Создает новую сессию обработки"""
        session_dir = os.path.join(self.base_temp_dir, video_id)
        os.makedirs(session_dir, exist_ok=True)
        
        self.sessions[video_id] = {
            'video_id': video_id,
            'original_filename': original_filename,
            'session_dir': session_dir,
            'created_at': datetime.now(),
            'status': ProcessingStatus.UPLOADED,
            'progress': 0.0,
            'message': 'Video uploaded',
            'files': {
                'uploaded_video': None,
                'analysis_json': None,
                'preview_video': None,
                'output_video': None
            }
        }
        
        return session_dir
    
    def save_uploaded_file(self, video_id: str, file_content: bytes) -> str:
        """Сохраняет загруженный видеофайл"""
        if video_id not in self.sessions:
            raise ValueError(f"Session {video_id} not found")
        
        session_dir = self.get_session_dir(video_id)
        file_path = os.path.join(session_dir, "original_video.mp4")
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        self.sessions[video_id]['files']['uploaded_video'] = file_path
        self.update_session_status(video_id, ProcessingStatus.UPLOADED, "Video uploaded successfully")
        
        return file_path
    
    def get_session_dir(self, video_id: str) -> str:
        """Возвращает путь к директории сессии"""
        return os.path.join(self.base_temp_dir, video_id)
    
    def save_analysis_result(self, video_id: str, analysis_data: Dict[str, Any]) -> str:
        """Сохраняет результаты анализа в JSON"""
        session_dir = self.get_session_dir(video_id)
        json_path = os.path.join(session_dir, "analysis_result.json")
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        self.sessions[video_id]['files']['analysis_json'] = json_path
        return json_path
    
    def get_analysis_result(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Загружает результаты анализа из JSON"""
        if video_id not in self.sessions:
            return None
        
        json_path = self.sessions[video_id]['files'].get('analysis_json')
        if not json_path or not os.path.exists(json_path):
            return None
        
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_preview_video(self, video_id: str, preview_path: str) -> str:
        """Сохраняет путь к превью видео"""
        self.sessions[video_id]['files']['preview_video'] = preview_path
        return preview_path
    
    def save_output_video(self, video_id: str, output_path: str) -> str:
        """Сохраняет путь к обработанному видео"""
        self.sessions[video_id]['files']['output_video'] = output_path
        return output_path
    
    def get_session_info(self, video_id: str) -> Optional[Dict]:
        """Возвращает информацию о сессии"""
        return self.sessions.get(video_id)
    
    def update_session_status(self, video_id: str, status: ProcessingStatus, 
                            message: str = "", progress: float = 0.0):
        """Обновляет статус сессии"""
        if video_id in self.sessions:
            self.sessions[video_id]['status'] = status
            self.sessions[video_id]['message'] = message
            self.sessions[video_id]['progress'] = progress
    
    def get_video_path(self, video_id: str) -> Optional[str]:
        """Возвращает путь к оригинальному видео"""
        return self.sessions.get(video_id, {}).get('files', {}).get('uploaded_video')
    
    def get_preview_path(self, video_id: str) -> Optional[str]:
        """Возвращает путь к превью"""
        return self.sessions.get(video_id, {}).get('files', {}).get('preview_video')
    
    def get_output_path(self, video_id: str) -> Optional[str]:
        """Возвращает путь к обработанному видео"""
        return self.sessions.get(video_id, {}).get('files', {}).get('output_video')
    
    def cleanup_session(self, video_id: str):
        """Удаляет все файлы сессии"""
        if video_id in self.sessions:
            session_dir = self.get_session_dir(video_id)
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
            del self.sessions[video_id]
    
    def _cleanup_old_files(self, hours_old: int = 24):
        """Очищает файлы старше указанного количества часов"""
        cutoff_time = datetime.now() - timedelta(hours=hours_old)
        
        for video_id in list(self.sessions.keys()):
            session = self.sessions[video_id]
            if session['created_at'] < cutoff_time:
                self.cleanup_session(video_id)

# Глобальный экземпляр хранилища
temp_storage = TempStorage()