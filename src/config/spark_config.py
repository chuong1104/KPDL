import os
from pyspark.sql import SparkSession
from dotenv import load_dotenv

load_dotenv()  # Đọc .env file

def create_spark_session(app_name: str = 'ElectronicsRecommendation') -> SparkSession:
    """
    Tạo SparkSession với config tối ưu cho local development + MinIO.
    Gọi hàm này 1 lần ở đầu mỗi notebook.
    """
    # Lấy và dọn dẹp endpoint (xóa http:// hoặc https:// nếu có để tránh lặp)
    raw_endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    clean_endpoint = raw_endpoint.replace('http://', '').replace('https://', '')
    
    # Xác định giao thức (http hoặc https)
    is_secure = str(os.getenv('MINIO_SECURE', 'false')).lower() == 'true'
    protocol = 'https://' if is_secure else 'http://'
    spark_s3a_endpoint = f'{protocol}{clean_endpoint}'

    minio_user     = os.getenv('MINIO_ROOT_USER', 'admin')
    minio_password = os.getenv('MINIO_ROOT_PASSWORD', 'password123')

    spark = (
        SparkSession.builder
        .appName(app_name)
        .master(os.getenv('SPARK_MASTER', 'local[*]'))

        # ── Memory config ────────────────────────────────────
        .config('spark.driver.memory',          os.getenv('SPARK_DRIVER_MEMORY', '4g'))
        .config('spark.executor.memory',        os.getenv('SPARK_EXECUTOR_MEMORY', '4g'))
        .config('spark.driver.maxResultSize',   '1g')

        # ── Shuffle optimization ─────────────────────────────
        .config('spark.sql.shuffle.partitions',              os.getenv('SPARK_SHUFFLE_PARTITIONS', '8'))
        .config('spark.default.parallelism',                 '8')
        .config('spark.sql.adaptive.enabled',                'true')
        .config('spark.sql.adaptive.coalescePartitions.enabled', 'true')

        # ── Serializer ───────────────────────────────────────
        .config('spark.serializer', 'org.apache.spark.serializer.KryoSerializer')

        # ── MinIO / S3 connector (hadoop-aws) ────────────────
        .config('spark.jars.packages',
                'org.apache.hadoop:hadoop-aws:3.3.4,'
                'com.amazonaws:aws-java-sdk-bundle:1.12.262')
        .config('spark.hadoop.fs.s3a.endpoint',         spark_s3a_endpoint)
        .config('spark.hadoop.fs.s3a.access.key',       minio_user)
        .config('spark.hadoop.fs.s3a.secret.key',       minio_password)
        .config('spark.hadoop.fs.s3a.path.style.access', 'true')  # QUAN TRỌNG với MinIO
        .config('spark.hadoop.fs.s3a.impl',
                'org.apache.hadoop.fs.s3a.S3AFileSystem')
        .config('spark.hadoop.fs.s3a.connection.ssl.enabled', str(is_secure).lower())

        # ── Network timeout (tránh lỗi khi machine busy) ─────
        .config('spark.network.timeout', '800s')
        .config('spark.executor.heartbeatInterval', '60s')

        .getOrCreate()
    )

    spark.sparkContext.setLogLevel('WARN')  # Ẩn INFO logs spam
    print(f'SparkSession created: {app_name}')
    print(f'MinIO endpoint: {spark_s3a_endpoint}')
    return spark


# Path helpers — dùng thay vì hardcode bucket names
def bronze_path(sub: str = '') -> str:
    bucket = os.getenv('BRONZE_BUCKET', 'electronics-bronze')
    return f's3a://{bucket}/{sub}' if sub else f's3a://{bucket}'

def silver_path(sub: str = '') -> str:
    bucket = os.getenv('SILVER_BUCKET', 'electronics-silver')
    return f's3a://{bucket}/{sub}' if sub else f's3a://{bucket}'

def gold_path(sub: str = '') -> str:
    bucket = os.getenv('GOLD_BUCKET', 'electronics-gold')
    return f's3a://{bucket}/{sub}' if sub else f's3a://{bucket}'