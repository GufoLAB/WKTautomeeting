#python Report_generation.py /home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2/chunks_summaries_brief_output/chunks_summaries_brief_reindexed.csv
import time
import pandas as pd
import os
import re
from dotenv import load_dotenv
from tqdm import tqdm
import ollama
import sys
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL
ST=time.time()
# 載入環境變數
load_dotenv()

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

# ====== 主邏輯 ======

MAX_CHARS = 8000
input_csv = sys.argv[1]
df = pd.read_csv(input_csv)

# 將所有 summary 合併為一大段文字，並加上 chunk_id 做標記
full_text = ""
for idx, row in df.iterrows():
    chunk_id = str(row["chunk_id"]).zfill(3)
    summary = str(row["summary"]).strip()
    full_text += f"【第 {chunk_id} 段】\n{summary}\n\n"

# 分段處理如果太長
parts = []
#if len(full_text) <= MAX_CHARS:
if len(full_text) <= 2000:
    parts = [full_text]
else:
    half = len(full_text) // 2
    part1, part2 = full_text[:half], full_text[half:]
    if len(part1) > MAX_CHARS or len(part2) > MAX_CHARS:
        raise ValueError("整份資料太長，無法在兩段內送出，請手動切段")
    parts = [part1, part2]

# 逐段呼叫模型
report_sections = []
for part in parts:
    #prompt = f"{part}\n\n請將以上多段會議重點整理成一份正式的 Markdown 格式會議報告，不要忽略任何會議重點："
    prompt = f"""{part}
請將以上多段會議重點整理成一份正式的 Markdown 格式會議報告：
- 請標示出每個主題（使用 `### 主題：` 開頭）
- 每個主題下列出數個重點
- 不能遺漏或縮寫任何會議中的要點，尤其是人事時地物
- 不要用數字或任何東西標示主題順序

"""
    messages = [{"role": "user", "content": prompt}]
    try:
        response = ai_response(messages)
    except Exception as e:
        response = f"Error: {str(e)}"
    report_sections.append(response)

# 合併所有模型回覆
final_report = "\n\n--- 分段總結 ---\n\n".join(report_sections)

# 輸出單一 .md 檔案
output_file = os.path.join(os.path.dirname(input_csv), os.path.splitext(os.path.basename(input_csv))[0] + "_總結報告.md")

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(final_report)
ET=time.time()-ST
print(f"用時:{ET:2f}")
print(f"✅ 會議報告已輸出：{output_file}")
