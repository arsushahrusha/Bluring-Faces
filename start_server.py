# start_server.py
import os
import sys
import uvicorn
# Добавляем backend в путь для импортов
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))


if __name__ == "__main__":
    print("🚀 Starting Video Face Blurring Server...")
    print("📁 Static files: ./static")
    print("🌐 Server: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔄 Auto-reload: Enabled")
    
    # Используем import string для включения reload
    uvicorn.run(
        "backend.main:app",  # Импорт как строка
        host="localhost",
        port=8000,
        reload=True,  # Теперь будет работать
        log_level="info"
    )