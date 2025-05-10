# 這個程式的功能：
# 1. 讀取指定資料夾內的多個 .md 檔案（每個檔案是一個逐字稿主題段落）
# 2. 每個 .md 檔案的第 1 行為標題，其餘為內容（text）
# 3. 使用本地 gemma3 27B 模型對每段逐字稿進行摘要與主題標籤生成
# 4. 將結果寫入兩份 CSV：
#    - chunks_summaries.csv：包含 chunk_id, title, summary, tags, text（含原文逐字稿）
#    - chunks_summaries_brief.csv：不含原文 text，方便瀏覽與後續載入使用
# 輸入資料夾範例路徑：/home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2
# 輸出檔案儲存於同一資料夾下，命名為 chunks_summaries.csv 和 chunks_summaries_brief.csv

import os
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
import re
import ollama
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL

# 載入環境變數
load_dotenv()

# 輸入資料夾與輸出檔案
chunk_folder = "/home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2"
output_csv = os.path.join(chunk_folder, "chunks_summaries.csv")

# 設定最大允許的中文字數（約略對應 7000 tokens，Gemma 27B 上限為 8192）
MAX_CHARS = 6000

# 讀取 chunk 檔案
all_data = []
for fname in sorted(os.listdir(chunk_folder)):
    if fname.endswith(".md"):
        with open(os.path.join(chunk_folder, fname), 'r', encoding='utf-8') as f:
            lines = f.readlines()
            title = lines[0].strip("# \n") if lines else ""
            content = "".join(lines[1:]).strip() if len(lines) > 1 else ""
            all_data.append({
                "chunk_id": fname.replace(".md", ""),
                "title": title,
                "text": content
            })

# 呼叫本地模型
def ai_response(conversation_history, max_tokens=1000):
    if BACK_END_MODEL == 'ollama':
        response = ollama.Client(host=OLLAMA_URL).chat(
            model=AI_MODEL,
            messages=conversation_history
        )
        assistant_reply = response['message']['content'].strip()
        if AI_MODEL.startswith("deepseek"):
            assistant_reply = re.sub(r'<think>(.*)</think>', '', assistant_reply, flags=re.DOTALL).strip()
    else:
        raise ValueError("Only OLLAMA backend is supported in this script.")
    return assistant_reply

# 產生摘要與標籤的 prompt
def generate_summary_tags_natural(text, title=""):
    prompt = f"""
逐字稿內容如下：
{text}

請你完成以下兩項任務：

1. 請你寫出不超過 80 字的摘要描述這段文字的核心內容（可能包含一到多個主題），需注意寫出重要數字或名稱或人事時地物（沒有提到就不用）。
2. 接著換一行，用「主題標籤：」開頭，列出不多於 5 個關鍵詞，用頓號「、」分隔，主題標籤8個字以內，應專注於那些別人一看就能想起來這一段在想什麼的標題。

請直接上述1與2格式回覆，不要其他任何說明或輸出。
""".strip()

    if len(prompt) > MAX_CHARS:
        print(f"⚠️ 超出字數限制（{len(prompt)} 字），跳過 {title}")
        return None
    
    messages = [{"role": "user", "content": prompt}]
    print("messages:",messages)
    response=ai_response(messages, max_tokens=6000)
    print("response:",response)
    return response

# 主處理流程
results = []
for row in tqdm(all_data, desc="產生摘要與主題標籤"):
    text_content = row["text"].strip()
    if len(text_content) < 2:
        print(f"⚠️ 跳過內容不足：{row['chunk_id']}")
        continue
    try:
        raw_output = generate_summary_tags_natural(text_content, row["title"])
        if raw_output is None:
            continue
        lines = raw_output.splitlines()
        summary = lines[0].strip()
        tag_line = [l for l in lines if l.startswith("主題標籤：")]
        tags = tag_line[0].replace("主題標籤：", "").replace("，", ",") if tag_line else ""
        results.append({
            "chunk_id": row["chunk_id"],
            "title": row["title"],
            "summary": summary,
            "tags": tags,
            "text": row["text"]
        })
    except Exception as e:
        print(f"❌ 處理 {row['chunk_id']} 時發生錯誤: {e}")

# 輸出 CSV
# 輸出 CSV（含原文 text）
if results:
    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    # ➕ 新增版本：不含原文 text 的 CSV
    output_csv_brief = os.path.join(chunk_folder, "chunks_summaries_brief.csv")
    df.drop(columns=["text"]).to_csv(output_csv_brief, index=False, encoding="utf-8-sig")
    print(f"✅ 簡版 CSV 也成功寫入，位置：{output_csv_brief}")
else:
    print("⚠️ 沒有任何資料寫入，請檢查過濾條件或 API 回應")
