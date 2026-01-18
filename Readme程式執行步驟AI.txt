【更新說明：現在有完整自動化流程！】

🆕 一鍵執行完整流程：
python integrated_main.py /path/to/shorten.txt

🆕 測試現有資料：
python integrated_main.py --test

========== 以下為詳細步驟說明 ==========

1. 會議通轉出逐字稿（原始資料）
用什麼：會議通App/平台

幹嘛：取得完整逐字稿，每句都有時間戳記

輸入：會議通原始錄音

輸出：逐字稿純文字檔（ex: 20250212第3次館務會報紀錄_逐字稿_修正版.txt）

2. 清理逐字稿：去除時間戳、整理說話人
用什麼：shorten_transcript.py

幹嘛：自動刪掉時間戳記、整理發言人格式

輸入：原始逐字稿 20250212第3次館務會報紀錄_逐字稿_修正版.txt

輸出：乾淨的逐字稿 /home/henry/automeeting/2025Feb_NSTM_meet/shorten.txt

3. （可略過）結晶法摘要
用什麼：crystal_G3.py

幹嘛：AI嘗試抓主題、做摘要（目前不建議，留作未來優化）

輸入：步驟2產生的純文字逐字稿

輸出：摘要或主題結構（格式依程式定義）

4. 主題分段（選一種即可，或都跑看看比較）
4.1. 數學快速分段法
用什麼：Alg_topic_split.py

幹嘛：用數學方法自動斷主題段落，超快

輸入：乾淨的逐字稿 /home/henry/automeeting/2025Feb_NSTM_meet/shorten.txt

輸出：分段後純文字檔（看設定）

4.2. AI主題分段＋摘要（推薦）
用什麼：topic_spliterG3v2.py

幹嘛：用AI分主題、幫每段生一個摘要（也拿前15字當檔名，沒發現特殊字元會有問題）

輸入：乾淨的逐字稿

輸出：產生 chunks_topic 資料夾，裡面每個段落都是一個 .md 檔案

5. 每段主題產生摘要（用AI）
用什麼：chucks_summary.py（內部路徑目前寫死，請注意維護）

幹嘛：AI對每個主題段落產生詳細摘要

輸入：chunks_topic 資料夾

輸出：

長摘要 CSV（chunks_summaries_brief.csv）

JSONL（shorten_topicsv2/chunks_summariesv3.jsonl，含原文與摘要，適合做RAG）

6. 簡化摘要檔
用什麼：brief_summary_reindex.py

幹嘛：去掉不必要欄位，整理成精簡版

輸入：chunks_summaries_brief.csv

輸出：/chunks_summaries_brief_output/chunks_summaries_brief_reindexed.csv

7. （可跳過）自動產出會議報告（但效果不佳）
用什麼：Report_generation.py

幹嘛：自動寫會議報告（目前因字數大效果不佳）

輸入/輸出：見原程式

8. 將長摘要切成主題區塊（summary blocks）
用什麼：summary_topic_spliter.py

幹嘛：把精簡摘要分成更細的主題塊（每約8行一組給AI判斷）

輸入：shorten_topicsv2/chunks_summaries_brief_output/chunks_summaries_brief_reindexed.csv

輸出：shorten_topicsv2/chunks_summaries_briefv3_topic_blocks/ 資料夾，裡面每個主題塊一個 CSV

9. 合併主題區塊產生Markdown
用什麼：Reportcombiner.py

幹嘛：把上一步各主題block合併成一份大md檔

輸入：chunks_summaries_briefv3_topic_blocks/ 裡面所有CSV

輸出：merged_summaries.md

10. 處理重複內容與雜訊（結果需人工再修）
用什麼：clean_md.py

幹嘛：用re清掉重複句、雜訊（如「本會議紀錄...」會多次出現），但有時還是需要手動校正

輸入：merged_summaries.md

輸出：merged_summariesv2_cleaned.md

以下實驗在long_report_test
10.2 測試合併兩段（僅供測試用）
用什麼：test_2chunks.py

幹嘛：精準測試AI合併兩段報告會怎樣

用法：
python test_2chunks.py --s（用內建prompt測試）
python test_2chunks.py（進入對話模式）

10.3 逐步續寫（單段測試用）
用什麼：continuous_writing.py

幹嘛：每次只處理一個新摘要，自動更新報告內容

流程：

抓現有報告最後五行（可調整）

輸入「新摘要內容」

AI合併舊結尾和新摘要，生成新結尾，更新檔案

支援用 --summary 指定內容或互動輸入

限制：一次約1600中文字

11. 類聚與向量化流程（目前不建議用，僅保留供未來優化）
step1_embed_summary.py、embed_cluster_chunksmd.py

主要功能：摘要或逐字稿向量化、語意聚類

目前效果不佳，建議先不用