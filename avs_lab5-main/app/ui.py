import gradio as gr
import requests
from PIL import Image
import io
import os
import numpy as np

API_URL = os.getenv("API_URL", "http://localhost:5000")
UI_PORT = int(os.getenv("UI_PORT", 7860))

def find_similar_cats(image):
    """Отправляет изображение на API и получает похожих котиков"""
    if image is None:
        return []
    
    try:
        # Конвертируем изображение в байты
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Отправляем на API
        files = {'file': ('image.png', img_byte_arr, 'image/png')}
        response = requests.post(f"{API_URL}/similar", files=files)
        
        if response.status_code == 200:
            results = response.json().get('results', [])
            
            # Для демо версии - возвращаем тестовые изображения
            # В реальном приложении здесь бы скачивались изображения из S3
            test_images = []
            for i in range(min(5, len(results))):
                # Создаем тестовое изображение
                img = Image.new('RGB', (224, 224), color=(i*50, 100, 150))
                test_images.append(img)
            
            return test_images
        else:
            return [Image.new('RGB', (224, 224), color='red')]
            
    except Exception as e:
        print(f"Error: {e}")
        return [Image.new('RGB', (224, 224), color='gray')]

# Создаем интерфейс
with gr.Blocks(title="Поиск похожих котиков 🐱", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🐱 Поиск похожих котиков")
    gr.Markdown("Загрузите фото котика, и мы найдем похожих!")
    
    with gr.Row():
        with gr.Column(scale=1):
            input_image = gr.Image(
                label="Загрузите фото котика", 
                type="pil",
                height=300
            )
            submit_btn = gr.Button("Найти похожих", variant="primary")
            gr.Markdown("### Или")
            upload_btn = gr.UploadButton(
                "Загрузить котика в базу",
                file_types=["image"]
            )
        
        with gr.Column(scale=2):
            output_gallery = gr.Gallery(
                label="Похожие котики",
                show_label=True,
                columns=3,
                height=400
            )
    
    # Обработчики
    submit_btn.click(
        fn=find_similar_cats,
        inputs=input_image,
        outputs=output_gallery
    )
    
    def upload_to_db(file):
        """Загружает изображение в базу данных"""
        if file is None:
            return "Пожалуйста, выберите файл"
        
        try:
            files = {'file': open(file.name, 'rb')}
            response = requests.post(f"{API_URL}/upload", files=files)
            
            if response.status_code == 200:
                return "Котик успешно добавлен в базу! 🎉"
            else:
                return f"Ошибка: {response.json().get('error', 'Unknown error')}"
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    upload_btn.upload(
        fn=upload_to_db,
        inputs=upload_btn,
        outputs=gr.Textbox(label="Результат загрузки")
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0", 
        server_port=UI_PORT,
        share=False
    )