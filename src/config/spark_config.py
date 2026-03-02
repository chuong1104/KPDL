import os
import re
from pyspark.sql import SparkSession
from dotenv import load_dotenv

load_dotenv()


def create_spark_session(app_name: str = 'ElectronicsRecommendation') -> SparkSession:
    """
    Tạo SparkSession tối ưu cho 2 workers (6C/12T, 16GB RAM).
    Bronze KHÔNG persist — chỉ tồn tại trên RAM → ghi thẳng Silver.
    """
    raw_endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    clean_endpoint = raw_endpoint.replace('http://', '').replace('https://', '')

    def _is_running_in_docker() -> bool:
        return (
            os.path.exists('/.dockerenv')
            or os.environ.get('JUPYTER_IN_DOCKER', '') == 'true'
        )

    if not _is_running_in_docker():
        clean_endpoint = re.sub(
            r'^[a-zA-Z_-]+:(\d+)$',
            lambda m: f"localhost:{m.group(1)}",
            clean_endpoint
        )

    is_secure = str(os.getenv('MINIO_SECURE', 'false')).lower() == 'true'
    protocol = 'https://' if is_secure else 'http://'
    spark_s3a_endpoint = f'{protocol}{clean_endpoint}'

    minio_user = os.getenv('MINIO_ROOT_USER', 'admin')
    minio_password = os.getenv('MINIO_ROOT_PASSWORD', 'password123')

    spark = (
        SparkSession.builder
        .appName(app_name)
        .master(os.getenv('SPARK_MASTER', 'local[*]'))

        # ── Memory (tối ưu 16GB, 2 workers) ─────────────────
        .config('spark.driver.memory',          os.getenv('SPARK_DRIVER_MEMORY', '2g'))
        .config('spark.executor.memory',        os.getenv('SPARK_EXECUTOR_MEMORY', '2g'))
        .config('spark.driver.maxResultSize',   '512m')
        .config('spark.executor.cores',         '3')
        .config('spark.memory.fraction',        '0.6')
        .config('spark.memory.storageFraction',  '0.3')

        # ── Shuffle (2 workers × 3 cores = 6 slots) ─────────
        .config('spark.sql.shuffle.partitions',
                os.getenv('SPARK_SHUFFLE_PARTITIONS', '12'))
        .config('spark.default.parallelism',    '12')
        .config('spark.sql.adaptive.enabled',   'true')
        .config('spark.sql.adaptive.coalescePartitions.enabled', 'true')
        .config('spark.sql.adaptive.coalescePartitions.minPartitionNum', '4')
        .config('spark.sql.adaptive.advisoryPartitionSizeInBytes', '128m')

        # ── Parquet tối ưu ───────────────────────────────────
        .config('spark.sql.parquet.compression.codec',  'zstd')
        .config('spark.sql.parquet.mergeSchema',        'false')
        .config('spark.sql.parquet.filterPushdown',     'true')
        .config('spark.sql.files.maxPartitionBytes',    '128m')
        .config('spark.sql.files.openCostInBytes',      '4m')

        # ── Serializer ──────────────────────────────────────
        .config('spark.serializer',
                'org.apache.spark.serializer.KryoSerializer')

        # ── MinIO / S3A connector ────────────────────────────
        .config('spark.jars.packages',
                'org.apache.hadoop:hadoop-aws:3.3.4,'
                'com.amazonaws:aws-java-sdk-bundle:1.12.262')
        .config('spark.hadoop.fs.s3a.endpoint',          spark_s3a_endpoint)
        .config('spark.hadoop.fs.s3a.access.key',        minio_user)
        .config('spark.hadoop.fs.s3a.secret.key',        minio_password)
        .config('spark.hadoop.fs.s3a.path.style.access', 'true')
        .config('spark.hadoop.fs.s3a.impl',
                'org.apache.hadoop.fs.s3a.S3AFileSystem')
        .config('spark.hadoop.fs.s3a.connection.ssl.enabled',
                str(is_secure).lower())
        .config('spark.hadoop.fs.s3a.multipart.size',    '64m')
        .config('spark.hadoop.fs.s3a.fast.upload',       'true')
        .config('spark.hadoop.fs.s3a.fast.upload.buffer', 'bytebuffer')

        # ── Timeout ──────────────────────────────────────────
        .config('spark.network.timeout',             '800s')
        .config('spark.executor.heartbeatInterval',  '60s')

        .getOrCreate()
    )

    spark.sparkContext.setLogLevel('WARN')
    print(f'SparkSession created: {app_name}')
    print(f'MinIO endpoint: {spark_s3a_endpoint}')
    print(f'Workers: 2 × 3 cores | Driver: {os.getenv("SPARK_DRIVER_MEMORY", "2g")} '
          f'| Executor: {os.getenv("SPARK_EXECUTOR_MEMORY", "2g")}')
    return spark


# ── Path helpers ─────────────────────────────────────────────
def bronze_path(sub: str = '') -> str:
    bucket = os.getenv('BRONZE_BUCKET', 'electronics-bronze')
    return f's3a://{bucket}/{sub}' if sub else f's3a://{bucket}'

def silver_path(sub: str = '') -> str:
    bucket = os.getenv('SILVER_BUCKET', 'electronics-silver')
    return f's3a://{bucket}/{sub}' if sub else f's3a://{bucket}'

def gold_path(sub: str = '') -> str:
    bucket = os.getenv('GOLD_BUCKET', 'electronics-gold')
    return f's3a://{bucket}/{sub}' if sub else f's3a://{bucket}'