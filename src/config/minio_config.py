# src/config/minio_config.py
import os
from minio import Minio
from dotenv import load_dotenv
import re

load_dotenv()

def get_minio_client() -> Minio:
    """
    Tạo MinIO client để upload/download files, tạo buckets.
    Dùng khi cần thao tác file trực tiếp (không qua Spark).
    """
    # Lấy endpoint từ biến môi trường
    raw_endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    
    # Dọn dẹp: Loại bỏ 'http://' hoặc 'https://' nếu có
    clean_endpoint = raw_endpoint.replace('http://', '').replace('https://', '')
    
    # Ép kiểu secure thành boolean
    is_secure = str(os.getenv('MINIO_SECURE', 'false')).lower() == 'true'

    # ── FIX: Tự động detect môi trường ──────────────────────────
    # Nếu chạy từ local (không phải trong Docker container),
    # thay "minio" → "localhost"
    def _is_running_in_docker() -> bool:
        """Trả về True nếu đang chạy bên trong Docker container."""
        return (
            os.path.exists('/.dockerenv')
            or os.environ.get('JUPYTER_IN_DOCKER', '') == 'true'
        )

    if not _is_running_in_docker():
        # Thay toàn bộ hostname Docker bằng localhost
        clean_endpoint = re.sub(
            r'^[a-zA-Z_-]+:(\d+)$',   # pattern: "minio:9000"
            lambda m: f"localhost:{m.group(1)}",
            clean_endpoint
        )

    return Minio(
        endpoint   = clean_endpoint,
        access_key = os.getenv('MINIO_ROOT_USER', 'admin'),
        secret_key = os.getenv('MINIO_ROOT_PASSWORD', 'password123'),
        secure     = is_secure
    )

def ensure_buckets_exist():
    """Tạo 3 buckets nếu chưa tồn tại. Safe to call nhiều lần."""
    client = get_minio_client()
    for bucket in ['electronics-bronze', 'electronics-silver', 'electronics-gold']:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            print(f'Created bucket: {bucket}')
        else:
            print(f'Bucket exists: {bucket}')
