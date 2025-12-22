# scripts/download_cats.py
import requests
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "cat_images"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Используем альтернативный API для получения фото котиков
API_URLS = [
    "https://api.thecatapi.com/v1/images/search",
    "https://placekitten.com/400/400",  # Простой сервис, возвращающий изображение по размеру
]

def download_cats(num_images=10):
    """Скачивает случайные фото котиков из публичных API"""
    downloaded = 0
    
    for i in range(num_images):
        try:
            # Пробуем первый API
            response = requests.get(API_URLS[0])
            
            if response.status_code == 200:
                data = response.json()
                image_url = data[0]['url']
            else:
                # Если первый API не сработал, используем второй
                image_url = f"{API_URLS[1]}?random={i}"
            
            # Скачиваем изображение
            img_response = requests.get(image_url, stream=True)
            
            if img_response.status_code == 200:
                # Сохраняем изображение
                file_path = DATA_DIR / f"real_cat_{i+1}.jpg"
                with open(file_path, 'wb') as f:
                    for chunk in img_response.iter_content(1024):
                        f.write(chunk)
                
                print(f"Скачан котик {i+1}: {file_path.name}")
                downloaded += 1
            else:
                print(f"Не удалось скачать изображение {i+1}")
                
        except Exception as e:
            print(f"Ошибка при скачивании изображения {i+1}: {e}")
            continue
    
    print(f"\nВсего скачано: {downloaded} фотографий котиков")
    return
