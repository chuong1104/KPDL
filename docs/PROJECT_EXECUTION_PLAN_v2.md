# KẾ HOẠCH THỰC THI DỰ ÁN
> *Tài liệu Lập kế hoạch & Checklist Chi tiết | v2.0 — Hybrid 3 Tầng*

---

## Tên đề tài

**Hệ thống Khuyến nghị Sản phẩm Điện tử Cá nhân hóa Kết hợp Lọc Tri thức Miền và Chấm điểm Chất lượng Đánh giá Người dùng trên Nền tảng Xử lý Phân tán Apache Spark với Bộ dữ liệu Amazon Electronics Reviews 2023 (43.9 triệu lượt đánh giá)**

---

| Thuộc tính | Giá trị |
|---|---|
| **Dự án** | Personalized Recommendation — Amazon Electronics |
| **Môn học** | CS246 — Mining Massive Datasets (Big Data) |
| **Phiên bản** | v2.1 — Cập nhật theo implementation thực tế |
| **Thời gian** | 15 tuần — Bắt đầu: 03/03/2026 |
| **Kiến trúc** | CF (ALS) → Knowledge-Based Filter (3 rules) → RQS Re-Ranker |
| **Infrastructure** | Docker Compose: Spark 3.5.1 (1 master + 2 workers × 3 cores) + MinIO + Jupyter Lab — 6 containers |
| **Trạng thái** | Phase 1 DONE — Bronze + Silver ingestion hoàn thành — Sẵn sàng Phase 2 |

---

## 1. Tổng quan Dự án

### 1.1. Mục tiêu hệ thống

Xây dựng hệ thống khuyến nghị Hybrid 3 tầng có khả năng: (1) cá nhân hóa gợi ý dựa trên hành vi người dùng qua ALS, (2) lọc cứng theo ràng buộc thực tế qua Knowledge-Based Filter, và (3) xếp hạng lại dựa trên chất lượng đánh giá đa chiều qua Review Quality Score — tất cả trên 43.9 triệu lượt đánh giá Electronics, chạy phân tán trên Apache Spark + MinIO trong môi trường Docker.

> **Điểm khác biệt so với v1.0 (Price Intelligence only)**
>
> - **v1.0:** Chỉ phân tích Price-Satisfaction Curve — output là insight, không phải recommendation
> - **v2.0:** Hệ thống khuyến nghị đầy đủ — output là danh sách sản phẩm cá nhân hóa cho từng user
> - **v2.0 bổ sung:** Knowledge-Based Filter (3 hard rules) + RQS Re-Ranker (4 structured signals)
> - **v2.0 bổ sung:** Ablation study 4 cấu hình (A→D) là contribution học thuật chính
> - Price Intelligence vẫn còn — đây là BQ-02 và BQ-03, phục vụ cả analysis lẫn dashboard

### 1.2. Cấu trúc 4 phase tổng thể

| Phase | Tên | Tuần | Mục tiêu chính | Deliverable chính | Trạng thái |
|:---:|---|:---:|---|---|:---:|
| Phase 1 | Foundation & Ingestion | 1–3 | Setup pipeline, Bronze + Silver layer, EDA | Silver Parquet + EDA Report | ✅ Done |
| Phase 2 | Feature Engineering | 4–7 | NLP processing, Gold layer (ALS/RQS/KB) | Gold Parquet | ⏳ TODO |
| Phase 3 | Hybrid 3 Tầng Modeling | 8–11 | ALS (T1) + KB Filter (T3) + RQS (T2) + Ablation | Model artifacts + Analysis | ⏳ TODO |
| Phase 4 | Product & Evaluation | 12–15 | Dashboard, ablation study, báo cáo, presentation | Demo + Final Report | ⏳ TODO |

### 1.3. Sơ đồ pipeline tổng thể

> **Luồng dữ liệu: HuggingFace → Bronze → Silver → Gold → Hybrid 3 tầng → Dashboard**

```
[NGUỒN] McAuley-Lab/Amazon-Reviews-2023 (HuggingFace Hub, streaming)             ✅
    ↓ HuggingFace streaming → Pandas pre-clean → PyArrow → MinIO
[BRONZE] electronics-bronze/ — Flat Parquet chunks (~300K rec/chunk, Snappy)       ✅
    ↓ Spark MapReduce: filter + transform + dedup
[SILVER] electronics-silver/reviews/ (partitioned year/month, zstd)                ✅
         electronics-silver/metadata/ (4 partitions, price parsed, zstd)            ✅
    ↓ NLP processing + Feature Engineering
[GOLD] electronics-gold/ — ALS matrix + RQS features + KB catalog                 ⏳
    ↓ TẦNG 1: ALS training → user/item latent vectors
    ↓ TẦNG 3: KB rules K-01/K-02/K-03 → hard filter
    ↓ TẦNG 2: RQS computation → re-rank → Top 10
[OUTPUT] Personalized Top 10 per user                                              ⏳
    ↓ Visualization layer
[DASHBOARD] Streamlit — Recommendation Demo + Ablation Charts                     ⏳
```

---

## PHASE 1: Foundation & Data Ingestion *(Tuần 1–3)* ✅ HOÀN THÀNH

**Mục tiêu:** Thiết lập toàn bộ infrastructure, tải dữ liệu thô vào Bronze layer qua HuggingFace streaming, transform Bronze → Silver qua Spark MapReduce, thực hiện EDA xác nhận chất lượng dữ liệu.

### Implementation thực tế

> **Notebook chính:** `02_stream_to_silver.ipynb` — thực hiện cả Bronze ingestion lẫn Silver MapReduce trong cùng 1 notebook (không tách riêng Bronze/Silver như kế hoạch ban đầu).

| Bước | Mô tả | Phương pháp thực tế |
|---|---|---|
| Bronze Reviews | HuggingFace → PyArrow chunks → MinIO | `download_and_chunk()` + `_pandas_pre_clean_reviews()` + `_write_chunk_pyarrow()` |
| Bronze Metadata | HuggingFace → PyArrow chunks → MinIO | Tương tự, dùng `_pandas_pre_clean_meta()` |
| Silver Reviews | Spark MapReduce: filter + transform + dedup | `mapreduce_reviews_to_silver()` — partitioned by `(review_year, review_month)`, zstd |
| Silver Metadata | Spark MapReduce: price parse + dedup | `mapreduce_metadata_to_silver()` — 4 partitions, zstd |
| Verification | Row count, null checks, file analysis | Cell 11: single Spark action + MinIO client |

### Checklist Phase 1 — Definition of Done

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| 1.1 | Infrastructure: 6 Docker containers healthy (minio, minio-init, spark-master, 2 workers, jupyter) | **✓ Xong** |
| 1.2 | MinIO 3 buckets (electronics-bronze, electronics-silver, electronics-gold) | **✓ Xong** |
| 1.3 | Spark ↔ MinIO read/write Parquet verified (`01_setup_verify.ipynb`) | **✓ Xong** |
| 1.4 | Bronze review chunks tại `electronics-bronze/reviews_chunks/` | **✓ Xong** |
| 1.5 | Bronze metadata chunks tại `electronics-bronze/metadata_chunks/` | **✓ Xong** |
| 1.6 | Silver reviews partitioned by `(review_year, review_month)`, zstd | **✓ Xong** |
| 1.7 | Silver metadata with `price_numeric` parsed, 4 partitions, zstd | **✓ Xong** |
| 1.8 | Verification: row count, null checks, rating range — PASS | **✓ Xong** |
| 1.9 | EDA notebook (`00-source-analyst.ipynb`): schema, ratings, temporal, DQ | **✓ Xong** |
| 1.10 | Source Analysis Document reviewed | **✓ Xong** |

> **Ghi chú so với kế hoạch ban đầu:**
>
> - Ingestion dùng HuggingFace streaming + PyArrow trực tiếp (không phải `spark.read.json()` trên JSONL.GZ)
> - Bronze là flat Parquet chunks (không partition theo year/month)
> - Review schema 8 fields (bỏ `asin`, `images`), Metadata schema 11 fields (bỏ `images`, `videos`, `details`)
> - Silver chưa áp dụng 5-core filter, verified filter, hay time window 2019–2023 (sẽ làm ở Phase 2 nếu cần)
> - Bronze + Silver gộp trong 1 notebook `02_stream_to_silver.ipynb` (không tách riêng 2 notebooks)

---

## PHASE 2: Feature Engineering & Gold Layer *(Tuần 4–7)* ⏳

**Mục tiêu:** Xây dựng Gold feature tables từ Silver layer, sẵn sàng cho cả 3 tầng. Silver layer đã hoàn thành ở Phase 1 (reviews partitioned by year/month + metadata with price parsed). Phase 2 tập trung vào NLP processing và Gold layer.

### Tasks chi tiết — NLP Processing

| ID | Task / Deliverable | Output cụ thể | Module | Ưu tiên |
|---|---|---|---|:---:|
| T2.1 | Text preprocessing: tokenize, stopword, lemma | Cleaned text columns | `src/nlp/text_pipeline.py` | P0 |
| T2.2 | ABSA: aspect extraction trên review text | Aspect-sentiment pairs | `src/nlp/absa.py` + `config/absa_seeds.yaml` | P0 |
| T2.3 | TF-IDF vectorization cho text similarity | TF-IDF feature vectors | `src/nlp/tfidf.py` | P1 |

**Notebook:** `04_silver_nlp.ipynb`

### Tasks chi tiết — Gold Layer (3 tầng)

| ID | Task / Deliverable | Output cụ thể | Module | Ưu tiên |
|---|---|---|---|:---:|
| T2.4 | ALS Matrix: StringIndexer userId/parent_asin → int | Gold/als_matrix/ (userIdx, itemIdx, rating) | `src/models/als_model.py` | P0 |
| T2.5 | RQS: Weighted_Rating (recency-weighted avg rating) | Gold/rqs_features/ | `src/evaluation/metrics.py` | P0 |
| T2.6 | RQS: Helpful_Ratio = log(1+helpful)/log(1+total) | Gold/rqs_features/ | `src/evaluation/metrics.py` | P0 |
| T2.7 | RQS: Verified_Rate = count(verified)/total | Gold/rqs_features/ | `src/evaluation/metrics.py` | P0 |
| T2.8 | RQS: Rating_Stability = 1/(1+std_by_year) | Gold/rqs_features/ | `src/evaluation/metrics.py` | P0 |
| T2.9 | Pre-compute RQS final score | Gold/rqs_scores/ | `src/evaluation/metrics.py` | P0 |
| T2.10 | KB: Price imputation + brand tier classification | Gold/product_features/ | `src/preprocessing/transformer.py` | P0 |
| T2.11 | KB: Rules table (price_numeric, rating_number, brand_tier) | Gold/product_features/kb_rules.parquet | `src/preprocessing/quality.py` | P0 |
| T2.12 | Co-purchase edge list từ bought_together | Gold/copurchase_edges/ | — | P1 |

### Checklist Phase 2 — Definition of Done

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| 2.1 | NLP pipeline: ABSA + TF-IDF trên review text (`04_silver_nlp.ipynb`) | **Chờ** |
| 2.2 | Gold ALS matrix: userIdx, itemIdx không null | **Chờ** |
| 2.3 | Gold RQS: 4 signal tables + rqs_final score | **Chờ** |
| 2.4 | Gold KB: kb_rules.parquet với price_numeric + rating_number + brand_tier | **Chờ** |
| 2.5 | Brand tier coverage ≥ 80% | **Chờ** |
| 2.6 | Co-purchase edges cho PageRank | **Chờ** |

---

## PHASE 3: Hybrid 3 Tầng Modeling & Ablation Study *(Tuần 8–11)*

**Mục tiêu:** Triển khai đầy đủ 3 tầng của hệ thống và chạy ablation study 4 cấu hình. Đây là phase thể hiện contribution học thuật của dự án — mỗi kỹ thuật CS246 phải được gắn với vai trò cụ thể trong một trong 3 tầng.

### Module T1 — Collaborative Filtering (ALS)

| ID | Task / Deliverable | Output cụ thể | Kỹ thuật CS246 / Tầng liên quan | Ưu tiên |
|---|---|---|---|:---:|
| T3.T1.1 | Build User-Item rating matrix từ Silver data | Sparse matrix (user_idx, item_idx, rating) | Spark MLlib StringIndexer \| T1 | P0 |
| T3.T1.2 | Train ALS: grid search rank=[20,50,100], regParam=[0.01,0.1] | Best ALS model checkpoint tại Gold/models/ | Spark ALS + CrossValidator \| T1 | P0 |
| T3.T1.3 | Evaluate ALS: RMSE trên temporal test set (2022–2023) | ALS RMSE so với popularity baseline | Spark RegressionEvaluator \| Ablation Config B | P0 |
| T3.T1.4 | Cold-start module: popularity-within-price-bucket | Popularity score table tại Gold/popularity/ | Spark groupBy sub_cat + price_bucket \| T1 fallback | P1 |
| T3.T1.5 | LSH: build product similarity clusters từ feature vectors | Similar product pairs (ASIN_a, ASIN_b, sim) | Spark MLlib MinHashLSH \| T1+T3 hỗ trợ | P1 |
| T3.T1.6 | PageRank trên co-purchase graph | Product authority scores tại Gold/pagerank/ | Spark GraphX PageRank damping=0.85 \| T3 hỗ trợ | P1 |

### Module T3 — Knowledge-Based Filter

| ID | Task / Deliverable | Output cụ thể | Kỹ thuật CS246 / Tầng liên quan | Ưu tiên |
|---|---|---|---|:---:|
| T3.T3.1 | Implement Rule K-01: price range hard filter | Spark filter function K01(df, price_min, price_max) | Spark DataFrame filter \| T3 K-01 | P0 |
| T3.T3.2 | Implement Rule K-02: review volume threshold | Spark filter function K02(df, min_reviews=50) | Spark DataFrame filter \| T3 K-02 | P0 |
| T3.T3.3 | Implement Rule K-03: brand tier matching từ user history | Spark join user history + filter brand_tier | Spark join + window \| T3 K-03 | P0 |
| T3.T3.4 | Pipeline KB: chạy K-01 → K-02 → K-03 sequential | KB pipeline function nhận 200 candidates → ~45 | Spark sequential filters \| T3 full | P0 |
| T3.T3.5 | Đo impact từng rule: reduction rate K-01, K-02, K-03 | Bảng: input count → output count mỗi rule | Spark count before/after \| Analysis | P1 |

### Module T2 — Review Quality Score (RQS)

| ID | Task / Deliverable | Output cụ thể | Kỹ thuật CS246 / Tầng liên quan | Ưu tiên |
|---|---|---|---|:---:|
| T3.T2.1 | Validate RQS formula trên 1000 sample: check correlation RQS vs human judgment | Correlation analysis notebook | Spark join + Pearson correlation \| T2 | P0 |
| T3.T2.2 | Tune RQS weights bằng grid search trên validation set | Optimal weights (w1,w2,w3,w4) | Spark cross-validation \| T2 | P1 |
| T3.T2.3 | Streaming: simulate rating stream theo timestamp → windowed RQS | Windowed RQS per product (6-month window) | Spark Structured Streaming + window \| T2 | P0 |
| T3.T2.4 | Change point detection: phát hiện products RQS thay đổi > 0.2 | Change point alert list | Spark lag() + threshold \| T2+BQ-03 | P1 |

### Ablation Study — 4 Cấu hình

| ID | Task / Deliverable | Output cụ thể | Kỹ thuật CS246 / Tầng liên quan | Ưu tiên |
|---|---|---|---|:---:|
| T3.ABL.1 | Config A — Baseline: popularity-based recommendation | NDCG@10, Precision@10, Hit Rate@10 cho Config A | Spark popularity ranking \| Ablation | P0 |
| T3.ABL.2 | Config B — CF Only: ALS recommendation, no filtering/reranking | Metrics cho Config B | Spark ALS inference only \| Ablation | P0 |
| T3.ABL.3 | Config C — CF + KB: ALS candidates → KB Filter, no RQS | Metrics cho Config C | T1 + T3 pipeline \| Ablation | P0 |
| T3.ABL.4 | Config D — Full Hybrid: ALS + KB Filter + RQS | Metrics cho Config D | T1 + T3 + T2 full pipeline \| Ablation | P0 |
| T3.ABL.5 | So sánh A vs B vs C vs D: bảng kết quả + statistical test | Ablation comparison table + p-values | Paired t-test \| Contribution | P0 |
| T3.ABL.6 | Per-sub-category analysis: Earbuds, Laptops, Smartphones | Metrics breakdown per sub-category | Spark stratified evaluation \| Analysis | P1 |
| T3.ABL.7 | Cold-start evaluation: đo riêng users < 5 interactions | Cold-start metrics comparison | Spark filter new users + evaluate \| Analysis | P1 |

### Checklist Phase 3 — Definition of Done

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| 3.1 | ALS RMSE < 1.2 trên temporal test set (2022–2023) | **Chờ** |
| 3.2 | KB Filter: đo được reduction rate của từng rule K-01/K-02/K-03 | **Chờ** |
| 3.3 | RQS: correlation với actual satisfaction ≥ 0.6 trên validation sample | **Chờ** |
| 3.4 | Full Hybrid pipeline: nhận user query → trả Top 10 trong < 30s | **Chờ** |
| 3.5 | Ablation: 4 configs đã chạy đủ, metrics documented | **Chờ** |
| 3.6 | Kết quả: D > C > B > A về NDCG@10 (hoặc giải thích nếu khác) | **Chờ** |
| 3.7 | Streaming pipeline: windowed RQS update theo từng month increment | **Chờ** |
| 3.8 | Tất cả model artifacts lưu tại Gold/models/ với version number | **Chờ** |
| 3.9 | Analysis narrative 1–2 trang: "What story does the data tell?" | **Chờ** |
| 3.10 | Notebook 05–08 chạy hoàn chỉnh, có comments giải thích từng bước | **Chờ** |

---

## PHASE 4: Product, Evaluation & Presentation *(Tuần 12–15)*

**Mục tiêu:** Đóng gói kết quả thành dashboard demo, hoàn thiện báo cáo học thuật, và chuẩn bị presentation. Đây là phase quyết định ấn tượng cuối cùng.

### Tasks chi tiết

| ID | Task / Deliverable | Output cụ thể | Kỹ thuật CS246 / Tầng liên quan | Ưu tiên |
|---|---|---|---|:---:|
| T4.1 | Dashboard: Recommendation widget + Sentiment radar + Trend chart | Streamlit app với 3 components | app/app.py + app/components/ | P0 |
| T4.2 | Dashboard: Hybrid pipeline live demo → Top 10 kết quả | Table hiển thị Top 10 + CF score + RQS score | Spark query + Plotly table \| Demo | P0 |
| T4.3 | Dashboard: Price-Satisfaction Curve visualization | Interactive curve với inflection points | Plotly line + scatter \| BQ-02 | P0 |
| T4.4 | Dashboard: RQS breakdown chart — 4 thành phần per product | Bar chart phân tích RQS components | Plotly bar chart \| T2 explanation | P1 |
| T4.5 | Dashboard: Temporal trend heatmap (year × price_bucket × rating) | Heatmap BQ-03 | Plotly heatmap \| BQ-03 | P1 |
| T4.6 | Dashboard: Ablation comparison chart A vs B vs C vs D | Bar chart metrics comparison | Plotly grouped bar \| Contribution | P0 |
| T4.7 | Evaluation report: full metrics table + statistical significance | Evaluation report notebook | Paired t-test \| Academic | P0 |
| T4.8 | Báo cáo cuối kỳ: 8–12 trang, format IEEE/ACM | Final report PDF/Word | LaTeX / Word \| Submission | P0 |
| T4.9 | Presentation slides: 15 phút + 5 phút Q&A, demo live | Slides 12–15 trang | PowerPoint \| Defense | P0 |
| T4.10 | Code cleanup: docstrings, requirements.txt, README hoàn chỉnh | Production-ready repo | Manual review \| Delivery | P1 |

### Checklist Phase 4 — Definition of Done

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| 4.1 | Dashboard: query → Top 10 trong < 30 giây từ Gold data | **Chờ** |
| 4.2 | Dashboard: hiển thị rõ CF score + RQS score + giải thích tại sao Top 1 được chọn | **Chờ** |
| 4.3 | Dashboard: Price-Satisfaction Curve có ít nhất 1 inflection point rõ ràng | **Chờ** |
| 4.4 | Dashboard: Ablation chart D > C > B > A visible và clear | **Chờ** |
| 4.5 | Báo cáo: 5 sections đầy đủ (Abstract, Intro, Methods, Results, Conclusion) | **Chờ** |
| 4.6 | Báo cáo: Ablation study table là mục Results chính, có statistical test | **Chờ** |
| 4.7 | Báo cáo: Citation dataset paper (Hou et al., 2024 arXiv:2403.03952) | **Chờ** |
| 4.8 | Demo live: chạy được không lỗi trong buổi thuyết trình | **Chờ** |
| 4.9 | Code: tất cả notebooks chạy lại từ đầu trên Docker sạch | **Chờ** |
| 4.10 | Nộp bài đúng hạn | **Chờ** |

---

## 2. Lịch trình Tổng hợp (Gantt Overview)

| Tuần | Phase | Task chính | Milestone |
|:---:|---|---|---|
| 1 | Phase 1 | Setup Docker infra + HuggingFace Bronze ingestion (reviews) | |
| 2 | Phase 1 | Bronze metadata + Silver MapReduce (reviews + metadata) | |
| 3 | Phase 1 | Verification + EDA (`00-source-analyst.ipynb`) | **M1:** Bronze + Silver Layer + EDA ✅ DONE |
| 4 | Phase 2 | NLP: ABSA + TF-IDF trên review text (`04_silver_nlp.ipynb`) | |
| 5 | Phase 2 | RQS signal tables: Weighted_Rating + Helpful_Ratio | |
| 6 | Phase 2 | RQS: Verified_Rate + Stability + pre-compute RQS final | |
| 7 | Phase 2 | Brand tier classification; KB rules table; copurchase edges | **M2:** Gold Layer DONE |
| 8 | Phase 3 | ALS training + hyperparameter tuning | |
| 9 | Phase 3 | KB Filter: implement K-01 + K-02 + K-03 + test pipeline | |
| 10 | Phase 3 | RQS validation + streaming windowed RQS | |
| 11 | Phase 3 | Ablation study 4 configs; LSH + PageRank | **M3:** Hybrid 3 Tầng + Ablation DONE |
| 12 | Phase 4 | Dashboard: query widget + Top 10 table + curve | |
| 13 | Phase 4 | Dashboard: ablation chart + temporal heatmap; báo cáo draft | |
| 14 | Phase 4 | Finalize báo cáo; slides; demo rehearsal | |
| 15 | Phase 4 | Nộp bài; thuyết trình cuối kỳ | **M4:** Final Submission |

### 2.1. Phân công vai trò nhóm

| Vai trò | Trách nhiệm chính | Phase tập trung | Tầng liên quan |
|---|---|:---:|---|
| Data Engineer | Bronze→Silver pipeline, ETL, schema validation, k-core | Phase 1 & 2 | Infrastructure + Silver |
| ML Engineer | ALS training, LSH, evaluation, hyperparameter tuning | Phase 2 & 3 | T1 — CF |
| Knowledge Engineer | KB rules K-01/K-02/K-03, brand tier, price parse | Phase 2 & 3 | T3 — KB Filter |
| Analytics Engineer | RQS formula, streaming, temporal analysis, ablation | Phase 2 & 3 | T2 — RQS |
| Product / Writer | Dashboard, visualization, báo cáo, slides, README | Phase 3 & 4 | All tầng (output) |

---

## 3. Quản lý Rủi ro Tổng hợp

| ID | Rủi ro | Xác suất | Tác động | Chiến lược |
|---|---|:---:|:---:|---|
| R01 | Null price > 50% — T3 K-01 không đủ dữ liệu | Cao | Cao | Scope top 5 sub-cat có price rate cao nhất; hoặc price proxy từ title |
| R02 | ALS không hội tụ hoặc RMSE > 1.5 | Trung bình | Cao | Fallback: item-based CF; vẫn đủ cho ablation |
| R03 | Docker OOM khi train ALS full Silver | Cao | Trung bình | Subsample 20%; hoặc tăng worker memory |
| R04 | RQS correlation thấp với actual satisfaction | Trung bình | Trung bình | Tune weights bằng grid search; adjust formula |
| R05 | Brand tier K-03 coverage thấp (store field null) | Trung bình | Thấp | Fallback parse từ title; Unknown tier không bị loại |
| R06 | Ablation kết quả D < C (RQS làm giảm chất lượng) | Thấp | Cao | Phân tích lỗi; điều chỉnh RQS weights; vẫn có giá trị học thuật |
| R07 | Tiến độ Phase 2 trễ → Phase 3 bị dồn | Trung bình | Cao | Buffer 1 tuần; Phase 3 T1 và T3 có thể song song |

---

## 4. Tiêu chí Đánh giá & Định nghĩa Thành công

### 4.1. Tiêu chí kỹ thuật

| Tiêu chí | Metric | Target tối thiểu | Target tốt | Cách đo |
|---|---|:---:|:---:|---|
| ALS Accuracy | RMSE test set | < 1.2 | < 0.95 | Spark RegressionEvaluator |
| Ablation: D vs A | NDCG@10 improvement | > 10% | > 20% | Full hybrid vs popularity baseline |
| Ablation: D vs B | NDCG@10 improvement | > 5% | > 12% | Full hybrid vs CF only |
| RQS Correlation | Pearson vs satisfaction | > 0.55 | > 0.70 | Validation sample 1000 products |
| KB Filter Rate | Precision của rules | K-01/K-02 không loại > 70% | < 50% loại | Count before/after mỗi rule |
| Pipeline Speed | End-to-end query time | < 60 giây | < 30 giây | Wall clock từ query đến Top 10 |
| Silver Quality | Non-null completeness | > 80% fields | > 90% | Spark describe() + null count |

### 4.2. Tiêu chí sản phẩm — Definition of Success

> **Dashboard "Hybrid Recommendation Demo" — Must Have / Should Have**
>
> - **MUST HAVE:** User nhập sub-cat + budget → hệ thống trả Top 10 trong < 30s với CF score + RQS score
> - **MUST HAVE:** Ablation comparison chart D > C > B > A — contribution học thuật visible ngay trên dashboard
> - **MUST HAVE:** Giải thích tại sao sản phẩm #1 được chọn — CF score bao nhiêu, RQS bao nhiêu, rule nào lọc gì
> - **SHOULD HAVE:** Price-Satisfaction Curve với inflection points cho ít nhất 3 sub-category
> - **SHOULD HAVE:** Temporal heatmap cho thấy kỳ vọng người dùng thay đổi theo năm
> - **NICE TO HAVE:** So sánh mode — input 2 products, hệ thống giải thích sự khác biệt RQS

---

## 5. Cấu trúc Notebook & Naming Convention

| Notebook | File | Phase | Nội dung | Trạng thái |
|---|---|:---:|---|:---:|
| NB-00 | 00-source-analyst.ipynb | Setup | Phân tích & xác minh nguồn dữ liệu HuggingFace | ✅ |
| NB-01 | 01_setup_verify.ipynb | Setup | Smoke test: Spark ↔ MinIO read/write Parquet | ✅ |
| NB-02 | 02_stream_to_silver.ipynb | Phase 1 | Bronze ingestion (HF→PyArrow→MinIO) + Silver MapReduce | ✅ |
| NB-04 | 04_silver_nlp.ipynb | Phase 2 | NLP processing: ABSA, TF-IDF, text pipeline | ⏳ |
| NB-05 | 05_gold_als.ipynb | Phase 3 | ALS train + evaluate + cold-start | ⏳ |
| NB-06 | 06_gold_lsh.ipynb | Phase 3 | LSH similarity clusters + product matching | ⏳ |
| NB-07 | 07_gold_pagerank.ipynb | Phase 3 | PageRank authority scoring trên co-purchase graph | ⏳ |
| NB-08 | 08_evaluation.ipynb | Phase 3-4 | Ablation study 4 configs + metrics + final evaluation | ⏳ |

> **Ghi chú:** Không có NB-03. Bronze + Silver gộp trong NB-02.

### MinIO Path Conventions (Thực tế)

```
Bronze:   s3a://electronics-bronze/reviews_chunks/chunk_NNNN.parquet     (flat, Snappy)
Bronze:   s3a://electronics-bronze/metadata_chunks/chunk_NNNN.parquet    (flat, Snappy)

Silver:   s3a://electronics-silver/reviews/review_year=YYYY/review_month=MM/*.parquet  (zstd)
Silver:   s3a://electronics-silver/metadata/*.parquet                                   (zstd)

Gold/ALS:     s3a://electronics-gold/als_matrix/                         (chưa tạo)
Gold/RQS:     s3a://electronics-gold/rqs_features/                       (chưa tạo)
Gold/RQS:     s3a://electronics-gold/rqs_scores/rqs_final.parquet        (chưa tạo)
Gold/KB:      s3a://electronics-gold/product_features/kb_rules.parquet   (chưa tạo)
Gold/Models:  s3a://electronics-gold/models/                             (chưa tạo)
Gold/Support: s3a://electronics-gold/pagerank_scores/                    (chưa tạo)
Gold/Support: s3a://electronics-gold/copurchase_edges/                   (chưa tạo)
```

---

## 6. Master Checklist — Toàn bộ Dự án

> Checklist tổng hợp để kiểm tra trạng thái dự án bất kỳ lúc nào.

### Infrastructure

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| I-01 | docker-compose up: 6 containers (minio, minio-init, spark-master, spark-worker-1, spark-worker-2, jupyter) | **✓ Xong** |
| I-02 | MinIO console: 3 buckets (electronics-bronze, electronics-silver, electronics-gold) | **✓ Xong** |
| I-03 | Spark Master UI localhost:8080 + 2 workers (8081, 8082) active | **✓ Xong** |
| I-04 | Jupyter Lab localhost:8888 accessible | **✓ Xong** |
| I-05 | NB-01 pass: Spark ↔ MinIO read/write Parquet | **✓ Xong** |
| I-06 | Source Analysis Document approved | **✓ Xong** |
| I-07 | README.md với hướng dẫn setup + pipeline | **✓ Xong** |

### Phase 1 — Data Ingestion ✅

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| P1-01 | Bronze review chunks (HuggingFace → PyArrow → MinIO) | **✓ Xong** |
| P1-02 | Bronze metadata chunks (HuggingFace → PyArrow → MinIO) | **✓ Xong** |
| P1-03 | Silver reviews (Spark MapReduce, review schema 8 fields, partitioned year/month, zstd) | **✓ Xong** |
| P1-04 | Silver metadata (Spark MapReduce, 11 fields, price parsed, 4 partitions, zstd) | **✓ Xong** |
| P1-05 | Verification: row count, null checks, rating range, file analysis — PASS | **✓ Xong** |
| P1-06 | EDA: `00-source-analyst.ipynb` — schema, ratings, temporal, data quality | **✓ Xong** |

### Phase 2 — Feature Engineering ⏳

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| P2-01 | NLP: ABSA + TF-IDF (`04_silver_nlp.ipynb`) | **Chờ** |
| P2-02 | Gold ALS matrix (userIdx, itemIdx, rating) | **Chờ** |
| P2-03 | Gold RQS: 4 signal tables + rqs_final | **Chờ** |
| P2-04 | Gold KB: kb_rules.parquet (price + rating_number + brand_tier) | **Chờ** |
| P2-05 | Brand tier coverage ≥ 80% | **Chờ** |
| P2-06 | Copurchase edges cho PageRank | **Chờ** |

### Phase 3 — Hybrid 3 Tầng + Ablation

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| P3-01 | T1: ALS RMSE < 1.2 trên test set 2022–2023 | **Chờ** |
| P3-02 | T3: KB pipeline K-01→K-02→K-03 chạy được, reduction rate documented | **Chờ** |
| P3-03 | T2: RQS correlation ≥ 0.55 trên validation sample | **Chờ** |
| P3-04 | Full pipeline: query → Top 10 trong < 60 giây | **Chờ** |
| P3-05 | Ablation: 4 configs đã chạy, metrics documented | **Chờ** |
| P3-06 | Ablation: statistical significance test (paired t-test) hoàn chỉnh | **Chờ** |
| P3-07 | Streaming: windowed RQS update per month increment | **Chờ** |

### Phase 4 — Product & Delivery

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| P4-01 | Dashboard: user query → Top 10 với explanation trong < 30s | **Chờ** |
| P4-02 | Dashboard: ablation chart D > C > B > A clearly visible | **Chờ** |
| P4-03 | Báo cáo: 8–12 trang, 5 sections, ablation study là Results chính | **Chờ** |
| P4-04 | Báo cáo: citation Hou et al. 2024 arXiv:2403.03952 | **Chờ** |
| P4-05 | Presentation slides: 12–15 slides, demo live không lỗi | **Chờ** |
| P4-06 | Code: tất cả 8 notebooks chạy lại từ đầu trên Docker sạch | **Chờ** |
| P4-07 | Nộp bài đúng hạn | **Chờ** |

---

## 7. Cấu trúc Mã nguồn (Source Code)

Dự án tổ chức source code theo mô-đun chức năng. Hiện tại chỉ `src/config/` đã triển khai, còn lại là stub. Logic ingestion nằm inline trong notebook `02_stream_to_silver.ipynb`.

| File / Module | Trạng thái | Phase / Tầng | Chức năng |
|---|:---:|---|---|
| `src/config/spark_config.py` | ✅ | Infrastructure | SparkSession (2g mem, 6 slots, S3A, zstd, AQE) + path helpers |
| `src/config/minio_config.py` | ✅ | Infrastructure | MinIO client (auto Docker/local) + ensure_buckets_exist() |
| `src/ingestion/hf_streamer.py` | ⏳ | Phase 1 | HuggingFace streaming (logic hiện inline trong NB-02) |
| `src/ingestion/bronze_writer.py` | ⏳ | Phase 1 | Bronze writer (logic hiện inline trong NB-02) |
| `src/preprocessing/cleaner.py` | ⏳ | Phase 2 | Dedup, null handling, type casting |
| `src/preprocessing/quality.py` | ⏳ | Phase 2 | Data quality checks |
| `src/preprocessing/transformer.py` | ⏳ | Phase 2 | Feature transformations cho Gold |
| `src/nlp/absa.py` | ⏳ | Phase 2 · T2 | ABSA (Aspect-Based Sentiment Analysis) |
| `src/nlp/text_pipeline.py` | ⏳ | Phase 2 · T2 | NLP text preprocessing |
| `src/nlp/tfidf.py` | ⏳ | Phase 2 · T2 | TF-IDF vectorization |
| `src/models/als_model.py` | ⏳ | Phase 3 · T1 | ALS Collaborative Filtering |
| `src/models/lsh_model.py` | ⏳ | Phase 3 · T1+T3 | LSH MinHash similarity |
| `src/models/pagerank.py` | ⏳ | Phase 3 · T3 | PageRank authority scoring |
| `src/evaluation/metrics.py` | ⏳ | Phase 3-4 | NDCG, Precision, MAP, ablation |
| `config/pipeline_config.yaml` | ⏳ | All Phases | Cấu hình pipeline chung |
| `config/absa_seeds.yaml` | ⏳ | Phase 2 | Seed words cho ABSA |
| `app/app.py` | ⏳ | Phase 4 | Streamlit entry point |
| `app/components/recommender.py` | ⏳ | Phase 4 | Recommendation UI |
| `app/components/sentiment_radar.py` | ⏳ | Phase 4 | Sentiment radar chart |
| `app/components/trend_chart.py` | ⏳ | Phase 4 | Temporal trend chart |
| `tests/test-datasource.py` | ✅ | Testing | HuggingFace streaming test |
| `tests/test_absa.py` | ⏳ | Testing | Unit test ABSA |
| `tests/test_cleaner.py` | ⏳ | Testing | Unit test cleaner |
| `tests/test_metrics.py` | ⏳ | Testing | Unit test metrics |

> ✅ = Đã triển khai | ⏳ = Stub/chưa triển khai

---

## Tài nguyên tham khảo quan trọng

| Tài nguyên | URL |
|---|---|
| Dataset paper | Hou et al. (2024) "Bridging Language and Items for Retrieval and Recommendation" — arXiv:2403.03952 |
| Dataset download | mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/ |
| HuggingFace | McAuley-Lab/Amazon-Reviews-2023 |
| CS246 Course | web.stanford.edu/class/cs246/ |
| Spark 3.5.1 MLlib ALS | spark.apache.org/docs/3.5.1/ml-collaborative-filtering.html |
| Spark 3.5.1 Streaming | spark.apache.org/docs/3.5.1/structured-streaming-programming-guide.html |
| MinIO Spark connector | min.io/docs/minio/linux/developers/spark/minio-spark.html |
