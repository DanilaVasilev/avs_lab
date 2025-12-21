#!/usr/bin/env python3
"""
Инициализация датасета: загружает изображения в PostgreSQL+pgvecto
"""
import os
import sys
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.ml_utils import embed_image
from app.db_utils import VectorDB

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/cats")
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "cat_images"))


def init_dataset():
    data_dir = Path(DATA_DIR)
    
    image_extensions = {'.jpg', '.jpeg', '.png'}
    image_files = sorted([
        f for f in data_dir.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ])
    
    if not image_files:
        return False
    
    db = VectorDB(DATABASE_URL)
    db.connect()
    db.init_table()
    
    for img_id, image_path in enumerate(tqdm(image_files, desc="Loading images", unit="img")):
        try:
            embedding = embed_image(str(image_path), device="cpu")
            db.insert_image(embedding, img_id)
        except Exception:
            pass
    
    db.close()
    return True


if __name__ == "__main__":
    success = init_dataset()
    sys.exit(0 if success else 1)
