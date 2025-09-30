import cv2
import numpy as np
import json
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FaceBoundingBox:
    """Класс для представления ограничивающего прямоугольника лица"""
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0

class VideoProcessor:
    """Основной класс для обработки видео и размытия лиц с использованием dlib"""
    
    def __init__(self, use_cnn: bool = False):
        """
        Инициализация детектора лиц dlib
        
        Args:
            use_cnn: Использовать ли CNN модель (точнее но медленнее)
        """
        try:
            import dlib
            self.dlib = dlib
            self.detector = None
            self.cnn_detector = None
            
            if use_cnn:
                # Пытаемся загрузить CNN модель
                cnn_model_path = self._find_cnn_model()
                if cnn_model_path:
                    logger.info("Using dlib CNN face detector")
                    self.cnn_detector = dlib.cnn_face_detection_model_v1(cnn_model_path)
                else:
                    logger.warning("CNN model not found. Using HOG detector")
                    self.detector = dlib.get_frontal_face_detector()
            else:
                logger.info("Using dlib HOG face detector")
                self.detector = dlib.get_frontal_face_detector()
                
        except ImportError:
            raise ImportError("dlib not available. Please install: pip install dlib")
    
    def _find_cnn_model(self) -> Optional[str]:
        """Пытается найти CNN модель dlib"""
        possible_paths = [
            "mmod_human_face_detector.dat",
            "./mmod_human_face_detector.dat",
            "models/mmod_human_face_detector.dat",
            os.path.join(os.path.dirname(__file__), "mmod_human_face_detector.dat"),
            os.path.join(os.path.dirname(__file__), "models", "mmod_human_face_detector.dat")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found CNN model at: {path}")
                return path
        
        logger.warning("CNN model file 'mmod_human_face_detector.dat' not found.")
        return None
    
    def analyze_video(self, video_path: str, output_json_path: Optional[str] = None) -> Dict:
        """
        Анализирует видео и обнаруживает лица в кадрах с помощью dlib
        
        Args:
            video_path: Путь к исходному видео файлу
            output_json_path: Путь для сохранения результатов анализа (опционально)
            frame_skip: Анализировать каждый N-ый кадр (для ускорения)
            
        Returns:
            Словарь с результатами анализа
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        # Получаем информацию о видео
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"Analyzing video: {video_path}")
        logger.info(f"Resolution: {width}x{height}, FPS: {fps}, Duration: {duration:.2f}s")
        
        faces_by_frame = {}
        frame_number = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            faces = self.detect_faces(frame)
            if faces:
                faces_by_frame[str(frame_number)] = [
                    {'x': face.x, 'y': face.y, 'width': face.width, 
                     'height': face.height, 'confidence': face.confidence}
                    for face in faces
                ]
                
            if frame_number % 100 == 0:
                logger.info(f"Processed frame {frame_number}/{total_frames} - found {len(faces)} faces")
            
            frame_number += 1
        
        cap.release()
        
        # Создаем результат анализа
        analysis_result = {
            'video_info': {
                'file_path': video_path,
                'fps': fps,
                'total_frames': total_frames,
                'duration': duration,
                'width': width,
                'height': height
            },
            'faces_by_frame': faces_by_frame,
            'analysis_settings': {
                'total_analyzed_frames': len(faces_by_frame)
            }
        }
        
        # Сохраняем результаты в JSON если указан путь
        if output_json_path:
            os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False)
            logger.info(f"Analysis results saved to: {output_json_path}")
        
        logger.info(f"Analysis complete. Detected faces in {len(faces_by_frame)} frames")
        return analysis_result
    
    def detect_faces(self, frame: np.ndarray) -> List[FaceBoundingBox]:
        """
        Обнаруживает лица в одном кадре с помощью dlib
        
        Args:
            frame: Кадр видео в формате BGR
            
        Returns:
            Список ограничивающих прямоугольников лиц
        """
        # Конвертируем BGR в RGB (dlib работает с RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        faces = []
        height, width = frame.shape[:2]
        
        try:
            if self.cnn_detector:
                # Используем CNN детектор (более точный)
                dets = self.cnn_detector(rgb_frame, 0)
                
                for detection in dets:
                    rect = detection.rect
                    confidence = detection.confidence
                    
                    # Пропускаем лица с низкой уверенностью
                    if confidence < 0.5:
                        continue
                    
                    x = rect.left()
                    y = rect.top()
                    w = rect.width()
                    h = rect.height()
                    
                    # Добавляем margin вокруг лица
                    margin = 0.15
                    x = max(0, int(x - w * margin))
                    y = max(0, int(y - h * margin))
                    w = min(width - x, int(w * (1 + 2 * margin)))
                    h = min(height - y, int(h * (1 + 2 * margin)))
                    
                    faces.append(FaceBoundingBox(x, y, w, h, confidence))
                    
            elif self.detector:
                # Используем HOG детектор (быстрый)
                # Второй аргумент - увеличение изображения для поиска (1 = нет увеличения)
                dets = self.detector(rgb_frame, 1)
                
                for rect in dets:
                    x = rect.left()
                    y = rect.top()
                    w = rect.width()
                    h = rect.height()
                    
                    # Добавляем margin
                    margin = 0.2
                    x = max(0, int(x - w * margin))
                    y = max(0, int(y - h * margin))
                    w = min(width - x, int(w * (1 + 2 * margin)))
                    h = min(height - y, int(h * (1 + 2 * margin)))
                    
                    faces.append(FaceBoundingBox(x, y, w, h, 1.0))
                    
        except Exception as e:
            logger.error(f"Error in face detection: {e}")
        
        return faces
    
    def process_video(self, input_path: str, output_path: str, 
                     masks_data: Dict, blur_strength: int = 15,
                     progress_callback: Optional[callable] = None) -> bool:
        """
        Обрабатывает видео: применяет размытие к обнаруженным лицам
        
        Args:
            input_path: Путь к исходному видео
            output_path: Путь для сохранения обработанного видео
            masks_data: Словарь с масками для размытия {frame_number: [masks]}
            blur_strength: Сила размытия (радиус Gaussian blur)
            progress_callback: Функция для отслеживания прогресса
            
        Returns:
            True если обработка завершена успешно
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open input video: {input_path}")
        
        # Получаем параметры видео
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Создаем VideoWriter для выходного файла
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            cap.release()
            raise ValueError(f"Cannot create output video: {output_path}")
        
        logger.info(f"Processing video: {input_path} -> {output_path}")
        logger.info(f"Blur strength: {blur_strength}, Total frames: {total_frames}")
        
        frame_number = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Получаем маски для текущего кадра
            frame_masks = masks_data.get(str(frame_number), [])
            
            if frame_masks:
                # Преобразуем словари обратно в FaceBoundingBox объекты
                masks = [
                    FaceBoundingBox(
                        x=mask['x'], y=mask['y'], 
                        width=mask['width'], height=mask['height'],
                        confidence=mask.get('confidence', 1.0)
                    ) for mask in frame_masks
                ]
                # Применяем размытие
                frame = self.apply_blur_to_frame(frame, masks, blur_strength)
            
            # Записываем обработанный кадр
            out.write(frame)
            
            # Вызываем callback прогресса
            if progress_callback and frame_number % 10 == 0:
                progress = (frame_number + 1) / total_frames * 100
                progress_callback(progress)
            
            frame_number += 1
        
        cap.release()
        out.release()
        
        logger.info(f"Video processing complete: {output_path}")
        return True
    
    def apply_blur_to_frame(self, frame: np.ndarray, masks: List[FaceBoundingBox], 
                           blur_strength: int) -> np.ndarray:
        """
        Применяет размытие к областям с лицами в кадре
        
        Args:
            frame: Исходный кадр
            masks: Список масок для размытия
            blur_strength: Сила размытия
            
        Returns:
            Кадр с примененным размытием
        """
        if not masks:
            return frame
        
        # Создаем копию кадра для модификации
        result_frame = frame.copy()
        
        for mask in masks:
            # Убеждаемся, что координаты в пределах кадра
            x1 = max(0, mask.x)
            y1 = max(0, mask.y)
            x2 = min(frame.shape[1], mask.x + mask.width)
            y2 = min(frame.shape[0], mask.y + mask.height)
            
            # Извлекаем область интереса (ROI)
            roi = result_frame[y1:y2, x1:x2]
            
            if roi.size > 0:
                # Применяем Gaussian blur
                kernel_size = max(3, blur_strength * 2 + 1)
                blurred_roi = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)
                
                # Вставляем размытую область обратно
                result_frame[y1:y2, x1:x2] = blurred_roi
        
        return result_frame
    
    def generate_preview(self, input_path: str, output_path: str, 
                        masks_data: Dict, blur_strength: int = 15,
                        preview_duration: int = 10) -> bool:
        """
        Генерирует короткий предпросмотр обработанного видео
        
        Args:
            input_path: Путь к исходному видео
            output_path: Путь для сохранения превью
            masks_data: Словарь с масками
            blur_strength: Сила размытия
            preview_duration: Длительность превью в секундах
            
        Returns:
            True если успешно
        """
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Вычисляем количество кадров для превью
        preview_frames = min(total_frames, int(preview_duration * fps))
        
        # Уменьшаем разрешение для быстрого превью
        preview_width = min(640, width)
        preview_height = int(preview_width * height / width)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (preview_width, preview_height))
        
        logger.info(f"Generating preview: {preview_duration}s, {preview_frames} frames")
        
        for frame_num in range(preview_frames):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Получаем маски для текущего кадра
            frame_masks = masks_data.get(str(frame_num), [])
            
            if frame_masks:
                masks = [
                    FaceBoundingBox(
                        x=mask['x'], y=mask['y'], 
                        width=mask['width'], height=mask['height']
                    ) for mask in frame_masks
                ]
                frame = self.apply_blur_to_frame(frame, masks, blur_strength)
            
            # Изменяем размер для превью
            frame_preview = cv2.resize(frame, (preview_width, preview_height))
            out.write(frame_preview)
        
        cap.release()
        out.release()
        
        logger.info(f"Preview generated: {output_path}")
        return True