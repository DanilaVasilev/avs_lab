import gradio as gr
import requests
import os
from PIL import Image
import io

API_URL = os.getenv("API_URL", "http://api:5000")
UI_PORT = int(os.getenv("UI_PORT", "7860"))

def find_similar_cats(image):
    if image is None:
        return []

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    files = {'file': ('query.jpg', img_byte_arr, 'image/jpeg')}
    
    try:
        response = requests.post(f"{API_URL}/similar", files=files)
        response.raise_for_status()
        data = response.json()
        
        result_images = []
        for item in data:
            s3_path = item['s3_path']
            dist = item['distance']
            
            # Загружаем саму картинку
            img_resp = requests.get(f"{API_URL}/image/{s3_path}")
            if img_resp.status_code == 200:
                pil_img = Image.open(io.BytesIO(img_resp.content))
                result_images.append((pil_img, f"Dist: {dist:.4f}"))
        
        return result_images
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def upload_cat(image):
    if image is None:
        return "No image provided"
        
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    files = {'file': ('upload.jpg', img_byte_arr, 'image/jpeg')}
    
    try:
        response = requests.post(f"{API_URL}/upload", files=files)
        return str(response.json())
    except Exception as e:
        return f"Error: {e}"

def get_stats():
    try:
        response = requests.get(f"{API_URL}/stats")
        return str(response.json())
    except Exception as e:
        return f"Error: {e}"

with gr.Blocks() as demo:
    gr.Markdown("# Cat Similarity Search")
    
    with gr.Tab("Search Similar"):
        with gr.Row():
            in_image = gr.Image(type="pil", label="Upload your cat")
            search_btn = gr.Button("Find Friends")
        
        gallery = gr.Gallery(label="Similar Cats").style(columns=5, height="auto")
        search_btn.click(fn=find_similar_cats, inputs=in_image, outputs=gallery)

    with gr.Tab("Upload to DB"):
        with gr.Row():
            upload_image_in = gr.Image(type="pil", label="New Cat")
            upload_btn = gr.Button("Add to Database")
        
        out_text = gr.Textbox(label="Status")
        upload_btn.click(fn=upload_cat, inputs=upload_image_in, outputs=out_text)
        
    with gr.Tab("Stats"):
        refresh_btn = gr.Button("Refresh Stats")
        stats_text = gr.Textbox()
        refresh_btn.click(fn=get_stats, inputs=None, outputs=stats_text)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=UI_PORT)
