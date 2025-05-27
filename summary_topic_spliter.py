"""
這個程式的功能是：
1. 讀取一個含有摘要欄位的 CSV 檔案。
2. 每 8 行摘要為一組，使用 GPT 模型找出主題轉換的「切換點」行號。
3. 根據切換點將資料切段，每段另存成一個 CSV 檔。
4. 每段內容送給 GPT 生出一個十字以內的主題標題，作為檔名。
5. 最終將所有切段存入一個新建立的資料夾中。

輸入：
- CSV 檔案路徑（需含有 `summary` 欄位）

輸出：
- 一個名為 `<原始檔案名>_topic_blocks/` 的資料夾
- 內含數個以主題命名的 `.csv` 檔案，每檔代表一段主題區塊

執行方式（範例）：
    python split_topics.py my_summary.csv
"""
import os
import re
import argparse
import time
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from zhconv_rs import zhconv
import ollama
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL
from openai import OpenAI

# ========= INIT =========
starttime = time.time()
parser = argparse.ArgumentParser(description="用 GPT 分析 CSV 摘要列表的主題轉換點")
parser.add_argument("input_file", help="輸入 CSV 檔案（欄位需包含 summary）")
args = parser.parse_args()

input_file = args.input_file  # 🔸這一行不能少！
input_dir = os.path.dirname(input_file)
output_dir = os.path.join(input_dir, os.path.splitext(os.path.basename(input_file))[0] + "_topic_blocks")
os.makedirs(output_dir, exist_ok=True)

# ========= AI 初始化 =========
load_dotenv()
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def ai_response(conversation_history, max_tokens=1000):
    if BACK_END_MODEL == 'openai':
        response = openai_client.chat.completions.create(
            model=AI_MODEL,
            messages=conversation_history
        )
        assistant_reply = response.choices[0].message.content
    elif BACK_END_MODEL == 'ollama':
        response = ollama.Client(host=OLLAMA_URL).chat(
            model=AI_MODEL,
            messages=conversation_history
        )
        assistant_reply = response['message']['content'].strip()
        if AI_MODEL.startswith("deepseek"):
            assistant_reply = re.sub(r'<think>(.*)</think>', '', assistant_reply, flags=re.DOTALL).strip()
    assistant_reply = zhconv(assistant_reply, "zh-tw")
    return assistant_reply

# ========= 讀入 CSV =========
df = pd.read_csv(input_file)
summaries = df['summary'].tolist()

def detect_topic_transitions(summaries, block_size=8, min_block_len=4):
    """
    根據逐段摘要，用 GPT 模型找出主題切換點，回傳切段 index 清單。
    每次從上一個切點開始向下分析，不重複、不遺漏。
    """
    split_points = []
    current_index = 0

    while current_index < len(summaries):
        sub = summaries[current_index:current_index + block_size]
        if not sub:
            break

        # 準備 prompt，從 1 開始標號
        prompt_lines = [f"[{current_index + j + 1}] {line}" for j, line in enumerate(sub)]
        chunk_text = "\n".join(prompt_lines)

        prompt = f"""{chunk_text}
---
請閱讀以上逐段摘要，以「主題是否明顯改變」為判準，判斷主題段落的切換位置。
若段落內容僅是敘述細節、同一討論脈絡延伸，請勿視為切換點。
僅在段落主軸明顯改變（例如從預算改談人力、從活動改談法規）時才切換，且每段落需達三句以上才可切換。

請僅輸出「切換點的行號」（即每組摘要開頭前的數字），格式如下：
切換點：4, 7
不准輸出其他文字或句點。
---
"""

        messages = [{"role": "user", "content": prompt}]
        reply = ai_response(messages)
        print(f"🧪 分析摘要段 [{current_index}–{current_index + block_size}] 回覆：{reply.strip()}")

        match = re.search(r'切換點[:：]([\d,\s]+)', reply)
        if match:
            # 將 GPT 回傳的行號轉為 summaries 中的 index（1-based → 0-based）
            raw_nums = match.group(1)
            raw_points = [int(n.strip()) for n in raw_nums.split(",") if n.strip().isdigit()]
            adjusted_points = [current_index + (p - 1) for p in raw_points if 1 <= p <= len(sub)]
            print(f"👉 切點 index: {adjusted_points}")

            # 過濾：與前段距離至少 min_block_len 行
            valid_points = []
            prev = current_index
            for p in sorted(adjusted_points):
                if p - prev >= min_block_len:
                    valid_points.append(p)
                    prev = p

            if valid_points:
                # 取第一個有效切點作為下一段開始
                split_points.append(valid_points[0])
                current_index = valid_points[0]
            else:
                print(f"⚠️ 沒有有效切點，跳過 {current_index}～{current_index + block_size}")
                current_index += block_size
        else:
            print(f"⚠️ 無切點格式於段落 {current_index}–{current_index + block_size}，跳過")
            current_index += block_size

    # 補上最後一段結尾
    split_points.append(len(summaries))
    return sorted(set(split_points))




split_indices = detect_topic_transitions(summaries)

# ========= 切段並寫出每段 =========
blocks = []
for idx, (start_idx, end_idx) in enumerate(zip([0] + split_indices[:-1], split_indices)):
    sub_df = df.iloc[start_idx:end_idx].copy()
    blocks.append(sub_df)

    # 合併內容摘要並產生主題
    combined_text = "\n".join(sub_df['summary'].tolist())[:3000]
    topic_prompt = f"""{combined_text}
---
請為以上內容摘要出**十個字以內的主題名稱**（不要加標點、不要多餘解釋）：
主題：
"""
    messages = [{"role": "user", "content": topic_prompt}]
    topic_title = ai_response(messages).strip()

    # 清理標題成檔名用
    filename_title = re.sub(r'[\\/*?:"<>|（）()【】「」、，。！？~`\'\s]+', '_', topic_title)
    filename_title = re.sub(r'[^\w\u4e00-\u9fff]', '', filename_title)[:20].strip('_')

    filename = f"{str(idx+1).zfill(2)}_{filename_title}.csv"
    sub_df.to_csv(os.path.join(output_dir, filename), index=False)
    print(f"✅ 寫入：{filename}")

print(f"\n🎉 共切出 {len(blocks)} 段主題，儲存在：{output_dir}")