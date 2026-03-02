# BIG DATA PIPELINE — HYBRID RECOMMENDER SYSTEM

> **Tài liệu kỹ thuật toàn diện — Từ MapReduce Ingestion đến Delivery**
>
> Amazon Electronics · ~43.9M Reviews · Apache Spark + MinIO + Docker + Streamlit

| Phase 1 ✅ | Phase 2 ⏳ | Phase 3 ⏳ | Phase 4 ⏳ |
|---|---|---|---|
| MapReduce Ingestion | Feature Engineering | Modelling & Ablation | Dashboard & Report |

---

## 0. Môi trường & Điều kiện tiên quyết

Môi trường đã được setup thành công. Tài liệu này định nghĩa toàn bộ công việc theo thứ tự thực thi, bắt đầu từ bước MapReduce Ingestion cho đến khi hoàn thiện sản phẩm.

| Thành phần | Đặc tả kỹ thuật |
|---|---|
| **Cluster** | Docker Compose — 1 spark-master + 2 spark-workers + 1 jupyter + 1 minio + 1 minio-init · 6 containers |
| **Compute Engine** | Apache Spark 3.5.1 (PySpark 3.5.0) · driverMemory=2g · executorMemory=2g · 2 workers × 3 cores = 6 slots |
| **Object Storage** | MinIO S3-compatible · buckets: electronics-bronze / electronics-silver / electronics-gold · port 9000/9001 |
| **Data Volume** | Reviews: ~43.9M rows · Metadata: ~1.61M items · Nguồn: HuggingFace streaming API |
| **Target Size** | Bronze: Parquet chunks (Snappy) · Silver: Parquet (zstd) · Gold: < 500 MB |
| **Notebook Server** | Jupyter Lab (custom image: jupyter/pyspark-notebook + requirements.txt) · port 8888 |

---

## 1. Pipeline tổng quan — Kiến trúc Medallion + Hybrid 3 tầng

Kiến trúc tổng thể kết hợp mô hình Medallion Architecture (Bronze → Silver → Gold) với Hybrid 3-Tier Recommendation Pipeline. Mỗi lớp có vai trò rõ ràng, độc lập có thể kiểm thử, và kết nối với nhau thông qua MinIO làm lớp lưu trữ trung gian.

```
📥 NGUỒN DỮ LIỆU
   McAuley-Lab/Amazon-Reviews-2023 (HuggingFace Hub)
   raw_review_Electronics (~43.9M) + raw_meta_Electronics (~1.61M)

        ▼ BƯỚC 1: HuggingFace Streaming → Pandas Pre-Clean → PyArrow → MinIO ▼

🔴 BRONZE LAYER — MinIO / electronics-bronze bucket
   Flat Parquet chunks (~300K records/chunk, Snappy compression)
   reviews_chunks/chunk_NNNN.parquet + metadata_chunks/chunk_NNNN.parquet

        ▼ BƯỚC 2: Spark MapReduce — Filter + Transform + Dedup ▼

⚪ SILVER LAYER — MinIO / electronics-silver bucket
   Reviews: partitioned by (review_year, review_month), zstd compression
   Metadata: 4 partitions, price parsed, zstd compression

        ▼ BƯỚC 3: Feature Engineering — 3 luồng song song (Spark Jobs) ▼

┌─────────────────────┬─────────────────────┬─────────────────────┐
│ 🟡 GOLD — T1: ALS   │ 🟡 GOLD — T2: RQS   │ 🟡 GOLD — T3: KB    │
│    Matrix            │    Features          │    Catalog           │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ user_item_matrix     │ rqs_features         │ product_catalog      │
│ userId × productId   │ helpful_vote ·       │ price · store ·      │
│   × rating           │ verified_purchase    │ rating_number        │
│ Parquet · partitioned│ temporal_decay ·     │ sub-categories       │
│   by userId          │ rating_variance      │                      │
└─────────────────────┴─────────────────────┴─────────────────────┘

        ▼ BƯỚC 4: Hybrid 3-Tier Inference Engine ▼

┌─────────────────────┬─────────────────────┬─────────────────────┐
│ TIER 1 — ALS (MLlib)│ TIER 3 — KB Filter  │ TIER 2 — RQS Re-Rank│
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Collaborative       │ Hard constraint rules│ Review Quality Score │
│ Filtering           │ K-01: Price          │ re-rank candidates   │
│ Top-200 candidates  │ K-02: Review Count   │ Weighted multi-signal│
│ rank=50 · iter=20   │ K-03: Brand Tier     │ scoring → Top-10     │
│ λ=0.01              │ 200 → ~45 candidates │                      │
└─────────────────────┴─────────────────────┴─────────────────────┘

        ▼ Final Top-10 Recommendations per User ▼

📊 ABLATION STUDY — 4 Cấu hình
   Config A (Baseline) · Config B (T1 only)
   Config C (T1+T3) · Config D (T1+T2+T3)

        ▼ BƯỚC 5: Evaluation + Packaging ▼

🖥️ DELIVERY — Streamlit Dashboard + Academic Report
   Interactive demo · Ablation comparison charts
   Báo cáo cuối kỳ · Presentation deck
```

---

## 2. Phase 1 — Bronze + Silver Ingestion (✅ HOÀN THÀNH)

> **Notebook:** `02_stream_to_silver.ipynb` — thực hiện cả Bronze ingestion lẫn Silver MapReduce trong cùng 1 notebook.

### 2.1. Chiến lược Ingestion: HuggingFace Streaming → PyArrow → MinIO

Thay vì download file JSONL.GZ rồi dùng `spark.read.json()`, pipeline sử dụng HuggingFace streaming API để stream trực tiếp từ Hub, pre-clean bằng Pandas, rồi ghi thẳng vào MinIO qua PyArrow — loại bỏ hoàn toàn overhead Spark job scheduling cho bước download.

> **Quy trình Bronze Ingestion:**
>
> 1. `datasets.load_dataset()` với `streaming=True, split="full"` — stream records từ HuggingFace
> 2. `_pandas_pre_clean_reviews()` / `_pandas_pre_clean_meta()` — Pandas pre-clean: dropna keys, type casting, list→string join (`" | "` separator)
> 3. `_write_chunk_pyarrow()` — PyArrow Table → Parquet buffer → MinIO `put_object()` trực tiếp
> 4. Mỗi chunk ~300,000 records (~64 MB, Snappy compression)
>
> **Ưu điểm:** Throughput ổn định, không bị bottleneck bởi Spark job scheduling overhead (tiết kiệm ~5-10s/chunk).

### 2.2. Bronze Schema thực tế

**Review Schema (8 fields):**

| Field | Type | Nullable | Vai trò |
|---|---|---|---|
| `rating` | FloatType | Yes | T1 ALS + T2 RQS |
| `title` | StringType | Yes | T2 NLP (TF-IDF, ABSA) |
| `text` | StringType | Yes | T2 NLP pipeline |
| `parent_asin` | StringType | No | Primary join key |
| `user_id` | StringType | No | T1 user latent vector |
| `timestamp` | LongType | Yes | T2 temporal_decay |
| `helpful_vote` | IntegerType | Yes | T2 Helpful_Ratio |
| `verified_purchase` | BooleanType | Yes | T2 Verified_Rate |

> **Lưu ý:** Không lấy `asin` (dùng `parent_asin` gộp variants), `images` (94.5% trống).

**Metadata Schema (11 fields):**

| Field | Type | Nullable | Vai trò |
|---|---|---|---|
| `main_category` | StringType | Yes | Category filter |
| `title` | StringType | Yes | T3 hiển thị + TF-IDF |
| `average_rating` | FloatType | Yes | T2 baseline |
| `rating_number` | IntegerType | Yes | T3 rule K-02 |
| `features` | StringType (joined " \| ") | Yes | T2 NLP |
| `description` | StringType (joined " \| ") | Yes | T2 NLP |
| `price` | StringType | Yes | T3 rule K-01 |
| `store` | StringType | Yes | T3 rule K-03 |
| `categories` | StringType (joined " \| ") | Yes | T3 scope |
| `parent_asin` | StringType | No | Primary join key |
| `bought_together` | StringType (joined " \| ") | Yes | Co-purchase graph |

> **Lưu ý:** List fields được join thành string bằng `" | "` tại pre-clean. Không lấy `images`, `videos`, `details`, `subtitle`, `author`.

### 2.3. Silver MapReduce — Bronze Chunks → Silver Parquet

#### Reviews MapReduce (`mapreduce_reviews_to_silver()`)

> **INPUT SPLIT:** Spark đọc tất cả `reviews_chunks/*.parquet` song song, cân bằng partitions theo cluster capacity (2 workers × 3 cores = 6 slots).
>
> **MAP Phase:**
> - Filter: `parent_asin`, `user_id`, `timestamp` NOT NULL, `rating` ∈ [1.0, 5.0]
> - Transform: `timestamp/1000` → `review_ts` (TimestampType), extract `review_year` (ShortType) / `review_month` (byte)
> - Text: `lower(trim(title))` → `title_clean`, `lower(trim(text))` → `text_clean`, tính `text_word_count`, `has_text`
> - Filter: `review_year` ∈ [1996, 2024]
>
> **REDUCE Phase:**
> - `dropDuplicates(['parent_asin', 'user_id', 'review_ts'])` — global dedup
> - `repartition(num_output_files, 'review_year', 'review_month')` — shuffle by time
> - `sortWithinPartitions('review_year', 'review_month', 'parent_asin')`
> - Write: `partitionBy('review_year', 'review_month')`, compression=zstd
>
> **Output:** `s3a://electronics-silver/reviews/review_year=YYYY/review_month=MM/*.parquet`

#### Metadata MapReduce (`mapreduce_metadata_to_silver()`)

> **MAP Phase:**
> - Filter: `parent_asin` NOT NULL, `parent_asin` != ''
> - Transform: Parse `price` string → `price_numeric` (Double) via regex `\$?([\d,]+\.?\d*)`
> - Coalesce null text fields → empty string
> - Select: `parent_asin`, `main_category`, `title`, `average_rating`, `rating_number`, `price_numeric`, `price_raw`, `store`, `features`, `description`, `categories`, `bought_together`
>
> **REDUCE Phase:**
> - `dropDuplicates(['parent_asin'])` — dedup on primary key
> - `repartition(4, 'main_category')`
> - `sortWithinPartitions('main_category', 'parent_asin')`
> - Write: compression=zstd
>
> **Output:** `s3a://electronics-silver/metadata/*.parquet`

### 2.4. Verification & Cleanup

**Cell 11 — Verification (single Spark action per dataset):**
- Reviews: row count, rating range/avg, null checks trên 4 fields, year 2023 count, distinct years, schema print, year distribution
- File analysis: count parquet files, min/max/avg size, total GB (qua MinIO client)
- Metadata: row count, price coverage %, price range/avg

**Cell 12 — Optional Bronze cleanup:** Xóa Bronze chunks sau khi Silver đã verify OK để giải phóng disk.

### 2.5. Công nghệ DE áp dụng trong Phase 1

| Công nghệ | Vai trò | Lý do chọn |
|---|---|---|
| HuggingFace Datasets (streaming) | Data Source API | Stream trực tiếp, không cần download toàn file |
| PyArrow + Pandas | Bronze Writer | Ghi Parquet chunks trực tiếp vào MinIO, nhẹ hơn Spark |
| Apache Spark | MapReduce Engine | Distributed processing cho Bronze→Silver: filter, transform, dedup |
| MinIO (S3A connector) | Data Lake Storage | S3-compatible, Docker-native, Bronze/Silver/Gold isolation |
| Parquet (Snappy/zstd) | Storage Format | Bronze=Snappy (PyArrow), Silver=zstd (Spark) · columnar · predicate pushdown |

> **✅ Definition of Done — Phase 1 — ĐÃ HOÀN THÀNH**
>
> - [x] Bronze `reviews_chunks/` chứa Parquet chunks (~300K records/chunk, Snappy)
> - [x] Bronze `metadata_chunks/` chứa Parquet chunks metadata
> - [x] Silver `reviews/` partitioned by `(review_year, review_month)`, zstd
> - [x] Silver `metadata/` với `price_numeric` parsed, 4 partitions, zstd
> - [x] Dedup reviews trên `(parent_asin, user_id, review_ts)`
> - [x] Dedup metadata trên `parent_asin`
> - [x] Verification PASS: row count, null checks, rating range, year distribution
> - [x] EDA notebook (`00-source-analyst.ipynb`) hoàn chỉnh

---

## 3. Phase 2 — Feature Engineering (Silver → Gold Layer) ⏳

Phase 2 là phase kỹ thuật nặng nhất của dự án. Chất lượng Gold layer quyết định trực tiếp chất lượng của cả 3 tầng trong hệ thống Hybrid. Mỗi Spark job được thiết kế độc lập và có thể re-run mà không ảnh hưởng đến job khác.

### 3.1. NLP Processing — Notebook `04_silver_nlp.ipynb` ⏳

| Task | Mô tả | Module |
|---|---|---|
| ABSA | Aspect-Based Sentiment Analysis trên review text | `src/nlp/absa.py` + `config/absa_seeds.yaml` |
| TF-IDF | TF-IDF vectorization cho text similarity | `src/nlp/tfidf.py` |
| Text Pipeline | NLP preprocessing: tokenize, stopword, lemma | `src/nlp/text_pipeline.py` |

### 3.2. Gold Layer — 3 Luồng Feature Engineering Song Song

| Gold T1 — ALS Matrix | Gold T2 — RQS Features | Gold T3 — KB Catalog |
|---|---|---|
| **Notebook:** `05_gold_als.ipynb` | **Module:** `src/nlp/` + `src/evaluation/metrics.py` | **Module:** `src/preprocessing/transformer.py` + `quality.py` |
| 1. Load Silver reviews | 1. `helpful_score = log(helpful+1)` | 1. Join metadata × Silver |
| 2. StringIndexer: userId → intId | 2. `verified_weight`: 1.3 vs 1.0 | 2. Price imputation, brand tier |
| 3. StringIndexer: parent_asin → itemId | 3. `temporal_decay = exp(-λ·days)` | 3. Define K-01/K-02/K-03 rules |
| 4. Output: (userIdx, itemIdx, rating) | 4. `rating_variance` per item | 4. Save → `gold/kb_catalog/` |
| 5. Save → `gold/als_matrix/` | 5. Save → `gold/rqs_features/` | |

### 3.3. Công nghệ DE áp dụng trong Phase 2

| Công nghệ / Kỹ thuật | Ứng dụng cụ thể |
|---|---|
| Spark DataFrame API | ETL: filter, groupBy, agg, join — lazy evaluation + catalyst optimizer |
| Spark ML StringIndexer | Encode userId/parent_asin → integer index cho ALS |
| Window Functions | Tính rating_variance, temporal ranking per user |
| Broadcast Join | Join metadata (nhỏ) với reviews (lớn), tránh shuffle join |
| NLTK | NLP text processing: tokenize, stopword removal |
| Parquet Partitioning | predicate pushdown khi filter theo category |

> **✅ Definition of Done — Phase 2**
>
> - [ ] NLP pipeline: ABSA + TF-IDF trên review text (`04_silver_nlp.ipynb`)
> - [ ] Gold `als_matrix`: userIdx và itemIdx không có null
> - [ ] Gold `rqs_features`: temporal_decay values trong khoảng (0,1]
> - [ ] Gold `kb_catalog`: price imputed, brand tier classified
> - [ ] Tất cả 3 Gold jobs chạy độc lập thành công

---

## 4. Phase 3 — Hybrid 3 tầng + Ablation Study ⏳

### 4.1. Module T1 — Collaborative Filtering (ALS)

ALS (Alternating Least Squares) — Matrix Factorization cho explicit feedback. Spark MLlib ALS native distributed training.

| Task | Mô tả | Notebook |
|---|---|---|
| Load Gold als_matrix | DataFrame (userIdx, itemIdx, rating) | `05_gold_als.ipynb` |
| Train ALS | rank=50, maxIter=20, regParam=0.01 | `05_gold_als.ipynb` |
| Generate Top-200 | `model.recommendForAllUsers(200)` | `05_gold_als.ipynb` |
| LSH Similarity | Product similarity clusters via MinHash | `06_gold_lsh.ipynb` |
| PageRank | Authority scores trên co-purchase graph | `07_gold_pagerank.ipynb` |

### 4.2. Module T2 — Review Quality Score (RQS)

> **Công thức RQS**
>
> ```
> RQS(i) = w1 × helpful_score(i) + w2 × verified_weight(i)
>        + w3 × temporal_decay(i) + w4 × (1 - rating_variance(i))
> ```
>
> w1=0.3, w2=0.25, w3=0.25, w4=0.2 (tunable hyperparameters)

### 4.3. Module T3 — Knowledge-Based Filter

| Rule ID | Tên Rule | Điều kiện lọc |
|---|---|---|
| **K-01** | Price Budget Filter | price ≤ user_budget hoặc price ≤ category_median × 1.5 |
| **K-02** | Min Review Count | rating_number ≥ threshold (configurable) |
| **K-03** | Brand Tier Match | brand_tier match user history |

### 4.4. Ablation Study — 4 Cấu hình

| Config | Thành phần | Hypothesis |
|---|---|---|
| **A** | Baseline (Popularity) | Baseline performance |
| **B** | T1 (ALS only) | CF improves over popularity |
| **C** | T1 + T3 (ALS + KB Filter) | Hard rules improve precision |
| **D** | T1 + T2 + T3 (Full Hybrid) | Combined approach is best |

**Notebook:** `08_evaluation.ipynb`

> **✅ Definition of Done — Phase 3**
>
> - [ ] ALS model converges: RMSE trên test set
> - [ ] Top-200 ALS recommendations generated
> - [ ] RQS pipeline không có NaN/Infinity
> - [ ] KB rules filter rate logged
> - [ ] 4 ablation configs metrics computed (NDCG@10, Precision@10, MAP)

---

## 5. Phase 4 — Delivery: Dashboard + Academic Report ⏳

### 5.1. Streamlit Dashboard

| File | Component |
|---|---|
| `app/app.py` | Entry point — `streamlit run app/app.py` hoặc `make app` |
| `app/components/recommender.py` | Recommendation widget — Top-10 |
| `app/components/sentiment_radar.py` | Sentiment radar chart (ABSA) |
| `app/components/trend_chart.py` | Temporal trend visualization |

### 5.2. Academic Report

Cấu trúc: Abstract → Introduction → Related Work → System Architecture → Dataset & DE → Methodology → Experiments (Ablation) → Analysis → Conclusion

> **✅ Definition of Done — Phase 4**
>
> - [ ] Streamlit dashboard chạy (`make app`)
> - [ ] Ablation chart 4 configs
> - [ ] Báo cáo cuối kỳ
> - [ ] README.md reproduce pipeline

---

## 6. Tổng hợp công nghệ Data Engineering

| Layer | Công nghệ | Phase | Vai trò |
|---|---|---|---|
| **Ingestion** | HuggingFace Datasets (streaming) | Phase 1 | Stream records trực tiếp từ Hub |
| | PyArrow + Pandas | Phase 1 | Pre-clean, ghi Parquet chunks → MinIO |
| | Spark MapReduce | Phase 1 | Bronze→Silver: MAP (filter+transform) + REDUCE (dedup+partition) |
| | MinIO S3A | All | Data lake · Bronze/Silver/Gold bucket isolation |
| | Parquet (Snappy/zstd) | Phase 1 | Bronze=Snappy, Silver=zstd · columnar · predicate pushdown |
| **ETL / DQ** | Spark DataFrame API | Phase 2 | Lazy evaluation · catalyst optimizer |
| | Window Functions | Phase 2 | Temporal aggregations, rating variance |
| | Broadcast Join | Phase 2 | Metadata (nhỏ) × reviews (lớn) |
| **ML / NLP** | Spark MLlib ALS | Phase 3 | Distributed Matrix Factorization |
| | NLTK / ABSA | Phase 2 | NLP text processing + aspect sentiment |
| | TF-IDF | Phase 2 | Text vectorization |
| | LSH (MinHash) | Phase 3 | Product similarity clusters |
| | PageRank | Phase 3 | Co-purchase graph authority |
| **Evaluation** | Custom metrics | Phase 3 | NDCG@10, Precision@10, MAP |
| | Ablation Framework | Phase 3 | 4-config comparison |
| **Delivery** | Streamlit | Phase 4 | Dashboard demo |
| | Docker Compose | All | 6 containers: Spark Master + 2 Workers + MinIO + Jupyter + MinIO-Init |

### 6.1. Cấu trúc mã nguồn

| Module | Trạng thái | Vai trò |
|---|---|---|
| `src/config/spark_config.py` | ✅ | SparkSession (2g mem, 6 slots, S3A, zstd, AQE) + path helpers |
| `src/config/minio_config.py` | ✅ | MinIO client (auto-detect Docker/local) + ensure_buckets_exist() |
| `src/ingestion/hf_streamer.py` | ⏳ | HuggingFace streaming (logic hiện inline trong NB-02) |
| `src/ingestion/bronze_writer.py` | ⏳ | Bronze writer (logic hiện inline trong NB-02) |
| `src/preprocessing/cleaner.py` | ⏳ | Dedup, null handling, type casting |
| `src/preprocessing/quality.py` | ⏳ | Data quality checks |
| `src/preprocessing/transformer.py` | ⏳ | Feature transformations cho Gold |
| `src/nlp/absa.py` | ⏳ | Aspect-Based Sentiment Analysis |
| `src/nlp/text_pipeline.py` | ⏳ | NLP preprocessing pipeline |
| `src/nlp/tfidf.py` | ⏳ | TF-IDF vectorization |
| `src/models/als_model.py` | ⏳ | ALS Collaborative Filtering |
| `src/models/lsh_model.py` | ⏳ | LSH MinHash similarity |
| `src/models/pagerank.py` | ⏳ | PageRank authority scoring |
| `src/evaluation/metrics.py` | ⏳ | NDCG@10, Precision@10, MAP, ablation |
| `config/pipeline_config.yaml` | ⏳ | Cấu hình pipeline chung |
| `config/absa_seeds.yaml` | ⏳ | Seed words cho ABSA |
| `app/app.py` | ⏳ | Streamlit entry point |
| `app/components/recommender.py` | ⏳ | Recommendation UI |
| `app/components/sentiment_radar.py` | ⏳ | Sentiment radar chart |
| `app/components/trend_chart.py` | ⏳ | Temporal trend chart |

> ✅ = Đã triển khai | ⏳ = Stub/chưa triển khai

---

## 7. Master Checklist

### Phase 1 — Bronze + Silver ✅

| # | Task | Status |
|---|---|---|
| 1.1 | Bronze review chunks (HF→PyArrow→MinIO) | ✅ |
| 1.2 | Bronze metadata chunks (HF→PyArrow→MinIO) | ✅ |
| 1.3 | Silver reviews (Spark MapReduce, partitioned year/month, zstd) | ✅ |
| 1.4 | Silver metadata (Spark MapReduce, price parsed, zstd) | ✅ |
| 1.5 | Verification PASS | ✅ |
| 1.6 | EDA notebook (`00-source-analyst.ipynb`) | ✅ |

### Phase 2 — Feature Engineering ⏳

| # | Task | Status |
|---|---|---|
| 2.1 | NLP: ABSA + TF-IDF (`04_silver_nlp.ipynb`) | ☐ TODO |
| 2.2 | Gold T1: ALS matrix | ☐ TODO |
| 2.3 | Gold T2: RQS signals | ☐ TODO |
| 2.4 | Gold T3: KB catalog | ☐ TODO |

### Phase 3 — Modelling + Ablation ⏳

| # | Task | Status |
|---|---|---|
| 3.1 | ALS training + Top-200 (`05_gold_als.ipynb`) | ☐ TODO |
| 3.2 | LSH similarity (`06_gold_lsh.ipynb`) | ☐ TODO |
| 3.3 | PageRank (`07_gold_pagerank.ipynb`) | ☐ TODO |
| 3.4 | RQS pipeline + re-rank | ☐ TODO |
| 3.5 | KB Filter K-01/K-02/K-03 | ☐ TODO |
| 3.6 | Ablation 4 configs (`08_evaluation.ipynb`) | ☐ TODO |

### Phase 4 — Delivery ⏳

| # | Task | Status |
|---|---|---|
| 4.1 | Streamlit dashboard | ☐ TODO |
| 4.2 | Academic report | ☐ TODO |
| 4.3 | Presentation + demo | ☐ TODO |
| 4.4 | Code cleanup + tests | ☐ TODO |

---

## 8. Quản lý rủi ro

| Rủi ro | Xác suất | Impact | Mitigation |
|---|---|---|---|
| OOM Spark khi process full Silver | Cao | Pipeline crash | AQE enabled, 2g executor, persist Silver Parquet |
| Null price > 50% metadata | **Đã xác nhận: 58.2%** | K-01 coverage thấp | Scope reduction top sub-categories |
| ALS không converge | Thấp | T1 baseline yếu | Tune rank/regParam |
| D ≤ C trong ablation | Trung bình | Yếu contribution | Phân tích sub-groups, tune thresholds |
| Docker OOM | Trung bình | Không demo được | Sequential jobs, Streamlit từ cached data |

---

*© Data Engineering Pipeline — Cập nhật theo implementation thực tế*
