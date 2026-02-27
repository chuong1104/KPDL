# src/config/minio_config.py
import os
from minio import Minio
from dotenv import load_dotenv

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
