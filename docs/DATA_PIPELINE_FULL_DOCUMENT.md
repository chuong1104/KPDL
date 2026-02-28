**BIG DATA PIPELINE**

**HYBRID RECOMMENDER SYSTEM**

Tài liệu kỹ thuật toàn diện --- Từ MapReduce Ingestion đến Delivery

Amazon Electronics · 43.9M Reviews · Apache Spark + MinIO + Docker +
Streamlit

  ----------------- ----------------- ----------------- -----------------
  **Phase 1**       **Phase 2**       **Phase 3**       **Phase 4**

  MapReduce         Feature           Modelling &       Dashboard &
  Ingestion         Engineering       Ablation          Report
  ----------------- ----------------- ----------------- -----------------

**0. MÔI TRƯỜNG & ĐIỀU KIỆN TIÊN QUYẾT**

Môi trường đã được setup thành công. Tài liệu này định nghĩa toàn bộ
công việc còn lại theo thứ tự thực thi, bắt đầu từ bước MapReduce
Ingestion cho đến khi hoàn thiện sản phẩm.

  ------------------ ----------------------------------------------------
  **Thành phần**     **Đặc tả kỹ thuật**

  **Cluster**        Docker Compose --- 1 spark-master + 1 spark-worker ·
                     network: spark-net

  **Compute Engine** Apache Spark 3.5.1 (PySpark) · executorMemory=4g ·
                     driverMemory=4g

  **Object Storage** MinIO S3-compatible · buckets: electronics-bronze /
                     electronics-silver / electronics-gold · port 9000/9001

  **Data Volume**    Reviews: 43.9M rows, 4.7 GB JSONL.GZ · Metadata:
                     \~3.1 GB JSONL.GZ

  **Target Size**    Silver: \~1.5--2 GB Parquet · Gold: \< 500 MB · RAM:
                     8--16 GB
  ------------------ ----------------------------------------------------

**1. PIPELINE TỔNG QUAN --- KIẾN TRÚC MEDALLION + HYBRID 3 TẦNG**

Kiến trúc tổng thể kết hợp mô hình Medallion Architecture (Bronze →
Silver → Gold) với Hybrid 3-Tier Recommendation Pipeline. Mỗi lớp có vai
trò rõ ràng, độc lập có thể kiểm thử, và kết nối với nhau thông qua
MinIO làm lớp lưu trữ trung gian.

+-----------------------------------------------------------------------+
| **📥 NGUỒN DỮ LIỆU THÔ**                                              |
|                                                                       |
| Electronics.jsonl.gz (4.7 GB) + meta_Electronics.jsonl.gz (3.1 GB) ·  |
| mcauleylab.ucsd.edu · UCSD Amazon Reviews\'23                         |
+-----------------------------------------------------------------------+

▼ BƯỚC 1: MapReduce Parallel Download + Checksum Verification ▼

+-----------------------------------------------------------------------+
| **🔴 BRONZE LAYER --- MinIO / electronics-bronze bucket**             |
|                                                                       |
| Raw JSONL → Parquet (schema-on-read) · Spark schema inference ·       |
| Partition by date · \~5.2 GB Parquet                                  |
+-----------------------------------------------------------------------+

▼ BƯỚC 2: Spark ETL --- Data Quality Assessment + Cleansing ▼

+-----------------------------------------------------------------------+
| **⚪ SILVER LAYER --- MinIO / electronics-silver bucket**             |
|                                                                       |
| Cleaned · Deduplicated · Null-imputed · 5-core filtered · \~43.9M →   |
| \~12M rows · 1.5--2 GB Parquet                                        |
+-----------------------------------------------------------------------+

▼ BƯỚC 3: Feature Engineering --- 3 luồng song song (Spark Jobs) ▼

+-----------------------+-----------------------+-----------------------+
| **🟡 GOLD --- T1: ALS | **🟡 GOLD --- T2: RQS | **🟡 GOLD --- T3: KB  |
| Matrix**              | Features**            | Catalog**             |
+-----------------------+-----------------------+-----------------------+
| **user_item_matrix**  | **rqs_features**      | **product_catalog**   |
|                       |                       |                       |
| userId × productId ×  | helpful_vote ·        | price · store ·       |
| rating                | verified_purchase     | rating_number         |
|                       |                       |                       |
| Parquet · partitioned | temporal_decay ·      | top-10 sub-categories |
| by userId             | rating_variance       | only                  |
+-----------------------+-----------------------+-----------------------+

▼ BƯỚC 4: Hybrid 3-Tier Inference Engine ▼

+-----------------------+-----------------------+-----------------------+
| **TIER 1 --- ALS      | **TIER 2 --- RQS      | **TIER 3 --- KB       |
| (MLlib)**             | Re-Rank**             | Filter**              |
+-----------------------+-----------------------+-----------------------+
| Collaborative         | Review Quality Score  | Hard constraint rules |
| Filtering             |                       |                       |
|                       | 200 → \~45 candidates | K-01: Price · K-02:   |
| Top-200 candidates /  |                       | Store                 |
| user                  | Weighted multi-signal |                       |
|                       | scoring               | K-03: Min review      |
| rank=50 · iter=10 ·   |                       | count                 |
| λ=0.01                |                       |                       |
+-----------------------+-----------------------+-----------------------+

▼ Final Top-10 Recommendations per User ▼

+-----------------------------------------------------------------------+
| **📊 ABLATION STUDY --- 4 Cấu hình**                                  |
|                                                                       |
| Config A (T1 only) · Config B (T1+T3) · Config C (T1+T2) · Config D   |
| (T1+T2+T3) · Metrics: NDCG@10, Precision@10, MAP                      |
+-----------------------------------------------------------------------+

▼ BƯỚC 5: Evaluation + Packaging ▼

+-----------------------------------------------------------------------+
| **🖥️ DELIVERY --- Streamlit Dashboard + Academic Report**             |
|                                                                       |
| Interactive demo · Ablation comparison charts · LaTeX/PDF report ·    |
| Presentation deck                                                     |
+-----------------------------------------------------------------------+

**2. PHASE 1 --- MAPREDUCE INGESTION VÀO BRONZE LAYER**

**2.1. Chiến lược MapReduce cho Large-Scale Ingestion**

MapReduce được áp dụng để phân rã bài toán ingestion \~7.8 GB dữ liệu
thô thành các tác vụ song song hoàn toàn độc lập, loại bỏ nút cổ chai
I/O tuần tự và tận dụng toàn bộ tài nguyên Spark cluster.

+-----------------------------------------------------------------------+
| **Nguyên lý MapReduce áp dụng cho Ingestion**                         |
|                                                                       |
| MAP PHASE: Mỗi block/partition của file JSONL.GZ được xử lý độc lập   |
| bởi một Spark task --- parse JSON, validate schema, emit              |
| (partition_key, record).                                              |
|                                                                       |
| SHUFFLE PHASE: Spark redistribute records theo partition key (asin    |
| hoặc date) --- đảm bảo locality cho downstream join giữa reviews và   |
| metadata.                                                             |
|                                                                       |
| REDUCE PHASE: Tổng hợp các records trong cùng partition, ghi ra file  |
| Parquet với snappy compression vào MinIO electronics-bronze bucket.   |
|                                                                       |
| Kết quả: Throughput tăng tuyến tính theo số worker --- 1 worker \~45  |
| phút, 2 workers \~25 phút cho toàn bộ dataset.                        |
+-----------------------------------------------------------------------+

**Task 1.1 --- Download & Verify dữ liệu nguồn**

1.  **Tải file Electronics.jsonl.gz** từ
    mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/

2.  **Tải file meta_Electronics.jsonl.gz** từ
    mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/meta_categories/

3.  **Checksum SHA256** --- verify integrity trước khi xử lý để tránh
    corrupt Parquet downstream

4.  **Đặt file vào volume MinIO** hoặc mount directory accessible từ
    Spark driver --- path: /data/raw/

**Task 1.2 --- Spark MapReduce Job: Raw JSONL → Bronze Parquet**

5.  **Khởi tạo SparkSession** với config S3/MinIO endpoint, accessKey,
    secretKey, path-style access

6.  **spark.read.json()** với multiLine=false (JSONL format) --- Spark
    tự động phân rã thành partitions (Map phase)

7.  **Schema inference / enforcement:** định nghĩa StructType tường minh
    cho cả 2 file để tránh schema drift

8.  **Áp dụng filter sơ bộ** --- loại bỏ dòng hoàn toàn null, kiểm tra
    cột bắt buộc (asin, user_id, rating)

9.  **Ghi Bronze Parquet** → MinIO s3a://electronics-bronze/reviews/ và
    s3a://electronics-bronze/metadata/ với partitionBy(\'main_category\')

10. **Validate Bronze** --- đọc lại sample 1% và kiểm tra row count khớp
    với wc -l gốc

**Task 1.3 --- EDA Bronze (Exploratory Data Analysis)**

-   **Row count audit:** 43.9M reviews (expected), \~786K metadata
    records

-   **Null analysis:** Đặc biệt cột price (metadata) --- expected null
    \~35--40% do sparse pricing

-   **Distribution check:** verified_purchase ratio, rating distribution
    (1--5 stars), helpful_vote stats

-   **Temporal coverage:** timestamp range --- confirm covers 2000--2023
    để temporal decay feature có ý nghĩa

-   **Sub-category inventory:** Liệt kê top-20 sub-categories theo
    volume để chọn top-10 cho scope reduction

**2.2. Công nghệ DE áp dụng trong Phase 1**

  ---------------- --------------- ---------------------------------------
  **Công nghệ**    **Vai trò**     **Lý do chọn**

  Apache Spark     MapReduce       Native distributed JSONL processing ·
                   Engine          in-memory shuffle · tối ưu hơn Hadoop
                                   MR cho iterative jobs

  MinIO (S3)       Data Lake       S3-compatible API · Docker-native ·
                   Storage         Bronze/Silver/Gold separation ·
                                   versioning support

  Parquet + Snappy Storage Format  Columnar storage · 60--70% compression
                                   vs JSONL · predicate pushdown cho
                                   downstream queries

  Spark Schema     Schema          Fail-fast trên schema mismatch · tránh
  StructType       Enforcement     silent data corruption · tài liệu hóa
                                   data contract
  ---------------- --------------- ---------------------------------------

+-----------------------------------------------------------------------+
| **✅ Definition of Done --- Phase 1 (Bronze Layer)**                  |
|                                                                       |
| □ electronics-bronze/reviews/ chứa Parquet với row count = 43,888,678  |
| (±0.1%)                                                               |
|                                                                       |
| □ electronics-bronze/metadata/ chứa Parquet với \~786,000 records      |
| metadata                                                              |
|                                                                       |
| □ Schema không có ambiguous type --- tất cả cột đều có explicit       |
| StructField                                                           |
|                                                                       |
| □ EDA notebook output: null rate report, distribution charts,         |
| sub-category inventory                                                |
|                                                                       |
| □ Spark job runtime \< 30 phút trên 2-node cluster (nếu \> 30: review |
| partitioning config)                                                  |
|                                                                       |
| □ Checksum SHA256 của file gốc được lưu vào                           |
| s3a://electronics-bronze/\_metadata/checksums.json                    |
+-----------------------------------------------------------------------+

**3. PHASE 2 --- FEATURE ENGINEERING (SILVER + GOLD LAYER)**

Phase 2 là phase kỹ thuật nặng nhất của dự án. Chất lượng Silver/Gold
layer quyết định trực tiếp chất lượng của cả 3 tầng trong hệ thống
Hybrid. Mỗi Spark job được thiết kế độc lập và có thể re-run mà không
ảnh hưởng đến job khác.

**3.1. Silver Layer --- Data Cleaning & Standardization**

**Task 2.1 --- Deduplication**

11. **Drop exact duplicates:** deduplicate trên (user_id, asin,
    timestamp) --- review trùng lặp hoàn toàn

12. **Near-duplicate detection:** group by (user_id, asin), giữ lại dòng
    có timestamp mới nhất nếu cùng user review cùng product nhiều lần

13. **Audit:** log số dòng trước và sau dedup --- expected drop \~2--5%

**Task 2.2 --- Null Imputation & Filtering**

-   **price (metadata):** impute = median price trong cùng main_category
    --- critical cho Knowledge Filter T3

-   **helpful_vote:** null → 0 (implicit: chưa có ai vote helpful)

-   **verified_purchase:** null → False (conservative assumption)

-   **5-core filtering:** chỉ giữ users có ≥ 5 reviews và items có ≥ 5
    reviews --- loại bỏ cold-start extreme cases

**Task 2.3 --- Data Type Standardization**

-   **timestamp:** convert Unix epoch → Spark TimestampType → year/month
    features

-   **rating:** cast FloatType, validate range \[1.0, 5.0\], reject
    out-of-range

-   **user_id / asin:** StringType, trim whitespace, lowercase
    normalization

-   **price:** parse string \'\$XX.XX\' → DoubleType, loại bỏ currency
    symbol

**Ghi Silver Parquet:** → s3a://electronics-silver/reviews_clean/ và
electronics-silver/metadata_clean/ · partitionBy(\'year\',\'main_category\')

**3.2. Gold Layer --- 3 Luồng Feature Engineering Song Song**

+-----------------------+-----------------------+-----------------------+
| **Gold T1 --- ALS     | **Gold T2 --- RQS     | **Gold T3 --- KB      |
| Matrix**              | Features**            | Catalog**             |
+-----------------------+-----------------------+-----------------------+
| **Module:              | **Module:              | **Module:              |
| src/models/           | src/nlp/              | src/preprocessing/    |
| als_model.py**        | text_pipeline.py +    | transformer.py +      |
|                       | src/evaluation/       | quality.py**          |
|                       | metrics.py**          |                       |
| 1\. Load Silver       |                       | 1\. Join metadata ×   |
| reviews               | 1\. helpful_score =   | Silver                |
|                       | log(helpful+1)        |                       |
| 2\. StringIndexer:    |                       | 2\. Scope: top-10     |
| userId → intId        | 2\. verified_weight:  | sub-categories        |
|                       | 1.3 vs 1.0            |                       |
| 3\. StringIndexer:    |                       | 3\. Calc avg_price,   |
| asin → itemId         | 3\. temporal_decay =  | min_reviews           |
|                       | exp(-λ·days)          |                       |
| 4\. Output: (userIdx, |                       | 4\. Define            |
| itemIdx, rating)      | 4\. rating_variance   | K-01/K-02/K-03 rules  |
|                       | per item              |                       |
| 5\. Save →            |                       | 5\. Save →            |
| gold/als_matrix/      | 5\. Save →            | gold/kb_catalog/      |
|                       | gold/rqs_features/    |                       |
+-----------------------+-----------------------+-----------------------+

**3.3. Công nghệ DE áp dụng trong Phase 2**

  ------------------ ----------------------------------------------------
  **Công nghệ / Kỹ   **Ứng dụng cụ thể trong Phase 2**
  thuật**            

  Spark DataFrame    ETL operations: filter, groupBy, agg, join --- lazy
  API                evaluation tối ưu execution plan

  Spark ML           Encode userId/asin thành integer index cho ALS ---
  StringIndexer      fit trên toàn Silver, transform deterministic

  Window Functions   Tính rating_variance, temporal ranking per user ---
                     thay thế Python UDF để tối ưu performance

  Broadcast Join     Join metadata (nhỏ \~500MB) với reviews (lớn \~2GB)
                     --- broadcast metadata để tránh shuffle join

  Parquet            partitionBy(\'main_category\') cho catalog --- tối
  Partitioning       ưu predicate pushdown khi filter theo category

  Data Quality       Assertion-based checks sau mỗi transformation: null
  (Great             rate \< 5%, value range, referential integrity
  Expectations       
  concept)           
  ------------------ ----------------------------------------------------

+-----------------------------------------------------------------------+
| **✅ Definition of Done --- Phase 2 (Silver + Gold)**                 |
|                                                                       |
| □ Silver reviews_clean: row count sau 5-core filter được log và       |
| verify (expected \~8--12M rows)                                       |
|                                                                       |
| □ Gold als_matrix: userIdx và itemIdx không có null, unique users ×   |
| items count được kiểm tra                                             |
|                                                                       |
| □ Gold rqs_features: temporal_decay values trong khoảng (0,1\], không |
| có Infinity/NaN                                                       |
|                                                                       |
| □ Gold kb_catalog: price không null (sau imputation), top-10          |
| sub-categories đủ coverage                                            |
|                                                                       |
| □ Tất cả 3 Gold jobs chạy độc lập thành công và có runtime \< 20 phút |
| mỗi job                                                               |
|                                                                       |
| □ Silver + Gold Parquet schemas được lưu dưới dạng JSON schema files  |
| trong /docs/schemas/                                                  |
+-----------------------------------------------------------------------+

**4. PHASE 3 --- HYBRID 3 TẦNG + ABLATION STUDY**

**4.1. Module T1 --- Collaborative Filtering (ALS)**

ALS (Alternating Least Squares) là kỹ thuật Matrix Factorization cho
implicit/explicit feedback. Spark MLlib ALS native hỗ trợ distributed
training trên user_item_matrix Gold layer.

**Task 3.1 --- Training ALS Model**

14. **Load Gold als_matrix** từ s3a://electronics-gold/als_matrix/ ---
    DataFrame với columns (userIdx, itemIdx, rating)

15. **Train/Test Split:** 80/20 random split, seed=42 --- ghi lại test
    set cho evaluation

16. **Hyperparameter config:** rank=50, maxIter=10, regParam=0.01,
    implicitPrefs=False (explicit ratings)

17. **Fit ALS model** --- Spark distributed training, monitor
    convergence loss per iteration

18. **Generate Top-200 recommendations** per user:
    model.recommendForAllUsers(200) → save s3a://electronics-gold/als_top200/

19. **Evaluate:** RegressionEvaluator (RMSE) trên test set + Ranking
    metrics (NDCG@10, Precision@10)

**4.2. Module T2 --- Review Quality Score (RQS)**

RQS là scoring function đa chiều, re-rank danh sách ALS candidates bằng
cách kết hợp 4 tín hiệu chất lượng structured, bổ sung bởi NLP
pipeline (ABSA + TF-IDF từ src/nlp/) để trích xuất aspect-level
sentiment từ review text. Dựa trên
structured fields từ Gold rqs_features.

+-----------------------------------------------------------------------+
| **Công thức RQS**                                                     |
|                                                                       |
| RQS(i) = w1 × helpful_score(i) + w2 × verified_weight(i) + w3 ×       |
| temporal_decay(i) + w4 × (1 - rating_variance(i))                     |
|                                                                       |
| Trong đó: w1=0.3, w2=0.25, w3=0.25, w4=0.2 (hyperparameters --- có    |
| thể tune)                                                             |
|                                                                       |
| helpful_score(i) = log(helpful_vote + 1) / log(max_helpful + 1) ---   |
| normalized log scale                                                  |
|                                                                       |
| verified_weight(i) = 1.3 nếu verified_purchase=True, else 1.0         |
|                                                                       |
| temporal_decay(i) = exp(-0.001 × days_since_review) --- recent        |
| reviews weighted higher                                               |
|                                                                       |
| rating_variance(i) = variance của tất cả ratings cho item i --- lower |
| variance = more consistent quality                                    |
+-----------------------------------------------------------------------+

**Task 3.2 --- RQS Re-ranking Pipeline**

20. **Load ALS Top-200** và join với Gold rqs_features trên asin

21. **Tính RQS score** cho mỗi (user, item) candidate --- Spark column
    expressions, không có UDF

22. **Re-rank:** sort candidates by (als_score \* rqs_weight)
    descending, lấy Top-45

23. **Save intermediate:** → s3a://electronics-gold/rqs_top45/

**4.3. Module T3 --- Knowledge-Based Filter**

Knowledge-Based Filter áp dụng hard constraints theo domain rules ---
loại bỏ sản phẩm không thỏa mãn ràng buộc kinh doanh bất kể score. Ba
rules chính được extract từ product_catalog Gold layer.

  ---------- ------------------ ---------------------- --------------------
  **Rule     **Tên Rule**       **Điều kiện lọc**      **Lý do nghiệp vụ**
  ID**                                                 

  **K-01**   Price Budget       price ≤ user_budget    Loại bỏ sản phẩm
             Filter             (nếu biết) hoặc price  ngoài tầm giá
                                ≤ category_median ×    
                                1.5                    

  **K-02**   Trusted Store      store IN whitelist     Ưu tiên brand/store
             Filter             top-sellers hoặc store đáng tin cậy
                                IS NOT NULL            

  **K-03**   Min Review Count   rating_number ≥ 10     Tránh recommend sản
                                (configurable          phẩm thiếu evidence
                                threshold)             
  ---------- ------------------ ---------------------- --------------------

24. **Task 3.3:** Load RQS Top-45 và join với kb_catalog trên asin

25. **Task 3.4:** Apply K-01/K-02/K-03 sequentially --- log filter rate
    cho từng rule

26. **Task 3.5:** Lấy Top-10 final recommendations --- save
    s3a://electronics-gold/final_recommendations/

**4.4. Ablation Study --- 4 Cấu hình**

Ablation study là contribution học thuật cốt lõi của dự án. Kết quả A \<
B \< C \< D là bằng chứng thực nghiệm cho thấy từng tầng mang lại
improvement có ý nghĩa thống kê.

  ------------ ---------------------- ------------------ --------------------
  **Config**   **Thành phần sử dụng** **Hypothesis**     **Expected NDCG@10**

  **A**        T1 (ALS only) ---      Baseline           \~0.05--0.08
               Baseline               performance        

  **B**        T1 + T3 (ALS + KB      Hard rules improve \> Config A
               Filter)                precision          

  **C**        T1 + T2 (ALS + RQS)    Quality signals    \> Config B
                                      improve ranking    

  **D**        T1 + T2 + T3 (Full     Combined approach  \> Config C
               Hybrid)                is best            
  ------------ ---------------------- ------------------ --------------------

+-----------------------------------------------------------------------+
| **✅ Definition of Done --- Phase 3 (Modelling + Ablation)**          |
|                                                                       |
| □ ALS model converges: RMSE trên test set được log, convergence curve |
| plot                                                                  |
|                                                                       |
| □ Top-200 ALS recommendations được generate cho toàn bộ users trong   |
| test set                                                              |
|                                                                       |
| □ RQS pipeline chạy không có NaN/Infinity trong score column          |
|                                                                       |
| □ Cả 3 KB rules hoạt động và filter rate được log (expected K-01:     |
| \~20%, K-02: \~10%, K-03: \~15%)                                      |
|                                                                       |
| □ 4 ablation configs chạy thành công và metrics NDCG@10,              |
| Precision@10, MAP được tính                                           |
|                                                                       |
| □ Thứ tự D \> C \> B \> A confirm hoặc có giải thích rõ nếu không     |
| đúng thứ tự                                                           |
+-----------------------------------------------------------------------+

**5. PHASE 4 --- DELIVERY: DASHBOARD + ACADEMIC REPORT**

**5.1. Streamlit Dashboard**

Dashboard là giao diện demo cuối cùng, thể hiện toàn bộ pipeline và kết
quả ablation study một cách trực quan. Được build bằng Streamlit và kết
nối trực tiếp với Gold/Output layer trên MinIO.

**Task 4.1 --- Dashboard Components**

-   **Input panel:** User ID input → load ALS recommendations → display
    full pipeline journey (T1 → T2 → T3)

-   **Ablation comparison:** Bar chart NDCG@10 cho 4 configs (A/B/C/D)
    --- highlight improvement % qua từng tier

-   **Item detail view:** Click vào recommended item → show metadata,
    RQS breakdown, KB rules status

-   **Data stats panel:** Live stats từ Parquet (Bronze/Silver/Gold row
    counts, null rates, timing metrics)

-   **Cold-start demo:** User không có history → fallback strategy
    visualization (popularity-based baseline)

**5.2. Academic Report**

**Task 4.2 --- Cấu trúc báo cáo học thuật**

27. Abstract (150--200 words): bài toán, phương pháp, kết quả chính

28. Introduction: motivation, contribution, paper structure

29. Related Work: ALS/MF literature, hybrid recommender systems, review
    quality scoring

30. System Architecture: Medallion architecture diagram, Hybrid 3-tier
    design

31. Dataset & Data Engineering: Amazon Reviews\'23, MapReduce ingestion,
    Silver/Gold pipeline

32. Methodology: T1 ALS formulation, T2 RQS formula, T3 KB rules formal
    definition

33. Experiments: Ablation study setup, evaluation metrics (NDCG, MAP,
    Precision), results table

34. Analysis & Discussion: Error analysis, cold-start handling,
    scalability analysis

35. Conclusion & Future Work: Limitations, NLP extension, production
    deployment path

+-----------------------------------------------------------------------+
| **✅ Definition of Done --- Phase 4 (Delivery)**                      |
|                                                                       |
| □ Streamlit dashboard chạy locally (make app), accessible               |
| tại http://localhost:8501                                               |
|                                                                       |
| □ Dashboard load recommendations trong \< 5 giây cho bất kỳ user_id   |
| trong test set                                                        |
|                                                                       |
| □ Ablation chart hiển thị đúng 4 configs với NDCG@10 values từ Phase  |
| 3                                                                     |
|                                                                       |
| □ Academic report đủ 9 sections, có bảng kết quả ablation và ít nhất  |
| 2 figures (architecture + results)                                    |
|                                                                       |
| □ Presentation deck: 10--12 slides, bao gồm live demo screenshot và   |
| ablation chart                                                        |
|                                                                       |
| □ README.md: hướng dẫn docker-compose up và reproduce toàn bộ         |
| pipeline từ đầu                                                       |
+-----------------------------------------------------------------------+

**6. TỔNG HỢP CÔNG NGHỆ DATA ENGINEERING ÁP DỤNG**

Bảng tổng hợp tất cả công nghệ và kỹ thuật DE được áp dụng trong toàn bộ
pipeline, phân loại theo layer và phase.

  ---------------- ------------------ --------------- ---------------------------
  **Layer**        **Công nghệ**      **Phase**       **Vai trò chi tiết**

  **Ingestion**    MapReduce (Spark)  Phase 1         Phân rã ingestion 7.8GB
                                                      thành parallel tasks ·
                                                      Map(parse) +
                                                      Shuffle(partition) +
                                                      Reduce(write Parquet)

                   Parquet + Snappy   Phase 1         Columnar format · 60-70%
                                                      compression · predicate
                                                      pushdown cho Silver filter

                   MinIO S3           Phase 1--4      Data lake storage ·
                                                      Bronze/Silver/Gold bucket
                                                      isolation · checkpoint-able
                                                      storage

  **ETL / DQ**     Spark DataFrame    Phase 2         Lazy evaluation · catalyst
                                                      optimizer · DAG
                                                      visualization · 100x faster
                                                      than Pandas trên 10M+ rows

                   Window Functions   Phase 2         Temporal aggregations
                                                      (rating variance, recency
                                                      rank) không cần
                                                      shuffle-heavy groupBy

                   Broadcast Join     Phase 2         Join metadata (small) với
                                                      reviews (large) · tránh
                                                      expensive shuffle join ·
                                                      broadcast threshold config

  **ML /           Spark MLlib ALS    Phase 3         Native distributed Matrix
  Modelling**                                         Factorization ·
                                                      rank/iter/lambda tuning ·
                                                      implicit/explicit feedback
                                                      support

                   ML Pipeline        Phase 3         Spark ML Pipeline API:
                                                      StringIndexer → ALS →
                                                      Recommender · serializable
                                                      và reproducible

  **Evaluation**   RankingEvaluator   Phase 3         NDCG@10, Precision@10, MAP
                                                      --- distributed computation
                                                      trên full test set

                   Ablation Framework Phase 3         4-config systematic
                                                      comparison · statistical
                                                      significance · contribution
                                                      isolation per tier

  **Delivery**     Streamlit          Phase 4         Python-native dashboard ·
                                                      MinIO integration ·
                                                      real-time recommendation
                                                      demo

                   Docker Compose     All Phases      Reproducible environment ·
                                                      service orchestration
                                                      (Spark + MinIO + Jupyter)
                                                      · one-command startup
                                                      (make up)
  ---------------- ------------------ --------------- ---------------------------

**6.1. Cấu trúc mã nguồn (Source Code)**

Dự án tổ chức source code theo mô-đun chức năng:

  ----------------------------- ----------------------------------------------
  **Module**                    **Vai trò**

  src/config/spark_config.py    Tạo SparkSession với MinIO S3A connector,
                                path helpers (bronze_path, silver_path,
                                gold_path)

  src/config/minio_config.py    MinIO client, tạo 3 buckets
                                (electronics-bronze/silver/gold)

  src/ingestion/hf_streamer.py  Streaming dữ liệu từ HuggingFace Hub

  src/ingestion/bronze_writer.py Ghi dữ liệu thô vào Bronze layer

  src/preprocessing/cleaner.py  Dedup, null handling, type casting

  src/preprocessing/quality.py  Data quality checks & assertions

  src/preprocessing/transformer.py  Feature transformations cho Silver/Gold

  src/nlp/absa.py               Aspect-Based Sentiment Analysis

  src/nlp/text_pipeline.py      NLP text preprocessing pipeline

  src/nlp/tfidf.py              TF-IDF vectorization

  src/models/als_model.py       ALS Collaborative Filtering (Tầng 1)

  src/models/lsh_model.py       LSH MinHash similarity

  src/models/pagerank.py        PageRank authority scoring

  src/evaluation/metrics.py     NDCG@10, Precision@10, MAP, ablation
                                comparison

  config/pipeline_config.yaml   Cấu hình pipeline chung

  config/absa_seeds.yaml        Seed words cho ABSA

  app/app.py                    Streamlit dashboard entry point

  app/components/recommender.py Recommendation UI component

  app/components/sentiment_radar.py  Sentiment radar chart component

  app/components/trend_chart.py Temporal trend visualization
  ----------------------------- ----------------------------------------------

**7. MASTER CHECKLIST --- TOÀN BỘ DỰ ÁN**

Checklist tổng hợp để track tiến độ toàn bộ pipeline. Cập nhật trạng
thái sau mỗi task hoàn thành.

**Phase 1 --- MapReduce Ingestion**

  -------- ---------------------------------------- ------------ ------------
  **\#**   **Task**                                 **Owner**    **Status**

  1.1      Download & checksum verify 2 file nguồn  DE Lead      □ TODO

  1.2      Spark MapReduce job: JSONL → Bronze      DE Lead      □ TODO
           Parquet                                               

  1.3      Validate Bronze row count và schema      QA           □ TODO

  1.4      EDA notebook: null analysis,             Analyst      □ TODO
           distributions, sub-category inventory                 
  -------- ---------------------------------------- ------------ ------------

**Phase 2 --- Feature Engineering**

  -------- ---------------------------------------- ------------ ------------
  **\#**   **Task**                                 **Owner**    **Status**

  2.1      Silver: deduplication + 5-core filter    DE           □ TODO

  2.2      Silver: null imputation (price median,   DE           □ TODO
           helpful_vote=0, verified=False)                       

  2.3      Silver: data type standardization +      DE           □ TODO
           schema validation                                     

  2.4      Gold T1: src/models/als_model.py ---     ML Eng       □ TODO
           StringIndexer + user_item_matrix                      

  2.5      Gold T2: src/nlp/ + src/evaluation/      ML Eng       □ TODO
           metrics.py --- RQS signals                            

  2.6      Gold T3: src/preprocessing/              ML Eng       □ TODO
           transformer.py + quality.py --- price                 
           imputation, store whitelist, review                   
           count                                                 
  -------- ---------------------------------------- ------------ ------------

**Phase 3 --- Modelling + Ablation**

  -------- ---------------------------------------- ------------ ------------
  **\#**   **Task**                                 **Owner**    **Status**

  3.1      Train ALS model (rank=50, iter=10,       ML Eng       □ TODO
           λ=0.01) + generate Top-200                            

  3.2      RQS pipeline: calculate 4 signals +      ML Eng       □ TODO
           re-rank Top-45                                        

  3.3      KB Filter: apply K-01/K-02/K-03 → Final  ML Eng       □ TODO
           Top-10                                                

  3.4      Run 4 ablation configs (A/B/C/D) +       ML Eng       □ TODO
           compute NDCG@10, MAP, Precision@10                    

  3.5      Statistical analysis ablation results    Analyst      □ TODO
           --- verify D \> C \> B \> A                           
  -------- ---------------------------------------- ------------ ------------

**Phase 4 --- Delivery**

  -------- ---------------------------------------- ------------ ------------
  **\#**   **Task**                                 **Owner**    **Status**

  4.1      Build Streamlit dashboard --- 5          FE/DE        □ TODO
           components (input, ablation chart, item               
           detail, stats, cold-start)                            

  4.2      Write academic report --- 9 sections với All          □ TODO
           ablation results table                                

  4.3      Prepare presentation deck --- 10--12     All          □ TODO
           slides + live demo                                    

  4.4      Write README.md --- reproduce pipeline   DE Lead      □ TODO
           từ docker-compose up                                  

  4.5      Final review + end-to-end smoke test     All          □ TODO
           toàn bộ pipeline                                      
  -------- ---------------------------------------- ------------ ------------

**8. QUẢN LÝ RỦI RO TỔNG HỢP**

  ------------------ ------------- ------------------ --------------------
  **Rủi ro**         **Xác suất**  **Impact**         **Mitigation**

  OOM Spark khi      **Cao**       Pipeline crash,    Dùng 5-core filter
  process 43.9M rows               mất tiến độ        sớm · tăng executor
                                                      memory · persist
                                                      Silver Parquet

  Null price \> 50%  **Trung       KB Filter T3 kém   Scope reduction
  sau imputation     bình**        chất lượng         top-10 sub-category
                                                      có price coverage
                                                      tốt nhất

  ALS không converge **Thấp**      T1 baseline yếu,   Tune regParam
  (RMSE không giảm)                ablation không có  (0.001--0.1), rank
                                   ý nghĩa            (10/50/100), verify
                                                      data không có bias

  D không tốt hơn C  **Trung       Yếu academic       Kiểm tra KB Filter
  trong ablation     bình**        contribution       không quá strict
                                                      (tune K-03
                                                      threshold) · phân
                                                      tích trên sub-groups

  Docker OOM khi     **Cao**       Không demo được    Run Spark jobs
  chạy Spark +                                        sequentially (không
  MinIO + Streamlit                                   concurrent) ·
  đồng thời                                           Streamlit load từ
                                                      cached Parquet,
                                                      không từ live Spark
  ------------------ ------------- ------------------ --------------------

© Data Engineering Pipeline v2.0 --- Dựa trên PROJECT_EXECUTION_PLAN_v2
& SOURCE_ANALYSIS_DOCUMENT_v2
