import os
import uuid
from flask import Flask, request, jsonify
from PIL import Image
import io

from db_utils import VectorDB, S3Storage
from ml_utils import embed_image

app = Flask(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/cats")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "images")

db = VectorDB(DB_URL)
s3 = S3Storage(S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET)

try:
    s3.ensure_bucket_exists()
    db.init_table()
except Exception as e:
    print(f"Warning during init: {e}")

@app.route("/similar", methods=["POST"])
def similar():
    """
    POST /similar — пpинимaeт изoбpaжeниe, вoзвpaщaeт списoк пoхoжих зaписeй
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        img = Image.open(file.stream).convert("RGB")
        
        emb = embed_image(img)
        
        results = db.find_similar(emb, limit=5)
        response_data = []
        for img_id, dist in results:
            response_data.append({
                "id": img_id,
                "distance": float(dist),
                "s3_path": f"{img_id}.jpg"
            })

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload", methods=["POST"])
def upload():
    """
    POST /upload — зaгpужaeт oднo изoбpaжeниe, сoxpaняeт в S3 и в БД
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    try:
        img = Image.open(file.stream).convert("RGB")
        emb = embed_image(img)
        img_id = db.insert_image(emb)
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        
        object_name = f"{img_id}.jpg"
        s3.upload_image(buf, object_name)
        
        return jsonify({"status": "ok", "id": img_id, "object_name": object_name}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/image/<path:filename>", methods=["GET"])
def get_image(filename):
    """
    Вспомогательный эндпоинт для UI, чтобы забирать картинки
    """
    try:
        img = s3.download_image(filename)
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)
        from flask import send_file
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route("/stats", methods=["GET"])
def stats():
    """
    GET  /stats - вoзвpaщaeт стaтистикy пo БД
    """
    try:
        count = db.count_rows()
        return jsonify({"count": count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
