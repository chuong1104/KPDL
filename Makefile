# Dùng: make <target>  ví dụ: make up
# docker compose up -d --build để khởi động lại toàn bộ hệ thống (bao gồm build lại image nếu có thay đổi trong Dockerfile)

.PHONY: build up down restart logs logs-minio status open-minio open-jupyter app clean-data help

# Build lại các image (để cài đặt các thư viện mới trong requirements.txt cho Jupyter)
build:
	docker compose build

# Khởi động tất cả services (MinIO, Spark 2 workers, Jupyter)
up:
    docker compose up -d --build
    @echo ""
    @echo "🚀 Services started (2 workers):"
    @echo "  Jupyter Notebook : http://localhost:8888"
    @echo "  MinIO Console    : http://localhost:9001"
    @echo "  Spark Master UI  : http://localhost:8080"
    @echo "  Spark Worker 1   : http://localhost:8081"
    @echo "  Spark Worker 2   : http://localhost:8082"

# Dừng tất cả services (vẫn giữ lại data trong volumes)
down:
	docker compose down

# Khởi động lại tất cả
restart:
	docker compose restart

# Xem logs realtime của toàn bộ hệ thống
logs:
	docker compose logs -f

# Xem logs của riêng MinIO
logs-minio:
	docker compose logs -f minio

# Xem trạng thái các containers đang chạy
status:
	docker compose ps

# Mở MinIO Console trên trình duyệt (dành cho Windows)
open-minio:
	start http://localhost:9001

# Mở Jupyter trên trình duyệt (dành cho Windows)
open-jupyter:
	start http://localhost:8888

# Chạy Streamlit demo app (nếu bạn vẫn muốn chạy app ở máy local)
app:
	streamlit run app/app.py

# XÓA TOÀN BỘ DATA VÀ CONTAINER (Cẩn thận!)
clean-data:
	@echo "CẢNH BÁO: Đang xóa toàn bộ container và data trong volumes..."
	docker compose down -v

# Hiển thị danh sách lệnh
help:
	@echo "Các lệnh có sẵn:"
	@echo "  make build       - Build lại Docker images (khi có thư viện mới)"
	@echo "  make up          - Khởi động MinIO, Spark, Jupyter"
	@echo "  make down        - Dừng tất cả services"
	@echo "  make restart     - Khởi động lại tất cả"
	@echo "  make logs        - Xem logs realtime"
	@echo "  make status      - Xem trạng thái containers"
	@echo "  make open-jupyter- Mở giao diện Jupyter Notebook"
	@echo "  make open-minio  - Mở giao diện MinIO Console"
	@echo "  make clean-data  - XÓA TOÀN BỘ DATA (nguy hiểm!)"