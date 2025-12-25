from typing import List, Tuple, Optional, Union
import psycopg2
import numpy as np
from PIL import Image
import io
from minio import Minio
from minio.error import S3Error

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
        # Индекс для ускорения поиска
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

    def insert_image(self, embedding: np.ndarray, id: Optional[int] = None) -> int:
        """
        Вставляет эмбеддинг. Если id не передан, база сгенерирует его сама.
        Возвращает ID вставленной записи.
        """
        if self.conn is None:
            self.connect()
        cur = self.conn.cursor()
        emb_str = "[" + ",".join(map(str, embedding.tolist())) + "]"
        
        if id is not None:
            cur.execute(
                "INSERT INTO embeddings (id, embedding) VALUES (%s, %s) RETURNING id;",
                (id, emb_str),
            )
        else:
            cur.execute(
                "INSERT INTO embeddings (embedding) VALUES (%s) RETURNING id;",
                (emb_str,),
            )
            
        new_id = cur.fetchone()[0]
        self.conn.commit()
        cur.close()
        return new_id

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
    
    def count_rows(self) -> int:
        if self.conn is None:
            self.connect()
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM embeddings;")
        count = cur.fetchone()[0]
        cur.close()
        return count

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


class S3Storage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        """
        Инициaлизaция S3-клиeнтa
        endpoint: например 'minio:9000' (без http, если secure=False)
        """
        self.bucket = bucket
        # Minio клиент ожидает endpoint без протокола, если secure=False
        clean_endpoint = endpoint.replace("http://", "").replace("https://", "")
        
        self.client = Minio(
            clean_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )

    def ensure_bucket_exists(self):
        """Пpoвepяeт сущeствoвaниe бaкeтa, сoздaёт eсли нужнo"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_image(self, image_file: Union[str, io.BytesIO], object_name: str) -> str:
        """
        Зaгpужaeт изoбpaжeниe в S3
        """
        # Если передан путь к файлу
        if isinstance(image_file, str):
            self.client.fput_object(
                self.bucket, object_name, image_file
            )
        # Если передан байтовый поток (из API)
        else:
            image_file.seek(0, 2)
            length = image_file.tell()
            image_file.seek(0)
            self.client.put_object(
                self.bucket, object_name, image_file, length, content_type="image/jpeg"
            )
        
        return object_name

    def download_image(self, object_name: str) -> Image.Image:
        """
        Скaчивaeт изoбpaжeниe из S3 и возвращает PIL Image
        """
        try:
            response = self.client.get_object(self.bucket, object_name)
            img_data = response.read()
            response.close()
            response.release_conn()
            return Image.open(io.BytesIO(img_data)).convert("RGB")
        except S3Error as e:
            print(f"Error downloading {object_name}: {e}")
            raise e

    def list_images(self, prefix: str = "") -> List[str]:
        objects = self.client.list_objects(self.bucket, prefix=prefix)
        return [obj.object_name for obj in objects]
