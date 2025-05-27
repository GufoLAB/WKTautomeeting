1. 先用會議通轉出逐字稿有時間戳記的版本

2. 然後用shorten_transcript.py 刪除時間戳記和整合發言人

3. (optional) 接著可以使用crystal_G3.py做結晶法 

4. 做chunk topic分段
4.1文章分段可以選用Alg_topic_split.py 數學方法不到一秒 
或是
4.2. topic_spliterG3v2.py 做兩件事情 
- 用ai(G3)分主題段落 約2萬字/200sec 
- 給予簡短摘要作為title、此摘要同時也取前15字作為chunks_topic檔名 
chunks_topic檔案會在inputfile位置產生chuck資料夾資料夾,裡面會有數十數百個段落檔.md

5.接著使用chucks_summary.py ai(G3)去輸入chuck資料夾的檔案路徑（目前路徑寫死在程式中） （以上兩種4.1、4.2方法都可以輸入）
跑出來的資料會在chuck資料夾裡面為長摘要csv檔"chunks_summaries_brief.csv"（也許用並行化處理加速）
還有一份shorten_topicsv2/chunks_summariesv3.jsonl 包含檔案名稱長摘要與逐字稿原文切片 適合拿去ＲＡＧ

6.brief_summary_reindex.py可以把上述"chunks_summaries_brief.csv"資料做適當簡化（去除不需要的ｃｓｖ欄位）
->/chunks_summaries_brief_output/chunks_summaries_brief_reindexed.csv

7.可跳過(Report_generation.py讀取上述檔案產出報告但因文字量過大效果不佳)

8.由於上述檔案太大因此要對50多條摘要進行切分成“summary blocks”，才有可能撰寫報告。
summary_topic_spliter.py讀取shorten_topicsv2/chunks_summaries_brief_output/chunks_summaries_brief_reindexed.csv 
中的summary欄位 進行約每八行給ＡＩ（G3）判斷chuncksummary 哪些可以再切割成一塊(block) ,
輸出到shorten_topicsv2/chunks_summaries_briefv3_topic_blocks
(然而此過程的ＡＩ輸出存在bug但結果依舊有一定的主題區分能力)

9.Reportcombiner.py讀取以上資料夾chunks_summaries_briefv3_topic_blocks會將內部 
的ＣＳＶ summary blocks 檔案（ex: 01_科工館預算危機.csv, 02_科工館營運與預算檢討.csv, ...）
 寫成 merged_summaries.md

10.merged_summaries.md 由於每一個summary blocks的ＡＩ都會試圖獨立完成報告
導致出現重複「本會議紀錄...會議紀錄結束...」重複數量等於 blocks
需要用clean_md.py 用re 清除大量錯誤字元

11.clean_md.py最終產出（格式不佳，但細節保留度高於GPT4.5）的報告
merged_summariesv2_cleaned.md




以下為之前的實驗，可以不用執行：
5.2接著用st ep1_embed_summary.py去讀取這個ＣＳＶ 產出以下兩者
    summary_embeddings.npy	N 個摘要的語意向量（通常為 384 維）	用於後續語意聚類或檢索
    chunk_ids.npy	對應每個向量的 chunk 名稱	可追溯回原始資料的 ID 或段落
    類聚效果不佳
5.3改採用chuks.md向量化類聚
    執行embed_cluster_chunksmd.py（目前路徑寫死在程式中 需要topics_split的資料夾內涵.md）
    使用兩個模型 (Alibaba-NLP/gte-large-zh, BAAI/bge-m3) 的嵌入
    KMeans 和 HDBSCAN 聚類方法，並可調整參數
    使用 UMAP 視覺化每個模型和聚類方法的結果，輸出圖像儲存在原資料夾中
    類聚效果不佳