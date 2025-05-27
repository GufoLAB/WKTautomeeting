import os
import re
import time
import pandas as pd
from dotenv import load_dotenv
import ollama
from tqdm import tqdm
from zhconv_rs import zhconv
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL
from itertools import count
# 載入環境變數
load_dotenv()

# 設定參數
INPUT_DIR = "/home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2/chunks_summaries_briefv3_topic_blocks"  # TODO: 改成你的資料夾名稱
MAX_CHARS = 7000

# 初始化 ollama client
client = ollama.Client(host=OLLAMA_URL)

def ai_response(messages, max_tokens=1000):
    response = client.chat(
        model=AI_MODEL,
        messages=messages
    )
    assistant_reply = response['message']['content'].strip()
    if AI_MODEL.startswith("deepseek"):
        assistant_reply = re.sub(r'<think>(.*?)</think>', '', assistant_reply, flags=re.DOTALL).strip()
    return zhconv(assistant_reply, "zh-tw")

# 處理一個 CSV，合併所有段落，並生成摘要
def summarize_csv(filepath):
    df = pd.read_csv(filepath)

    if 'summary' not in df.columns:
        raise ValueError("CSV中沒有'summary'欄位")

    # 只使用 summary 欄位的內容當作輸入
    all_text = '\n\n'.join(str(x) for x in df['summary'] if pd.notna(x))
    all_text = all_text[:MAX_CHARS]  # 若內容太長則截斷

    messages = [{
        "role": "user",
        "content": f"：{all_text}\n\n因為原文過長的原因，以上只是會議的一部分紀錄，你必須寫好這部分的會議紀錄而且寫得很詳細，但是讓他可以無縫接上其他段會議紀錄，所以請用markdown 格式來寫不要標數字．以上附件不許遺漏任何與會議有關的細節，只准許改寫語句讓其更符合會議報告的寫法但不許改寫語意 尤其是人事時地物、金錢、費用等都要寫出來。"
    }]

    summary = ai_response(messages)
    return summary



def process_all_csvs_to_md(folder_path):
    md_lines = []
    for filename in tqdm(sorted(os.listdir(folder_path))):
        if filename.endswith(".csv"):
            filepath = os.path.join(folder_path, filename)
            try:
                summary = summarize_csv(filepath)
                md_lines.append(summary.strip() + "\n")
            except Exception as e:
                print(f"⚠️ 處理 {filename} 時發生錯誤：{e}")
    return '\n'.join(md_lines)


if __name__ == "__main__":
    start = time.time()
    merged_md = process_all_csvs_to_md(INPUT_DIR)

    # 只保留第一個 ## 會議紀錄摘錄，其餘刪除
    counter = count(1)  # 初始化計數器從 1 開始
    merged_md = re.sub(r'## 會議紀錄摘錄', lambda m: m.group(0) if next(counter) == 1 else '', merged_md)

    output_path = "merged_summaries.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(merged_md)
    print(f"✅ 全部處理完畢，花費時間：{time.time() - start:.1f} 秒")
    print(f"📄 已輸出為 {output_path}")
