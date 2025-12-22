import boto3
from botocore.client import Config
from PIL import Image
import io
from typing import List, Tuple, Optional, Union
import psycopg2
import numpy as np

class VectorDB:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None

    def connect(self):
        if self.conn is None:
            self.conn = psycopg2.connect(self.db_url)

    def init_table(self):
        """Создаёт таблицу и индекс для pgvector"""
        if self.conn is None:
            self.connect()
        cur = self.conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id SERIAL PRIMARY KEY,
                embedding vector(1280) NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        
        cur.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = 'idx_embedding'
              ) THEN
                CREATE INDEX idx_embedding ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
              END IF;
            END
            $$;
            """
        )
        self.conn.commit()
        cur.close()

    def insert_image(self, embedding: np.ndarray, img_id: str):
    """Сохраняет эмбеддинг в базу данных"""
    if self.conn is None:
        self.connect()
    cur = self.conn.cursor()
    
    # Конвертируем numpy array в список для PostgreSQL
    embedding_list = embedding.tolist()
    
    # Вставка данных
    cur.execute(
        "INSERT INTO embeddings (id, embedding) VALUES (%s, %s);",
        (img_id, embedding_list),  # PostgreSQL сам конвертирует список в vector
    )
    self.conn.commit()
    cur.close()

    def find_similar(self, query_embedding: np.ndarray, limit: int = 5) -> List[Tuple]:
        if self.conn is None:
            self.connect()
        cur = self.conn.cursor()
        emb_str = "[" + ",".join(map(str, query_embedding.tolist())) + "]"
        cur.execute(
            "SELECT id, embedding <-> %s as distance FROM embeddings ORDER BY distance LIMIT %s;",
            (emb_str, limit),
        )
        rows = cur.fetchall()
        cur.close()
        return rows

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


class S3Storage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4')
        )
        self.bucket = bucket
        self.endpoint = endpoint
        self.ensure_bucket_exists()

    def ensure_bucket_exists(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            print(f"Bucket {self.bucket} already exists")
        except Exception as e:
            print(f"Creating bucket {self.bucket}: {e}")
            self.s3_client.create_bucket(Bucket=self.bucket)
            print(f"Bucket {self.bucket} created")

    def upload_image(self, image_file, object_name: str) -> str:
        if isinstance(image_file, str):
            with open(image_file, 'rb') as f:
                self.s3_client.upload_fileobj(f, self.bucket, object_name)
        else:
            self.s3_client.upload_fileobj(image_file, self.bucket, object_name)
        
        return f"{self.endpoint}/{self.bucket}/{object_name}"

    def download_image(self, object_name: str) -> Image.Image:
        response = self.s3_client.get_object(Bucket=self.bucket, Key=object_name)
        image_data = response['Body'].read()
        return Image.open(io.BytesIO(image_data))

    def list_images(self, prefix: str = "") -> List[str]:
        response = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        contents = response.get('Contents', [])
        return [obj['Key'] for obj in contents]
