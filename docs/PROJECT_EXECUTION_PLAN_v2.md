# KẾ HOẠCH THỰC THI DỰ ÁN
> *Tài liệu Lập kế hoạch & Checklist Chi tiết | v2.0 — Hybrid 3 Tầng*

---

## Tên đề tài

**Hệ thống Khuyến nghị Sản phẩm Điện tử Cá nhân hóa Kết hợp Lọc Tri thức Miền và Chấm điểm Chất lượng Đánh giá Người dùng trên Nền tảng Xử lý Phân tán Apache Spark với Bộ dữ liệu Amazon Electronics Reviews 2023 (43.9 triệu lượt đánh giá)**

---

| Thuộc tính | Giá trị |
|---|---|
| **Dự án** | Price Intelligence + Personalized Recommendation — Amazon Electronics |
| **Môn học** | CS246 — Mining Massive Datasets (Big Data) |
| **Phiên bản** | v2.0 — 28/02/2026 — Cập nhật kiến trúc Hybrid 3 tầng |
| **Thời gian** | 15 tuần — Bắt đầu: 03/03/2026 |
| **Kiến trúc** | CF (ALS) → Knowledge-Based Filter (3 rules) → RQS Re-Ranker |
| **Infrastructure** | Docker: Spark 3.5.1 + MinIO Medallion + Jupyter Lab — Fully Containerized |
| **Trạng thái** | PRE-EXECUTION — Infrastructure DONE — Sẵn sàng Phase 1 |

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

| Phase | Tên | Tuần | Mục tiêu chính | Deliverable chính |
|:---:|---|:---:|---|---|
| Phase 1 | Foundation & Ingestion | 1–3 | Setup pipeline, Bronze layer, EDA | Bronze Parquet + EDA Report |
| Phase 2 | Feature Engineering | 4–7 | Silver/Gold layer, price parse, RQS signals, KB rules | Silver + Gold Parquet |
| Phase 3 | Hybrid 3 Tầng Modeling | 8–11 | ALS (T1) + KB Filter (T3) + RQS (T2) + Ablation | Model artifacts + Analysis |
| Phase 4 | Product & Evaluation | 12–15 | Dashboard, ablation study, báo cáo, presentation | Demo + Final Report |

### 1.3. Sơ đồ pipeline tổng thể

> **Luồng dữ liệu: Raw → Bronze → Silver → Gold → Hybrid 3 tầng → Dashboard**

```
[NGUỒN] McAuley Lab: Electronics.jsonl.gz (43.9M ratings) + meta_Electronics.jsonl.gz (1.6M items)
    ↓ Spark read JSONL + Parquet convert
[BRONZE] electronics-bronze/ — Dữ liệu thô, partition year/month, không transform
    ↓ verified filter + time filter (2019–2023) + price parse + k-core + brand tier
[SILVER] electronics-silver/ — ~15–18M reviews sạch, partition sub-category
    ↓ Aggregate: price_rating_agg | product_features | copurchase_edges | RQS signals
[GOLD] electronics-gold/ — Feature tables + model-ready aggregates + RQS pre-computed
    ↓ TẦNG 1: ALS training → user/item latent vectors
    ↓ TẦNG 3: KB rules K-01/K-02/K-03 → hard filter 200→45 candidates
    ↓ TẦNG 2: RQS computation → re-rank 45→Top 10
[OUTPUT] Personalized Top 10 + Price-Satisfaction Analysis + Temporal Trend Alerts
    ↓ Visualization layer
[DASHBOARD] Jupyter Plotly — Price Intelligence + Recommendation Demo
```

---

## PHASE 1: Foundation & Data Ingestion *(Tuần 1–3)*

**Mục tiêu:** Thiết lập toàn bộ infrastructure, tải dữ liệu thô vào Bronze layer, thực hiện EDA ban đầu để xác nhận chất lượng dữ liệu — đặc biệt tỷ lệ null price và phân phối verified_purchase — trước khi bắt đầu feature engineering.

### Tasks chi tiết

| ID | Task / Deliverable | Output cụ thể | Kỹ thuật CS246 / Tầng liên quan | Ưu tiên |
|---|---|---|---|:---:|
| T1.1 | Tải Electronics.jsonl.gz (~8GB) → Bronze Parquet | electronics-bronze/reviews/ partitioned year/month | Spark read JSONL, MapReduce write Parquet \| Tất cả tầng | P0 |
| T1.2 | Tải meta_Electronics.jsonl.gz (~4GB) → Bronze Parquet | electronics-bronze/meta/ Parquet | Spark read JSONL, write Parquet \| T3 Knowledge Rules | P0 |
| T1.3 | EDA: Phân phối rating theo năm 1996–2023 | Biểu đồ + bảng rating distribution | Spark groupBy + Matplotlib \| T1 ALS baseline | P0 |
| T1.4 | EDA: Null rate của field price theo sub-category | Bảng null% per sub-cat — chọn top 10 sub-cat | Spark describe() + countNull() \| T3 K-01 | P0 |
| T1.5 | EDA: Tỷ lệ verified_purchase toàn dataset | Tỷ lệ verified vs unverified — quyết định filter | Spark groupBy + count \| T2 Verified_Rate | P0 |
| T1.6 | EDA: Phân phối helpful_vote — histogram + zero rate | Báo cáo zero rate → confirm log(1+x) strategy | Spark describe() + histogram \| T2 Helpful_Ratio | P1 |
| T1.7 | EDA: Top 20 sub-category theo reviews + price coverage | Bảng chọn top 10 sub-cat cho scope | Spark groupBy + orderBy \| T3 scope | P1 |
| T1.8 | EDA: Price format analysis — pattern types và parsable rate | Danh mục patterns + tỷ lệ parsable → confirm regex | Spark regex sampling \| T3 K-01 | P1 |
| T1.9 | Xác nhận Bronze pipeline end-to-end, count check | NB 02_bronze_ingestion.ipynb pass toàn bộ | Integration test | P0 |

### Checklist Phase 1 — Definition of Done

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| 1.1 | Bronze reviews: count() ≈ 43.9M rows, schema đúng 10 fields | **Chờ** |
| 1.2 | Bronze meta: count() ≈ 1.6M rows, schema đúng 12 fields | **Chờ** |
| 1.3 | EDA notebook chạy không lỗi, 5 phân tích đều có output | **Chờ** |
| 1.4 | Đã xác nhận % null price và chọn top 10 sub-category có price rate cao nhất | **Chờ** |
| 1.5 | Đã xác nhận tỷ lệ verified — quyết định dùng filter T3 hay ratio T2 | **Chờ** |
| 1.6 | Đã xác nhận zero rate helpful_vote → confirm log(1+x) formula cho RQS | **Chờ** |
| 1.7 | Source Analysis Document v2.0 reviewed và approved bởi toàn nhóm | **✓ Xong** |
| 1.8 | Kế hoạch thực thi v2.0 (file này) reviewed và approved | **Chờ** |
| 1.9 | README.md cập nhật với hướng dẫn Phase 1 | **Chờ** |

> **Rủi ro Phase 1**
>
> - **RR-01 [CAO]** Tải ~12 GB chậm: wget với resume flag `-c`; tải ngoài giờ cao điểm
> - **RR-02 [CAO]** Null price > 50%: Scope reduction top 5 sub-cat; hoặc bổ sung Appliances dataset
> - **RR-03 [TB]** Spark OOM khi đọc toàn bộ JSONL: Đọc partition by year; tăng executor.memory

---

## PHASE 2: Feature Engineering & Silver/Gold Layer *(Tuần 4–7)*

**Mục tiêu:** Biến đổi Bronze thô thành Silver sạch và Gold feature tables sẵn sàng cho cả 3 tầng. Đây là phase kỹ thuật nặng nhất — chất lượng Silver/Gold quyết định trực tiếp chất lượng của T1 (ALS), T2 (RQS), và T3 (KB rules).

### Tasks chi tiết — Silver Layer

| ID | Task / Deliverable | Output cụ thể | Kỹ thuật CS246 / Tầng liên quan | Ưu tiên |
|---|---|---|---|:---:|
| T2.1 | Price parsing: string → float (parse "$XX.XX", loại range) | Silver: price_numeric float column | Spark UDF + Regex \| T3 K-01 | P0 |
| T2.2 | K-core filtering: user ≥ 5, item ≥ 10 (iterative, max 5 rounds) | Silver filtered ~15–18M rows | Spark iterative join + filter \| T1 ALS | P0 |
| T2.3 | Verified filter (True only) + time filter 2019–2023 | Silver: clean base dataset | Spark where() \| T2+T3 | P0 |
| T2.4 | Sub-category extraction từ categories array → chuẩn hóa | Silver: sub_category column chuẩn | Spark explode + regex \| T3 scope | P1 |
| T2.5 | Price bucket per sub-category (8 buckets, dynamic thresholds) | Silver: price_bucket column | Spark QuantileDiscretizer \| T3 K-01 | P0 |
| T2.6 | Dedup reviews: remove (user_id, parent_asin, timestamp) trùng | Silver: no duplicate rows | Spark dropDuplicates \| T1 data quality | P1 |

### Tasks chi tiết — Gold Layer (3 tầng)

| ID | Task / Deliverable | Output cụ thể | Kỹ thuật CS246 / Tầng liên quan | Ưu tiên |
|---|---|---|---|:---:|
| T2.7 | RQS Signal Table: Weighted_Rating per product per year | Gold/rqs_signals/weighted_rating.parquet | Spark window + exp recency weight \| T2 RQS | P0 |
| T2.8 | RQS Signal Table: Helpful_Ratio = log(1+helpful)/log(1+total) | Gold/rqs_signals/helpful_ratio.parquet | Spark agg \| T2 RQS | P0 |
| T2.9 | RQS Signal Table: Verified_Rate per product | Gold/rqs_signals/verified_rate.parquet | Spark agg \| T2 RQS | P0 |
| T2.10 | RQS Signal Table: Rating_Stability = 1/(1+std_by_year) | Gold/rqs_signals/stability.parquet | Spark groupBy year + std \| T2 RQS | P0 |
| T2.11 | Pre-compute RQS = 0.40×WR + 0.25×VR + 0.20×HR + 0.15×RS | Gold/rqs_scores/rqs_final.parquet | Spark join 4 tables + formula \| T2 | P0 |
| T2.12 | Brand Tier classification: Premium/Mid/Budget từ store field | Gold/product_features/brand_tier.parquet | Spark lookup + regex \| T3 K-03 | P0 |
| T2.13 | Product Features table: price_numeric, rating_number, brand_tier | Gold/product_features/kb_rules.parquet | Spark join meta + computed fields \| T3 | P0 |
| T2.14 | Price-Rating aggregation: mean/std per (sub_cat, price_bucket, year) | Gold/price_rating_agg/*.parquet | MapReduce groupBy agg \| BQ-02 analysis | P1 |
| T2.15 | Co-purchase edge list từ bought_together | Gold/copurchase_edges/*.parquet | Spark explode + join \| T1 PageRank | P1 |

### Checklist Phase 2 — Definition of Done

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| 2.1 | Silver count: 15M–18M rows sau toàn bộ filters | **Chờ** |
| 2.2 | Price parse: ≥ 60% items có price_numeric hợp lệ trong top 10 sub-cat | **Chờ** |
| 2.3 | Gold RQS: 4 signal tables đã tạo, coverage ≥ 300K products | **Chờ** |
| 2.4 | Gold RQS: rqs_final.parquet đã pre-compute cho ≥ 300K products | **Chờ** |
| 2.5 | Gold KB: brand_tier coverage ≥ 80% products (Premium/Mid/Budget/Unknown) | **Chờ** |
| 2.6 | Gold KB: kb_rules.parquet có đủ 3 fields: price_numeric, rating_number, brand_tier | **Chờ** |
| 2.7 | Gold: copurchase_edges ≥ 500K edges cho PageRank | **Chờ** |
| 2.8 | Notebook 03_silver_cleaning.ipynb chạy < 45 phút trên Docker cluster | **Chờ** |
| 2.9 | Sample inspection: 20 sản phẩm Wireless Earbuds đã có đủ RQS và KB fields | **Chờ** |
| 2.10 | Path conventions MinIO thống nhất và documented trong README | **Chờ** |

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
| 1 | Phase 1 | Tải Electronics.jsonl.gz → Bronze reviews | |
| 2 | Phase 1 | Tải meta → Bronze; EDA rating distribution + price null | |
| 3 | Phase 1 | EDA helpful_vote, verified, sub-cat; chọn top 10 scope | **M1:** Bronze Layer + EDA Report DONE |
| 4 | Phase 2 | Price parsing; k-core; verified+time filter → Silver | |
| 5 | Phase 2 | RQS signal tables: Weighted_Rating + Helpful_Ratio | |
| 6 | Phase 2 | RQS: Verified_Rate + Stability + pre-compute RQS final | |
| 7 | Phase 2 | Brand tier classification; KB rules table; copurchase edges | **M2:** Silver + Gold Layer DONE |
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

| Notebook | File | Phase | Nội dung | Tầng liên quan |
|---|---|:---:|---|---|
| NB-01 | 01_setup_verify.ipynb | Setup | Test MinIO + Spark — PASS | Infrastructure |
| NB-02 | 02_bronze_ingestion.ipynb | Phase 1 | Download → Bronze Parquet | All tầng (nguồn) |
| NB-03 | 03_silver_cleaning.ipynb | Phase 2 | Silver layer cleaning + dedup + standardization | T1+T2+T3 prep |
| NB-04 | 04_silver_nlp.ipynb | Phase 2 | NLP processing: ABSA, TF-IDF, text pipeline | T2 — RQS + NLP |
| NB-05 | 05_gold_als.ipynb | Phase 3 | ALS train + evaluate + cold-start | T1 — CF |
| NB-06 | 06_gold_lsh.ipynb | Phase 3 | LSH similarity clusters + product matching | T1+T3 support |
| NB-07 | 07_gold_pagerank.ipynb | Phase 3 | PageRank authority scoring trên co-purchase graph | T3 hỗ trợ |
| NB-08 | 08_evaluation.ipynb | Phase 3-4 | Ablation study 4 configs + metrics + final evaluation | Contribution + Academic |

### MinIO Path Conventions v2.0

```
Bronze:   s3a://electronics-bronze/reviews/year={YYYY}/month={MM}/*.parquet
Bronze:   s3a://electronics-bronze/meta/*.parquet

Silver:   s3a://electronics-silver/reviews_clean/sub_category={CAT}/*.parquet

Gold/RQS: s3a://electronics-gold/rqs_signals/{weighted_rating|helpful_ratio|verified_rate|stability}/
Gold/RQS: s3a://electronics-gold/rqs_scores/rqs_final.parquet

Gold/KB:  s3a://electronics-gold/product_features/kb_rules.parquet
Gold/KB:  s3a://electronics-gold/product_features/brand_tier.parquet

Gold/Models:  s3a://electronics-gold/models/als_v{N}/ (user_factors + item_factors)
Gold/Support: s3a://electronics-gold/pagerank_scores/ | copurchase_edges/ | popularity/
```

---

## 6. Master Checklist — Toàn bộ Dự án

> Checklist tổng hợp để kiểm tra trạng thái dự án bất kỳ lúc nào.

### Infrastructure

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| I-01 | docker-compose up -d: 5 containers (minio, minio-init, spark-master, spark-worker, jupyter) — 4 services healthy | **✓ Xong** |
| I-02 | MinIO console localhost:9001: 3 buckets tạo đủ (electronics-bronze, electronics-silver, electronics-gold) | **✓ Xong** |
| I-03 | Spark Master UI localhost:8080 accessible | **✓ Xong** |
| I-04 | Jupyter Lab localhost:8888 accessible | **✓ Xong** |
| I-05 | NB-01 pass: Spark ↔ MinIO read/write Parquet hoạt động | **✓ Xong** |
| I-06 | Source Analysis Document v2.0 approved | **✓ Xong** |
| I-07 | Project Execution Plan v2.0 (file này) approved toàn nhóm | **Chờ** |

### Phase 1 — Data Ingestion

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| P1-01 | Electronics.jsonl.gz (~8GB) tải về và extract thành công | **Chờ** |
| P1-02 | meta_Electronics.jsonl.gz (~4GB) tải về và extract thành công | **Chờ** |
| P1-03 | Bronze reviews count() ≈ 43.9M, schema 10 fields đúng | **Chờ** |
| P1-04 | Bronze meta count() ≈ 1.6M, schema 12 fields đúng | **Chờ** |
| P1-05 | EDA: null price rate documented, top 10 sub-cat đã chọn | **Chờ** |
| P1-06 | EDA: helpful_vote zero rate → confirmed log(1+x) strategy | **Chờ** |

### Phase 2 — Feature Engineering

| # | Checklist Item | Trạng thái |
|:---:|---|:---:|
| P2-01 | Silver: ≥ 15M rows sau toàn bộ filters | **Chờ** |
| P2-02 | Price parse ≥ 60% coverage trong top 10 sub-cat | **Chờ** |
| P2-03 | Gold RQS: 4 signal tables + rqs_final.parquet coverage ≥ 300K products | **Chờ** |
| P2-04 | Gold KB: kb_rules.parquet có price_numeric + rating_number + brand_tier | **Chờ** |
| P2-05 | Brand tier coverage ≥ 80% (Unknown tier cho phần còn lại) | **Chờ** |
| P2-06 | Copurchase edges ≥ 500K edges | **Chờ** |

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

Dự án tổ chức source code theo mô-đun chức năng, mapping trực tiếp với từng phase và tầng trong pipeline:

| File / Module | Phase / Tầng | Chức năng |
|---|---|---|
| `src/config/spark_config.py` | Infrastructure | SparkSession + MinIO S3A · path helpers (bronze_path, silver_path, gold_path) |
| `src/config/minio_config.py` | Infrastructure | MinIO client · ensure_buckets_exist() |
| `src/ingestion/hf_streamer.py` | Phase 1 | HuggingFace dataset streaming |
| `src/ingestion/bronze_writer.py` | Phase 1 | Bronze Parquet writer |
| `src/preprocessing/cleaner.py` | Phase 2 · Silver | Dedup, null handling, type casting |
| `src/preprocessing/quality.py` | Phase 2 · Silver | Data quality checks |
| `src/preprocessing/transformer.py` | Phase 2 · Gold | Feature transformations |
| `src/nlp/absa.py` | Phase 2 · T2 | ABSA (Aspect-Based Sentiment Analysis) |
| `src/nlp/text_pipeline.py` | Phase 2 · T2 | NLP text preprocessing |
| `src/nlp/tfidf.py` | Phase 2 · T2 | TF-IDF vectorization |
| `src/models/als_model.py` | Phase 3 · T1 | ALS Collaborative Filtering |
| `src/models/lsh_model.py` | Phase 3 · T1+T3 | LSH MinHash similarity |
| `src/models/pagerank.py` | Phase 3 · T3 | PageRank authority |
| `src/evaluation/metrics.py` | Phase 3-4 | NDCG, Precision, MAP, ablation comparison |
| `config/pipeline_config.yaml` | All Phases | Cấu hình pipeline chung |
| `config/absa_seeds.yaml` | Phase 2 | Seed words cho ABSA |
| `app/app.py` | Phase 4 | Streamlit entry point |
| `app/components/recommender.py` | Phase 4 | Recommendation UI |
| `app/components/sentiment_radar.py` | Phase 4 | Sentiment radar chart |
| `app/components/trend_chart.py` | Phase 4 | Temporal trend chart |
| `tests/test_absa.py` | Testing | Unit test ABSA |
| `tests/test_cleaner.py` | Testing | Unit test cleaner |
| `tests/test_metrics.py` | Testing | Unit test metrics |

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
