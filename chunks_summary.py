"""
這個程式的功能是：
1. 讀取指定資料夾內的多個 .md 檔案（每個檔案是一個逐字稿主題段落）
2. 使用本地 Gemma 27B 模型產生逐字稿摘要
3. 將摘要存入 CSV（含 chunk_id, summary, text 原文）
4. 將摘要 CSV 根據 GPT 模型判斷的主題切換點進一步切割
5. 每段切割後的資料再送入 GPT，產生十個字以內的主題作為檔名
6. 最終輸出至 `<摘要CSV檔名>_topic_blocks/` 資料夾，每段主題各為一個 CSV

執行方式（範例）：
python split_topics.py your_chunks_folder
"""

import os
import re
import argparse
import time
import pandas as pd
from dotenv import load_dotenv
import ollama
from tqdm import tqdm
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL
from zhconv_rs import zhconv

load_dotenv()

# ========= 設定區 =========
MAX_CHARS = 6000

# ========= 初始化 Ollama =========
def ai_response(messages, max_tokens=1000):
    response = ollama.Client(host=OLLAMA_URL).chat(
        model=AI_MODEL,
        messages=messages
    )
    assistant_reply = response['message']['content'].strip()
    if AI_MODEL.startswith("deepseek"):
        assistant_reply = re.sub(r'<think>(.*)</think>', '', assistant_reply, flags=re.DOTALL).strip()
    return zhconv(assistant_reply, "zh-tw")

# ========= 產生摘要 =========
def generate_summary_tags_natural(text):
    prompt = f"""逐字稿片段內容如下：\n{text}\n\n你是科工館的ai，請用不超過100字準確摘要逐字稿的主要意思，需包含重要數字、名稱、人事時地物與單位，無則不寫。"""
    if len(text) > MAX_CHARS:
        print(f"⚠️ 超出字數限制（{len(text)}字），跳過")
        return None
    messages = [{"role": "user", "content": prompt}]
    return ai_response(messages)

# ========= 讀取 .md 檔並生成摘要 CSV =========
def generate_summary_csv(md_folder):
    start_time = time.time()
    results = []
    for fname in sorted(os.listdir(md_folder)):
        if fname.endswith(".md"):
            with open(os.path.join(md_folder, fname), 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if len(content) < 2:
                    print(f"⚠️ 跳過內容不足：{fname}")
                    continue
                try:
                    summary = generate_summary_tags_natural(content)
                    if summary:
                        results.append({"chunk_id": fname[:-3], "summary": summary, "text": content})
                except Exception as e:
                    print(f"❌ 處理 {fname} 時發生錯誤: {e}")

    df = pd.DataFrame(results)
    csv_path = os.path.join(md_folder, "chunks_summaries.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df[["chunk_id", "summary"]].to_csv(csv_path.replace(".csv", "_brief.csv"), index=False, encoding="utf-8-sig")

    print(f"✅ 全部完成，寫入：\n{csv_path}\n{csv_path.replace('.csv', '_brief.csv')}")

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"執行時間：{elapsed:.2f} 秒")
    return csv_path

# ========= 主程式 =========
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", help="逐字稿.md所在資料夾")
    args = parser.parse_args()

    generate_summary_csv(args.folder)
