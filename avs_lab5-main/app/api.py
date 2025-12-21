from flask import Flask, request, jsonify
import os
import numpy as np
from PIL import Image
import io
import uuid

from app.ml_utils import embed_image
from app.db_utils import VectorDB, S3Storage

app = Flask(__name__)

# Инициализация подключений
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cats")
db = VectorDB(db_url)

s3 = S3Storage(
    endpoint=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
    access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
    secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
    bucket=os.getenv("S3_BUCKET", "cats")
)

@app.route("/similar", methods=["POST"])
def similar():
    """Ищет похожих котиков по загруженному изображению"""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    try:
        # Читаем изображение
        img = Image.open(file.stream)
        
        # Получаем эмбеддинг
        embedding = embed_image(img)
        
        # Ищем похожих в БД
        similar_results = db.find_similar(embedding, limit=5)
        
        # Формируем ответ
        results = []
        for img_id, distance in similar_results:
            results.append({
                "id": img_id,
                "distance": float(distance),
                "url": f"{os.getenv('S3_ENDPOINT')}/{os.getenv('S3_BUCKET')}/cat_{img_id}.jpg"
            })
        
        return jsonify({"results": results})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload", methods=["POST"])
def upload():
    """Загружает изображение в систему"""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    try:
        # Генерируем уникальный ID
        img_id = str(uuid.uuid4())
        
        # Загружаем в S3
        s3_url = s3.upload_image(file.stream, f"cat_{img_id}.jpg")
        
        # Получаем эмбеддинг
        file.stream.seek(0)  # Возвращаемся к началу файла
        img = Image.open(file.stream)
        embedding = embed_image(img)
        
        # Сохраняем в БД
        db.insert_image(embedding, img_id)
        
        return jsonify({
            "id": img_id,
            "url": s3_url,
            "message": "Image uploaded successfully"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stats", methods=["GET"])
def stats():
    """Статистика по базе данных"""
    try:
        db.connect()
        cur = db.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM embeddings")
        count = cur.fetchone()[0]
        cur.close()
        
        return jsonify({
            "total_images": count,
            "database": "PostgreSQL + pgvector",
            "storage": "S3 (MinIO)"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)