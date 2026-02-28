+-----------------------------------------------------------------------+
| **KẾ HOẠCH THỰC THI DỰ ÁN**                                           |
|                                                                       |
| *Tài liệu Lập kế hoạch & Checklist Chi tiết \| v2.0 --- Hybrid 3      |
| Tầng*                                                                 |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
| **Tên đề tài:**                                                       |
|                                                                       |
| **Hệ thống Khuyến nghị Sản phẩm Điện tử Cá nhân hóa Kết hợp Lọc Tri   |
| thức Miền và Chấm điểm Chất lượng Đánh giá Người dùng trên Nền tảng   |
| Xử lý Phân tán Apache Spark với Bộ dữ liệu Amazon Electronics Reviews |
| 2023 (43.9 triệu lượt đánh giá)**                                     |
+-----------------------------------------------------------------------+

  -------------------- ---------------------------------------------------
  **Dự án**            Price Intelligence + Personalized Recommendation
                       --- Amazon Electronics

  **Môn học**          CS246 --- Mining Massive Datasets (Big Data)

  **Phiên bản**        v2.0 --- 28/02/2026 --- Cập nhật kiến trúc Hybrid 3
                       tầng

  **Thời gian**        15 tuần --- Bắt đầu: 03/03/2026

  **Kiến trúc**        CF (ALS) → Knowledge-Based Filter (3 rules) → RQS
                       Re-Ranker

  **Infrastructure**   Docker: Spark 3.5.1 + MinIO Medallion + Jupyter Lab
                       --- Fully Containerized

  **Trạng thái**       PRE-EXECUTION --- Infrastructure DONE --- Sẵn sàng
                       Phase 1
  -------------------- ---------------------------------------------------

**1. TỔNG QUAN DỰ ÁN**

**1.1. Mục tiêu hệ thống**

Xây dựng hệ thống khuyến nghị Hybrid 3 tầng có khả năng: (1) cá nhân hóa
gợi ý dựa trên hành vi người dùng qua ALS, (2) lọc cứng theo ràng buộc
thực tế qua Knowledge-Based Filter, và (3) xếp hạng lại dựa trên chất
lượng đánh giá đa chiều qua Review Quality Score --- tất cả trên 43.9
triệu lượt đánh giá Electronics, chạy phân tán trên Apache Spark + MinIO
trong môi trường Docker.

+-----------------------------------------------------------------------+
| **Điểm khác biệt so với v1.0 (Price Intelligence only)**              |
|                                                                       |
| v1.0: Chỉ phân tích Price-Satisfaction Curve --- output là insight,   |
| không phải recommendation                                             |
|                                                                       |
| v2.0: Hệ thống khuyến nghị đầy đủ --- output là danh sách sản phẩm cá |
| nhân hóa cho từng user                                                |
|                                                                       |
| v2.0 bổ sung: Knowledge-Based Filter (3 hard rules) + RQS Re-Ranker   |
| (4 structured signals)                                                |
|                                                                       |
| v2.0 bổ sung: Ablation study 4 cấu hình (A→D) là contribution học     |
| thuật chính                                                           |
|                                                                       |
| Price Intelligence vẫn còn --- đây là BQ-02 và BQ-03, phục vụ cả      |
| analysis lẫn dashboard                                                |
+-----------------------------------------------------------------------+

**1.2. Cấu trúc 4 phase tổng thể**

  -----------------------------------------------------------------------------------
  **Phase**   **Tên**       **Tuần**   **Mục tiêu chính**       **Deliverable chính**
  ----------- ------------- ---------- ------------------------ ---------------------
  Phase 1     Foundation &  1--3       Setup pipeline, Bronze   Bronze Parquet + EDA
              Ingestion                layer, EDA               Report

  Phase 2     Feature       4--7       Silver/Gold layer, price Silver + Gold Parquet
              Engineering              parse, RQS signals, KB   
                                       rules                    

  Phase 3     Hybrid 3 Tầng 8--11      ALS (T1) + KB Filter     Model artifacts +
              Modeling                 (T3) + RQS (T2) +        Analysis
                                       Ablation                 

  Phase 4     Product &     12--15     Dashboard, ablation      Demo + Final Report
              Evaluation               study, báo cáo,          
                                       presentation             
  -----------------------------------------------------------------------------------

**1.3. Sơ đồ pipeline tổng thể**

+-----------------------------------------------------------------------+
| **Luồng dữ liệu: Raw → Bronze → Silver → Gold → Hybrid 3 tầng →       |
| Dashboard**                                                           |
|                                                                       |
| \[NGUỒN\] McAuley Lab: Electronics.jsonl.gz (43.9M ratings) +         |
| meta_Electronics.jsonl.gz (1.6M items)                                |
|                                                                       |
| ↓ Spark read JSONL + Parquet convert                                  |
|                                                                       |
| \[BRONZE\] electronics-bronze/ --- Dữ liệu thô, partition year/month, |
| không transform                                                       |
|                                                                       |
| ↓ verified filter + time filter (2019--2023) + price parse + k-core + |
| brand tier                                                            |
|                                                                       |
| \[SILVER\] electronics-silver/ --- \~15--18M reviews sạch, partition  |
| sub-category                                                          |
|                                                                       |
| ↓ Aggregate: price_rating_agg \| product_features \| copurchase_edges |
| \| RQS signals                                                        |
|                                                                       |
| \[GOLD\] electronics-gold/ --- Feature tables + model-ready           |
| aggregates + RQS pre-computed                                         |
|                                                                       |
| ↓ TẦNG 1: ALS training → user/item latent vectors                     |
|                                                                       |
| ↓ TẦNG 3: KB rules K-01/K-02/K-03 → hard filter 200→45 candidates     |
|                                                                       |
| ↓ TẦNG 2: RQS computation → re-rank 45→Top 10                         |
|                                                                       |
| \[OUTPUT\] Personalized Top 10 + Price-Satisfaction Analysis +        |
| Temporal Trend Alerts                                                 |
|                                                                       |
| ↓ Visualization layer                                                 |
|                                                                       |
| \[DASHBOARD\] Jupyter Plotly --- Price Intelligence + Recommendation  |
| Demo                                                                  |
+-----------------------------------------------------------------------+

  -----------------------------------------------------------------------
  **PHASE 1:** Foundation & Data Ingestion *(Tuần 1--3)*

  -----------------------------------------------------------------------

Mục tiêu: Thiết lập toàn bộ infrastructure, tải dữ liệu thô vào Bronze
layer, thực hiện EDA ban đầu để xác nhận chất lượng dữ liệu --- đặc biệt
tỷ lệ null price và phân phối verified_purchase --- trước khi bắt đầu
feature engineering.

**Tasks chi tiết**

  ------------------------------------------------------------------------------------------------
  **ID**   **Task / Deliverable**      **Output cụ thể**             **Kỹ thuật CS246 / **Ưu
                                                                     Tầng liên quan**   tiên**
  -------- --------------------------- ----------------------------- ------------------ ----------
  T1.1     Tải Electronics.jsonl.gz    electronics-bronze/reviews/   Spark read JSONL,  P0
           (\~8GB) → Bronze Parquet    partitioned year/month        MapReduce write    
                                                                     Parquet \| Tất cả  
                                                                     tầng               

  T1.2     Tải                         electronics-bronze/meta/      Spark read JSONL,  P0
           meta_Electronics.jsonl.gz   Parquet                       write Parquet \|   
           (\~4GB) → Bronze Parquet                                  T3 Knowledge Rules 

  T1.3     EDA: Phân phối rating theo  Biểu đồ + bảng rating         Spark groupBy +    P0
           năm 1996--2023              distribution                  Matplotlib \| T1   
                                                                     ALS baseline       

  T1.4     EDA: Null rate của field    Bảng null% per sub-cat ---    Spark describe() + P0
           price theo sub-category     chọn top 10 sub-cat           countNull() \| T3  
                                                                     K-01               

  T1.5     EDA: Tỷ lệ                  Tỷ lệ verified vs unverified  Spark groupBy +    P0
           verified_purchase toàn      --- quyết định filter         count \| T2        
           dataset                                                   Verified_Rate      

  T1.6     EDA: Phân phối helpful_vote Báo cáo zero rate → confirm   Spark describe() + P1
           --- histogram + zero rate   log(1+x) strategy             histogram \| T2    
                                                                     Helpful_Ratio      

  T1.7     EDA: Top 20 sub-category    Bảng chọn top 10 sub-cat cho  Spark groupBy +    P1
           theo reviews + price        scope                         orderBy \| T3      
           coverage                                                  scope              

  T1.8     EDA: Price format analysis  Danh mục patterns + tỷ lệ     Spark regex        P1
           --- pattern types và        parsable → confirm regex      sampling \| T3     
           parsable rate                                             K-01               

  T1.9     Xác nhận Bronze pipeline    NB 02_bronze_ingestion.ipynb  Integration test   P0
           end-to-end, count check     pass toàn bộ                                     
  ------------------------------------------------------------------------------------------------

**Checklist Phase 1 --- Definition of Done**

  ----------------------------------------------------------------------------
  **\#**   **Checklist Item**                                        **Trạng
                                                                     thái**
  -------- --------------------------------------------------------- ---------
  1.1      Bronze reviews: count() ≈ 43.9M rows, schema đúng 10      **Chờ**
           fields                                                    

  1.2      Bronze meta: count() ≈ 1.6M rows, schema đúng 12 fields   **Chờ**

  1.3      EDA notebook chạy không lỗi, 5 phân tích đều có output    **Chờ**

  1.4      Đã xác nhận % null price và chọn top 10 sub-category có   **Chờ**
           price rate cao nhất                                       

  1.5      Đã xác nhận tỷ lệ verified --- quyết định dùng filter T3  **Chờ**
           hay ratio T2                                              

  1.6      Đã xác nhận zero rate helpful_vote → confirm log(1+x)     **Chờ**
           formula cho RQS                                           

  1.7      Source Analysis Document v2.0 reviewed và approved bởi    **✓
           toàn nhóm                                                 Xong**

  1.8      Kế hoạch thực thi v2.0 (file này) reviewed và approved    **Chờ**

  1.9      README.md cập nhật với hướng dẫn Phase 1                  **Chờ**
  ----------------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **Rủi ro Phase 1**                                                    |
|                                                                       |
| RR-01 \[CAO\] Tải \~12 GB chậm: wget với resume flag -c; tải ngoài    |
| giờ cao điểm                                                          |
|                                                                       |
| RR-02 \[CAO\] Null price \> 50%: Scope reduction top 5 sub-cat; hoặc  |
| bổ sung Appliances dataset                                            |
|                                                                       |
| RR-03 \[TB\] Spark OOM khi đọc toàn bộ JSONL: Đọc partition by year;  |
| tăng executor.memory                                                  |
+-----------------------------------------------------------------------+

  -----------------------------------------------------------------------
  **PHASE 2:** Feature Engineering & Silver/Gold Layer *(Tuần 4--7)*

  -----------------------------------------------------------------------

Mục tiêu: Biến đổi Bronze thô thành Silver sạch và Gold feature tables
sẵn sàng cho cả 3 tầng. Đây là phase kỹ thuật nặng nhất --- chất lượng
Silver/Gold quyết định trực tiếp chất lượng của T1 (ALS), T2 (RQS), và
T3 (KB rules).

**Tasks chi tiết --- Silver Layer**

  --------------------------------------------------------------------------------
  **ID**   **Task /            **Output cụ thể**  **Kỹ thuật CS246 /    **Ưu
           Deliverable**                          Tầng liên quan**      tiên**
  -------- ------------------- ------------------ --------------------- ----------
  T2.1     Price parsing:      Silver:            Spark UDF + Regex \|  P0
           string → float      price_numeric      T3 K-01               
           (parse \"\$XX.XX\", float column                             
           loại range)                                                  

  T2.2     K-core filtering:   Silver filtered    Spark iterative       P0
           user ≥ 5, item ≥ 10 \~15--18M rows     join + filter \| T1   
           (iterative, max 5                      ALS                   
           rounds)                                                      

  T2.3     Verified filter     Silver: clean base Spark where() \|      P0
           (True only) + time  dataset            T2+T3                 
           filter 2019--2023                                            

  T2.4     Sub-category        Silver:            Spark explode + regex P1
           extraction từ       sub_category       \| T3 scope           
           categories array →  column chuẩn                             
           chuẩn hóa                                                    

  T2.5     Price bucket per    Silver:            Spark                 P0
           sub-category (8     price_bucket       QuantileDiscretizer   
           buckets, dynamic    column             \| T3 K-01            
           thresholds)                                                  

  T2.6     Dedup reviews:      Silver: no         Spark dropDuplicates  P1
           remove (user_id,    duplicate rows     \| T1 data quality    
           parent_asin,                                                 
           timestamp) trùng                                             
  --------------------------------------------------------------------------------

**Tasks chi tiết --- Gold Layer (3 tầng)**

  ---------------------------------------------------------------------------------------------------------------
  **ID**   **Task / Deliverable**        **Output cụ thể**                          **Kỹ thuật CS246 / **Ưu
                                                                                    Tầng liên quan**   tiên**
  -------- ----------------------------- ------------------------------------------ ------------------ ----------
  T2.7     RQS Signal Table:             Gold/rqs_signals/weighted_rating.parquet   Spark window + exp P0
           Weighted_Rating per product                                              recency weight \|  
           per year                                                                 T2 RQS             

  T2.8     RQS Signal Table:             Gold/rqs_signals/helpful_ratio.parquet     Spark agg \| T2    P0
           Helpful_Ratio =                                                          RQS                
           log(1+helpful)/log(1+total)                                                                 

  T2.9     RQS Signal Table:             Gold/rqs_signals/verified_rate.parquet     Spark agg \| T2    P0
           Verified_Rate per product                                                RQS                

  T2.10    RQS Signal Table:             Gold/rqs_signals/stability.parquet         Spark groupBy      P0
           Rating_Stability =                                                       year + std \| T2   
           1/(1+std_by_year)                                                        RQS                

  T2.11    Pre-compute RQS = 0.40×WR +   Gold/rqs_scores/rqs_final.parquet          Spark join 4       P0
           0.25×VR + 0.20×HR + 0.15×RS                                              tables + formula   
                                                                                    \| T2              

  T2.12    Brand Tier classification:    Gold/product_features/brand_tier.parquet   Spark lookup +     P0
           Premium/Mid/Budget từ store                                              regex \| T3 K-03   
           field                                                                                       

  T2.13    Product Features table:       Gold/product_features/kb_rules.parquet     Spark join meta +  P0
           price_numeric, rating_number,                                            computed fields \| 
           brand_tier                                                               T3                 

  T2.14    Price-Rating aggregation:     Gold/price_rating_agg/\*.parquet           MapReduce groupBy  P1
           mean/std per (sub_cat,                                                   agg \| BQ-02       
           price_bucket, year)                                                      analysis           

  T2.15    Co-purchase edge list từ      Gold/copurchase_edges/\*.parquet           Spark explode +    P1
           bought_together                                                          join \| T1         
                                                                                    PageRank           
  ---------------------------------------------------------------------------------------------------------------

**Checklist Phase 2 --- Definition of Done**

  ----------------------------------------------------------------------------
  **\#**   **Checklist Item**                                        **Trạng
                                                                     thái**
  -------- --------------------------------------------------------- ---------
  2.1      Silver count: 15M--18M rows sau toàn bộ filters           **Chờ**

  2.2      Price parse: ≥ 60% items có price_numeric hợp lệ trong    **Chờ**
           top 10 sub-cat                                            

  2.3      Gold RQS: 4 signal tables đã tạo, coverage ≥ 300K         **Chờ**
           products                                                  

  2.4      Gold RQS: rqs_final.parquet đã pre-compute cho ≥ 300K     **Chờ**
           products                                                  

  2.5      Gold KB: brand_tier coverage ≥ 80% products               **Chờ**
           (Premium/Mid/Budget/Unknown)                              

  2.6      Gold KB: kb_rules.parquet có đủ 3 fields: price_numeric,  **Chờ**
           rating_number, brand_tier                                 

  2.7      Gold: copurchase_edges ≥ 500K edges cho PageRank          **Chờ**

  2.8      Notebook 03_silver_cleaning.ipynb chạy \< 45 phút          **Chờ**
           trên Docker cluster                                       

  2.9      Sample inspection: 20 sản phẩm Wireless Earbuds đã có đủ  **Chờ**
           RQS và KB fields                                          

  2.10     Path conventions MinIO thống nhất và documented trong     **Chờ**
           README                                                    
  ----------------------------------------------------------------------------

  -----------------------------------------------------------------------
  **PHASE 3:** Hybrid 3 Tầng Modeling & Ablation Study *(Tuần 8--11)*

  -----------------------------------------------------------------------

Mục tiêu: Triển khai đầy đủ 3 tầng của hệ thống và chạy ablation study 4
cấu hình. Đây là phase thể hiện contribution học thuật của dự án --- mỗi
kỹ thuật CS246 phải được gắn với vai trò cụ thể trong một trong 3 tầng.

**Module T1 --- Collaborative Filtering (ALS)**

  ----------------------------------------------------------------------------------------------
  **ID**    **Task / Deliverable**           **Output cụ thể**  **Kỹ thuật CS246 /    **Ưu
                                                                Tầng liên quan**      tiên**
  --------- -------------------------------- ------------------ --------------------- ----------
  T3.T1.1   Build User-Item rating matrix từ Sparse matrix      Spark MLlib           P0
            Silver data                      (user_idx,         StringIndexer \| T1   
                                             item_idx, rating)                        

  T3.T1.2   Train ALS: grid search           Best ALS model     Spark ALS +           P0
            rank=\[20,50,100\],              checkpoint tại     CrossValidator \| T1  
            regParam=\[0.01,0.1\]            Gold/models/                             

  T3.T1.3   Evaluate ALS: RMSE trên temporal ALS RMSE so với    Spark                 P0
            test set (2022--2023)            popularity         RegressionEvaluator   
                                             baseline           \| Ablation Config B  

  T3.T1.4   Cold-start module:               Popularity score   Spark groupBy         P1
            popularity-within-price-bucket   table tại          sub_cat +             
                                             Gold/popularity/   price_bucket \| T1    
                                                                fallback              

  T3.T1.5   LSH: build product similarity    Similar product    Spark MLlib           P1
            clusters từ feature vectors      pairs (ASIN_a,     MinHashLSH \| T1+T3   
                                             ASIN_b, sim)       hỗ trợ                

  T3.T1.6   PageRank trên co-purchase graph  Product authority  Spark GraphX PageRank P1
                                             scores tại         damping=0.85 \| T3 hỗ 
                                             Gold/pagerank/     trợ                   
  ----------------------------------------------------------------------------------------------

**Module T3 --- Knowledge-Based Filter**

  ------------------------------------------------------------------------------
  **ID**    **Task /            **Output cụ thể**  **Kỹ thuật CS246 / **Ưu
            Deliverable**                          Tầng liên quan**   tiên**
  --------- ------------------- ------------------ ------------------ ----------
  T3.T3.1   Implement Rule      Spark filter       Spark DataFrame    P0
            K-01: price range   function K01(df,   filter \| T3 K-01  
            hard filter         price_min,                            
                                price_max)                            

  T3.T3.2   Implement Rule      Spark filter       Spark DataFrame    P0
            K-02: review volume function K02(df,   filter \| T3 K-02  
            threshold           min_reviews=50)                       

  T3.T3.3   Implement Rule      Spark join user    Spark join +       P0
            K-03: brand tier    history + filter   window \| T3 K-03  
            matching từ user    brand_tier                            
            history                                                   

  T3.T3.4   Pipeline KB: chạy   KB pipeline        Spark sequential   P0
            K-01 → K-02 → K-03  function nhận 200  filters \| T3 full 
            sequential          candidates → \~45                     

  T3.T3.5   Đo impact từng      Bảng: input count  Spark count        P1
            rule: reduction     → output count mỗi before/after \|    
            rate K-01, K-02,    rule               Analysis           
            K-03                                                      
  ------------------------------------------------------------------------------

**Module T2 --- Review Quality Score (RQS)**

  ------------------------------------------------------------------------------
  **ID**    **Task /            **Output cụ thể**  **Kỹ thuật CS246 / **Ưu
            Deliverable**                          Tầng liên quan**   tiên**
  --------- ------------------- ------------------ ------------------ ----------
  T3.T2.1   Validate RQS        Correlation        Spark join +       P0
            formula trên 1000   analysis notebook  Pearson            
            sample: check                          correlation \| T2  
            correlation RQS vs                                        
            human judgment                                            

  T3.T2.2   Tune RQS weights    Optimal weights    Spark              P1
            bằng grid search    (w1,w2,w3,w4)      cross-validation   
            trên validation set                    \| T2              

  T3.T2.3   Streaming: simulate Windowed RQS per   Spark Structured   P0
            rating stream theo  product (6-month   Streaming + window 
            timestamp →         window)            \| T2              
            windowed RQS                                              

  T3.T2.4   Change point        Change point alert Spark lag() +      P1
            detection: phát     list               threshold \|       
            hiện products RQS                      T2+BQ-03           
            thay đổi \> 0.2                                           
  ------------------------------------------------------------------------------

**Ablation Study --- 4 Cấu hình**

  ---------------------------------------------------------------------------------
  **ID**     **Task /              **Output cụ thể**  **Kỹ thuật CS246 / **Ưu
             Deliverable**                            Tầng liên quan**   tiên**
  ---------- --------------------- ------------------ ------------------ ----------
  T3.ABL.1   Config A ---          NDCG@10,           Spark popularity   P0
             Baseline:             Precision@10, Hit  ranking \|         
             popularity-based      Rate@10 cho Config Ablation           
             recommendation        A                                     

  T3.ABL.2   Config B --- CF Only: Metrics cho Config Spark ALS          P0
             ALS recommendation,   B                  inference only \|  
             no                                       Ablation           
             filtering/reranking                                         

  T3.ABL.3   Config C --- CF + KB: Metrics cho Config T1 + T3 pipeline   P0
             ALS candidates → KB   C                  \| Ablation        
             Filter, no RQS                                              

  T3.ABL.4   Config D --- Full     Metrics cho Config T1 + T3 + T2 full  P0
             Hybrid: ALS + KB      D                  pipeline \|        
             Filter + RQS                             Ablation           

  T3.ABL.5   So sánh A vs B vs C   Ablation           Paired t-test \|   P0
             vs D: bảng kết quả +  comparison table + Contribution       
             statistical test      p-values                              

  T3.ABL.6   Per-sub-category      Metrics breakdown  Spark stratified   P1
             analysis: Earbuds,    per sub-category   evaluation \|      
             Laptops, Smartphones                     Analysis           

  T3.ABL.7   Cold-start            Cold-start metrics Spark filter new   P1
             evaluation: đo riêng  comparison         users + evaluate   
             users \< 5                               \| Analysis        
             interactions                                                
  ---------------------------------------------------------------------------------

**Checklist Phase 3 --- Definition of Done**

  ----------------------------------------------------------------------------
  **\#**   **Checklist Item**                                        **Trạng
                                                                     thái**
  -------- --------------------------------------------------------- ---------
  3.1      ALS RMSE \< 1.2 trên temporal test set (2022--2023)       **Chờ**

  3.2      KB Filter: đo được reduction rate của từng rule           **Chờ**
           K-01/K-02/K-03                                            

  3.3      RQS: correlation với actual satisfaction ≥ 0.6 trên       **Chờ**
           validation sample                                         

  3.4      Full Hybrid pipeline: nhận user query → trả Top 10 trong  **Chờ**
           \< 30s                                                    

  3.5      Ablation: 4 configs đã chạy đủ, metrics documented        **Chờ**

  3.6      Kết quả: D \> C \> B \> A về NDCG@10 (hoặc giải thích nếu **Chờ**
           khác)                                                     

  3.7      Streaming pipeline: windowed RQS update theo từng month   **Chờ**
           increment                                                 

  3.8      Tất cả model artifacts lưu tại Gold/models/ với version   **Chờ**
           number                                                    

  3.9      Analysis narrative 1--2 trang: \"What story does the data **Chờ**
           tell?\"                                                   

  3.10     Notebook 05--08 chạy hoàn chỉnh, có comments giải thích   **Chờ**
           từng bước (05_gold_als, 06_gold_lsh,                        
           07_gold_pagerank, 08_evaluation)                          
  ----------------------------------------------------------------------------

  -----------------------------------------------------------------------
  **PHASE 4:** Product, Evaluation & Presentation *(Tuần 12--15)*

  -----------------------------------------------------------------------

Mục tiêu: Đóng gói kết quả thành dashboard demo, hoàn thiện báo cáo học
thuật, và chuẩn bị presentation. Đây là phase quyết định ấn tượng cuối
cùng.

**Tasks chi tiết**

  ------------------------------------------------------------------------------
  **ID**   **Task /             **Output cụ thể**  **Kỹ thuật CS246 / **Ưu
           Deliverable**                           Tầng liên quan**   tiên**
  -------- -------------------- ------------------ ------------------ ----------
  T4.1     Dashboard:           Streamlit app       app/app.py +       P0
           Recommendation       với 3 components:   app/components/    
           widget + Sentiment   recommender,        recommender.py,    
           radar + Trend chart  sentiment_radar,    sentiment_radar.py,
                                trend_chart         trend_chart.py     

  T4.2     Dashboard: Hybrid    Table hiển thị Top Spark query +      P0
           pipeline live demo → 10 + CF score +    Plotly table \|    
           Top 10 kết quả       RQS score          Demo               

  T4.3     Dashboard:           Interactive curve  Plotly line +      P0
           Price-Satisfaction   với inflection     scatter \| BQ-02   
           Curve visualization  points                                

  T4.4     Dashboard: RQS       Bar chart phân     Plotly bar chart   P1
           breakdown chart ---  tích RQS           \| T2 explanation  
           4 thành phần per     components                            
           product                                                    

  T4.5     Dashboard: Temporal  Heatmap BQ-03      Plotly heatmap \|  P1
           trend heatmap (year                     BQ-03              
           × price_bucket ×                                           
           rating)                                                    

  T4.6     Dashboard: Ablation  Bar chart metrics  Plotly grouped bar P0
           comparison chart A   comparison         \| Contribution    
           vs B vs C vs D                                             

  T4.7     Evaluation report:   Evaluation report  Paired t-test \|   P0
           full metrics table + notebook           Academic           
           statistical                                                
           significance                                               

  T4.8     Báo cáo cuối kỳ:     Final report       LaTeX / Word \|    P0
           8--12 trang, format  PDF/Word           Submission         
           IEEE/ACM                                                   

  T4.9     Presentation slides: Slides 12--15      PowerPoint \|      P0
           15 phút + 5 phút     trang              Defense            
           Q&A, demo live                                             

  T4.10    Code cleanup:        Production-ready   Manual review \|   P1
           docstrings,          repo               Delivery           
           requirements.txt,                                          
           README hoàn chỉnh                                          
  ------------------------------------------------------------------------------

**Checklist Phase 4 --- Definition of Done**

  ----------------------------------------------------------------------------
  **\#**   **Checklist Item**                                        **Trạng
                                                                     thái**
  -------- --------------------------------------------------------- ---------
  4.1      Dashboard: query → Top 10 trong \< 30 giây từ Gold data   **Chờ**

  4.2      Dashboard: hiển thị rõ CF score + RQS score + giải thích  **Chờ**
           tại sao Top 1 được chọn                                   

  4.3      Dashboard: Price-Satisfaction Curve có ít nhất 1          **Chờ**
           inflection point rõ ràng                                  

  4.4      Dashboard: Ablation chart D \> C \> B \> A visible và     **Chờ**
           clear                                                     

  4.5      Báo cáo: 5 sections đầy đủ (Abstract, Intro, Methods,     **Chờ**
           Results, Conclusion)                                      

  4.6      Báo cáo: Ablation study table là mục Results chính, có    **Chờ**
           statistical test                                          

  4.7      Báo cáo: Citation dataset paper (Hou et al., 2024         **Chờ**
           arXiv:2403.03952)                                         

  4.8      Demo live: chạy được không lỗi trong buổi thuyết trình    **Chờ**

  4.9      Code: tất cả notebooks chạy lại từ đầu trên Docker sạch   **Chờ**

  4.10     Nộp bài đúng hạn                                          **Chờ**
  ----------------------------------------------------------------------------

**2. LỊCH TRÌNH TỔNG HỢP (GANTT OVERVIEW)**

  ----------------------------------------------------------------------------------
  **Tuần**   **Phase**   **Task chính**                     **Milestone**
  ---------- ----------- ---------------------------------- ------------------------
  1          Phase 1     Tải Electronics.jsonl.gz → Bronze  
                         reviews                            

  2          Phase 1     Tải meta → Bronze; EDA rating      
                         distribution + price null          

  3          Phase 1     EDA helpful_vote, verified,        M1: Bronze Layer + EDA
                         sub-cat; chọn top 10 scope         Report DONE

  4          Phase 2     Price parsing; k-core;             
                         verified+time filter → Silver      

  5          Phase 2     RQS signal tables:                 
                         Weighted_Rating + Helpful_Ratio    

  6          Phase 2     RQS: Verified_Rate + Stability +   
                         pre-compute RQS final              

  7          Phase 2     Brand tier classification; KB      M2: Silver + Gold Layer
                         rules table; copurchase edges      DONE

  8          Phase 3     ALS training + hyperparameter      
                         tuning                             

  9          Phase 3     KB Filter: implement K-01 + K-02 + 
                         K-03 + test pipeline               

  10         Phase 3     RQS validation + streaming         
                         windowed RQS                       

  11         Phase 3     Ablation study 4 configs; LSH +    M3: Hybrid 3 Tầng +
                         PageRank                           Ablation DONE

  12         Phase 4     Dashboard: query widget + Top 10   
                         table + curve                      

  13         Phase 4     Dashboard: ablation chart +        
                         temporal heatmap; báo cáo draft    

  14         Phase 4     Finalize báo cáo; slides; demo     
                         rehearsal                          

  15         Phase 4     Nộp bài; thuyết trình cuối kỳ      M4: Final Submission
  ----------------------------------------------------------------------------------

**2.1. Phân công vai trò nhóm**

  ------------------------------------------------------------------------
  **Vai trò**  **Trách nhiệm chính**  **Phase tập  **Tầng liên quan**
                                      trung**      
  ------------ ---------------------- ------------ -----------------------
  Data         Bronze→Silver          Phase 1 & 2  Infrastructure + Silver
  Engineer     pipeline, ETL, schema               
               validation, k-core                  

  ML Engineer  ALS training, LSH,     Phase 2 & 3  T1 -- CF
               evaluation,                         
               hyperparameter tuning               

  Knowledge    KB rules               Phase 2 & 3  T3 -- KB Filter
  Engineer     K-01/K-02/K-03, brand               
               tier, price parse                   

  Analytics    RQS formula,           Phase 2 & 3  T2 -- RQS
  Engineer     streaming, temporal                 
               analysis, ablation                  

  Product /    Dashboard,             Phase 3 & 4  All tầng (output)
  Writer       visualization, báo                  
               cáo, slides, README                 
  ------------------------------------------------------------------------

**3. QUẢN LÝ RỦI RO TỔNG HỢP**

  -------------------------------------------------------------------------------
  **ID**   **Rủi ro**       **Xác    **Tác    **Chiến lược**
                            suất**   động**   
  -------- ---------------- -------- -------- -----------------------------------
  R01      Null price \>    Cao      Cao      Scope top 5 sub-cat có price rate
           50% --- T3 K-01                    cao nhất; hoặc price proxy từ title
           không đủ dữ liệu                   

  R02      ALS không hội tụ Trung    Cao      Fallback: item-based CF; vẫn đủ cho
           hoặc RMSE \> 1.5 bình              ablation

  R03      Docker OOM khi   Cao      Trung    Subsample 20%; hoặc tăng worker
           train ALS full            bình     memory
           Silver                             

  R04      RQS correlation  Trung    Trung    Tune weights bằng grid search;
           thấp với actual  bình     bình     adjust formula
           satisfaction                       

  R05      Brand tier K-03  Trung    Thấp     Fallback parse từ title; Unknown
           coverage thấp    bình              tier không bị loại
           (store field                       
           null)                              

  R06      Ablation kết quả Thấp     Cao      Phân tích lỗi; điều chỉnh RQS
           D \< C (RQS làm                    weights; vẫn có giá trị học thuật
           giảm chất lượng)                   

  R07      Tiến độ Phase 2  Trung    Cao      Buffer 1 tuần; Phase 3 T1 và T3 có
           trễ → Phase 3 bị bình              thể song song
           dồn                                
  -------------------------------------------------------------------------------

**4. TIÊU CHÍ ĐÁNH GIÁ & ĐỊNH NGHĨA THÀNH CÔNG**

**4.1. Tiêu chí kỹ thuật**

  ---------------------------------------------------------------------------
  **Tiêu chí**  **Metric**     **Target tối  **Target   **Cách đo**
                               thiểu**       tốt**      
  ------------- -------------- ------------- ---------- ---------------------
  ALS Accuracy  RMSE test set  \< 1.2        \< 0.95    Spark
                                                        RegressionEvaluator

  Ablation: D   NDCG@10        \> 10%        \> 20%     Full hybrid vs
  vs A          improvement                             popularity baseline

  Ablation: D   NDCG@10        \> 5%         \> 12%     Full hybrid vs CF
  vs B          improvement                             only

  RQS           Pearson vs     \> 0.55       \> 0.70    Validation sample
  Correlation   satisfaction                            1000 products

  KB Filter     Precision của  K-01/K-02     \< 50%     Count before/after
  Rate          rules          không loại \> loại       mỗi rule
                               70%                      
                               candidates               

  Pipeline      End-to-end     \< 60 giây    \< 30 giây Wall clock từ query
  Speed         query time                              đến Top 10

  Silver        Non-null       \> 80% fields \> 90%     Spark describe() +
  Quality       completeness                            null count
  ---------------------------------------------------------------------------

**4.2. Tiêu chí sản phẩm --- Definition of Success**

+-----------------------------------------------------------------------+
| **Dashboard \"Hybrid Recommendation Demo\" --- Must Have / Should     |
| Have**                                                                |
|                                                                       |
| MUST HAVE: User nhập sub-cat + budget → hệ thống trả Top 10 trong \<  |
| 30s với CF score + RQS score                                          |
|                                                                       |
| MUST HAVE: Ablation comparison chart D \> C \> B \> A ---             |
| contribution học thuật visible ngay trên dashboard                    |
|                                                                       |
| MUST HAVE: Giải thích tại sao sản phẩm #1 được chọn --- CF score bao  |
| nhiêu, RQS bao nhiêu, rule nào lọc gì                                 |
|                                                                       |
| SHOULD HAVE: Price-Satisfaction Curve với inflection points cho ít    |
| nhất 3 sub-category                                                   |
|                                                                       |
| SHOULD HAVE: Temporal heatmap cho thấy kỳ vọng người dùng thay đổi    |
| theo năm                                                              |
|                                                                       |
| NICE TO HAVE: So sánh mode --- input 2 products, hệ thống giải thích  |
| sự khác biệt RQS                                                      |
+-----------------------------------------------------------------------+

**5. CẤU TRÚC NOTEBOOK & NAMING CONVENTION**

  ----------------------------------------------------------------------------------------------------
  **Notebook**   **File**                       **Phase**   **Nội dung**          **Tầng liên quan**
  -------------- ------------------------------ ----------- --------------------- --------------------
  NB-01          01_setup_verify.ipynb          Setup       Test MinIO + Spark    Infrastructure
                                                            --- PASS              

  NB-02          02_bronze_ingestion.ipynb      Phase 1     Download → Bronze     All tầng (nguồn)
                                                            Parquet               

  NB-03          03_silver_cleaning.ipynb       Phase 2     Silver layer          T1+T2+T3 prep
                                                            cleaning + dedup +    
                                                            standardization       

  NB-04          04_silver_nlp.ipynb            Phase 2     NLP processing:       T2 -- RQS + NLP
                                                            ABSA, TF-IDF,         
                                                            text pipeline         

  NB-05          05_gold_als.ipynb              Phase 3     ALS train +           T1 -- CF
                                                            evaluate + cold-start 

  NB-06          06_gold_lsh.ipynb              Phase 3     LSH similarity        T1+T3 support
                                                            clusters +            
                                                            product matching      

  NB-07          07_gold_pagerank.ipynb         Phase 3     PageRank authority    T3 hỗ trợ
                                                            scoring trên          
                                                            co-purchase graph     

  NB-08          08_evaluation.ipynb            Phase 3-4   Ablation study 4      Contribution +
                                                            configs + metrics     Academic
                                                            + final evaluation    
  ----------------------------------------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **MinIO Path Conventions v2.0**                                       |
|                                                                       |
| Bronze:                                                               |
| s3a://electronics-bronze/reviews/year={YYYY}/month={MM}/\*.parquet    |
|                                                                       |
| Bronze: s3a://electronics-bronze/meta/\*.parquet                      |
|                                                                       |
| Silver:                                                               |
| s3a://electronics-silver/reviews_clean/sub_category={CAT}/\*.parquet  |
|                                                                       |
| Gold/RQS:                                                             |
| s3a://electronics-gold/rq                                             |
| s_signals/{weighted_rating\|helpful_ratio\|verified_rate\|stability}/ |
|                                                                       |
| Gold/RQS: s3a://electronics-gold/rqs_scores/rqs_final.parquet         |
|                                                                       |
| Gold/KB: s3a://electronics-gold/product_features/kb_rules.parquet     |
|                                                                       |
| Gold/KB: s3a://electronics-gold/product_features/brand_tier.parquet   |
|                                                                       |
| Gold/Models: s3a://electronics-gold/models/als_v{N}/ (user_factors +  |
| item_factors)                                                         |
|                                                                       |
| Gold/Support: s3a://electronics-gold/pagerank_scores/ \|              |
| copurchase_edges/ \| popularity/                                      |
+-----------------------------------------------------------------------+

**6. MASTER CHECKLIST --- TOÀN BỘ DỰ ÁN**

Checklist tổng hợp để kiểm tra trạng thái dự án bất kỳ lúc nào. Xanh =
DONE, Cam = Đang làm, Xanh nhạt = Chờ.

**Infrastructure**

  ----------------------------------------------------------------------------
  **\#**   **Checklist Item**                                        **Trạng
                                                                     thái**
  -------- --------------------------------------------------------- ---------
  I-01     docker-compose up -d: 5 containers (minio, minio-init,    **✓
           spark-master, spark-worker, jupyter) --- 4 services        Xong**
           healthy (minio-init exits sau khi tạo buckets)              

  I-02     MinIO console localhost:9001: 3 buckets tạo đủ              **✓
           (electronics-bronze, electronics-silver,                  Xong**
           electronics-gold)                                         

  I-03     Spark Master UI localhost:8080 accessible                 **✓
                                                                     Xong**

  I-04     Jupyter Lab localhost:8888 accessible                     **✓
                                                                     Xong**

  I-05     NB-01 pass: Spark ↔ MinIO read/write Parquet hoạt động    **✓
                                                                     Xong**

  I-06     Source Analysis Document v2.0 approved                    **✓
                                                                     Xong**

  I-07     Project Execution Plan v2.0 (file này) approved toàn nhóm **Chờ**
  ----------------------------------------------------------------------------

**Phase 1 --- Data Ingestion**

  ----------------------------------------------------------------------------
  **\#**   **Checklist Item**                                        **Trạng
                                                                     thái**
  -------- --------------------------------------------------------- ---------
  P1-01    Electronics.jsonl.gz (\~8GB) tải về và extract thành công **Chờ**

  P1-02    meta_Electronics.jsonl.gz (\~4GB) tải về và extract thành **Chờ**
           công                                                      

  P1-03    Bronze reviews count() ≈ 43.9M, schema 10 fields đúng     **Chờ**

  P1-04    Bronze meta count() ≈ 1.6M, schema 12 fields đúng         **Chờ**

  P1-05    EDA: null price rate documented, top 10 sub-cat đã chọn   **Chờ**

  P1-06    EDA: helpful_vote zero rate → confirmed log(1+x) strategy **Chờ**
  ----------------------------------------------------------------------------

**Phase 2 --- Feature Engineering**

  ----------------------------------------------------------------------------
  **\#**   **Checklist Item**                                        **Trạng
                                                                     thái**
  -------- --------------------------------------------------------- ---------
  P2-01    Silver: ≥ 15M rows sau toàn bộ filters                    **Chờ**

  P2-02    Price parse ≥ 60% coverage trong top 10 sub-cat           **Chờ**

  P2-03    Gold RQS: 4 signal tables + rqs_final.parquet coverage ≥  **Chờ**
           300K products                                             

  P2-04    Gold KB: kb_rules.parquet có price_numeric +              **Chờ**
           rating_number + brand_tier                                

  P2-05    Brand tier coverage ≥ 80% (Unknown tier cho phần còn lại) **Chờ**

  P2-06    Copurchase edges ≥ 500K edges                             **Chờ**
  ----------------------------------------------------------------------------

**Phase 3 --- Hybrid 3 Tầng + Ablation**

  ----------------------------------------------------------------------------
  **\#**   **Checklist Item**                                        **Trạng
                                                                     thái**
  -------- --------------------------------------------------------- ---------
  P3-01    T1: ALS RMSE \< 1.2 trên test set 2022--2023              **Chờ**

  P3-02    T3: KB pipeline K-01→K-02→K-03 chạy được, reduction rate  **Chờ**
           documented                                                

  P3-03    T2: RQS correlation ≥ 0.55 trên validation sample         **Chờ**

  P3-04    Full pipeline: query → Top 10 trong \< 60 giây            **Chờ**

  P3-05    Ablation: 4 configs đã chạy, metrics documented           **Chờ**

  P3-06    Ablation: statistical significance test (paired t-test)   **Chờ**
           hoàn chỉnh                                                

  P3-07    Streaming: windowed RQS update per month increment        **Chờ**
  ----------------------------------------------------------------------------

**Phase 4 --- Product & Delivery**

  ----------------------------------------------------------------------------
  **\#**   **Checklist Item**                                        **Trạng
                                                                     thái**
  -------- --------------------------------------------------------- ---------
  P4-01    Dashboard: user query → Top 10 với explanation trong \<   **Chờ**
           30s                                                       

  P4-02    Dashboard: ablation chart D \> C \> B \> A clearly        **Chờ**
           visible                                                   

  P4-03    Báo cáo: 8--12 trang, 5 sections, ablation study là       **Chờ**
           Results chính                                             

  P4-04    Báo cáo: citation Hou et al. 2024 arXiv:2403.03952        **Chờ**

  P4-05    Presentation slides: 12--15 slides, demo live không lỗi   **Chờ**

  P4-06    Code: tất cả 8 notebooks chạy lại từ đầu trên Docker       **Chờ**
           sạch                                                      

  P4-07    Nộp bài đúng hạn                                          **Chờ**
  ----------------------------------------------------------------------------

**7. CẤU TRÚC MÃ NGUỒN (SOURCE CODE)**

Dự án tổ chức source code theo mô-đun chức năng, mapping trực tiếp với
từng phase và tầng trong pipeline:

  -------------------------------- ------------------- ----------------------
  **File / Module**                **Phase / Tầng**    **Chức năng**

  src/config/spark_config.py       Infrastructure      SparkSession + MinIO
                                                       S3A · path helpers
                                                       (bronze_path,
                                                       silver_path, gold_path)

  src/config/minio_config.py       Infrastructure      MinIO client ·
                                                       ensure_buckets_exist()

  src/ingestion/hf_streamer.py     Phase 1             HuggingFace dataset
                                                       streaming

  src/ingestion/bronze_writer.py   Phase 1             Bronze Parquet writer

  src/preprocessing/cleaner.py     Phase 2 · Silver    Dedup, null handling,
                                                       type casting

  src/preprocessing/quality.py     Phase 2 · Silver    Data quality checks

  src/preprocessing/transformer.py Phase 2 · Gold      Feature transformations

  src/nlp/absa.py                  Phase 2 · T2        ABSA (Aspect-Based
                                                       Sentiment Analysis)

  src/nlp/text_pipeline.py         Phase 2 · T2        NLP text preprocessing

  src/nlp/tfidf.py                 Phase 2 · T2        TF-IDF vectorization

  src/models/als_model.py          Phase 3 · T1        ALS Collaborative
                                                       Filtering

  src/models/lsh_model.py          Phase 3 · T1+T3     LSH MinHash similarity

  src/models/pagerank.py           Phase 3 · T3        PageRank authority

  src/evaluation/metrics.py        Phase 3-4           NDCG, Precision, MAP,
                                                       ablation comparison

  config/pipeline_config.yaml      All Phases          Cấu hình pipeline chung

  config/absa_seeds.yaml           Phase 2             Seed words cho ABSA

  app/app.py                       Phase 4             Streamlit entry point

  app/components/recommender.py    Phase 4             Recommendation UI

  app/components/                  Phase 4             Sentiment radar chart
  sentiment_radar.py

  app/components/trend_chart.py    Phase 4             Temporal trend chart

  tests/test_absa.py               Testing             Unit test ABSA

  tests/test_cleaner.py            Testing             Unit test cleaner

  tests/test_metrics.py            Testing             Unit test metrics
  -------------------------------- ------------------- ----------------------

+-----------------------------------------------------------------------+
| **Tài nguyên tham khảo quan trọng**                                   |
|                                                                       |
| Dataset paper: Hou et al. (2024) \"Bridging Language and Items for    |
| Retrieval and Recommendation\" --- arXiv:2403.03952                   |
|                                                                       |
| Dataset download:                                                     |
| mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/             |
|                                                                       |
| HuggingFace: McAuley-Lab/Amazon-Reviews-2023                          |
|                                                                       |
| CS246 Course: web.stanford.edu/class/cs246/                           |
|                                                                       |
| Spark 3.5.1 MLlib ALS:                                                |
| spark.apache.org/docs/3.5.1/ml-collaborative-filtering.html           |
|                                                                       |
| Spark 3.5.1 Streaming:                                                |
| sp                                                                    |
| ark.apache.org/docs/3.5.1/structured-streaming-programming-guide.html |
|                                                                       |
| MinIO Spark connector:                                                |
| min.io/docs/minio/linux/developers/spark/minio-spark.html             |
+-----------------------------------------------------------------------+
