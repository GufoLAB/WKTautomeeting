#一次同時看一個片段並且給出覺得應該分割的點
import os
import re
import argparse
import time
from dotenv import load_dotenv
from tqdm import tqdm
from zhconv_rs import zhconv
import ollama
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL
from openai import OpenAI

# ========= INIT =========
starttime = time.time()
parser = argparse.ArgumentParser(description="用 GPT 將逐字稿依主題分段並輸出 md 檔")
parser.add_argument("input_file", help="輸入逐字稿檔案（每行格式為 speakerX: 說話內容）")
args = parser.parse_args()
input_file = args.input_file
MAX_TEXT_LEN = 3000
output_dir = os.path.splitext(os.path.basename(input_file))[0] + "_topics"
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

# ========= 讀入逐字稿 =========
with open(input_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

# ========= 用 chunk 分段請 AI 偵測主題切點 =========
def batch_cut_by_chunk(lines, lines_per_chunk=60, stride=50, min_gap=6):
    split_indices = [0]
    idx = 0
    total_lines = len(lines)

    while idx < total_lines:
        chunk_lines = lines[idx:idx+lines_per_chunk]
        numbered_chunk = [f"[{i+idx}] {line}" for i, line in enumerate(chunk_lines)]
        chunk_text = "\n".join(numbered_chunk)

        prompt = f"""

---
{chunk_text}
---
請閱讀以上逐字稿，找出明顯的主題段落切換的位置。
請僅輸出「切換點的行號」（即中括號內的原始行號），格式必須符合：
切換點：12, 102

請嚴格遵守，**不准輸出任何其他文字說明**，否則視為錯誤。

"""
#        messages = [
#    {
#        "role": "user",
#        "content": "請閱讀以下逐字稿，找出明顯的主題段落切換的位置。\n請僅輸出「切換點的行號」（即中括號內的原始行號）格式要可以被r'切換點[:：]([\\d,\\s]+)'讀取，輸出格式嚴格遵守以下："
#    },
#    {
#        "role": "assistant",
#        "content": "切換點：12, 102 這是一段博物館或類似機構內部會議的錄音紀錄，討論了預算緊縮和未來計畫。以下是內容的摘要和分析："
#    },
#    {
#        "role": "user",
#        "content": "我說過不准輸出其他文字"
#    },
#    {
#        "role": "assistant",
#        "content": "切換點：45, 182,219"
#    },
#    {
#        "role": "user",
#        "content": "很好繼續維持這樣的輸出"
#    }
#]
        messages=[]
        messages.append({"role": "user", "content": prompt})
        reply = ai_response(messages).strip()
        print(f"🧪 分析 chunk [{idx}:{idx+lines_per_chunk}] 回覆：{reply[:50]}...")

        match = re.search(r'切換點[:：]([\d,\s]+)', reply)
        if match:
            nums = match.group(1)
            new_points = [int(n.strip()) for n in nums.split(",") if n.strip().isdigit()]
            split_indices.extend(new_points)

        idx += stride

    # 過濾過近的切點
    split_indices = sorted(set(split_indices + [len(lines)]))
    filtered = [split_indices[0]]
    for pt in split_indices[1:]:
        if pt - filtered[-1] >= min_gap:
            filtered.append(pt)

    return filtered
split_indices = batch_cut_by_chunk(lines)
# ========= 切段並加入 padding =========
padding = 1
segments = []
for start_idx, end_idx in zip(split_indices[:-1], split_indices[1:]):
    real_start = max(0, start_idx - padding)
    real_end = end_idx  # ✅ 不加尾端 padding，避免重複
    segments.append(lines[real_start:real_end])

# ========= 檔名清理 =========
def sanitize_filename(text):
    text = re.sub(r'[\\/*?:"<>|（）()【】「」、，。！？~`\'\s]+', '_', text)
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
    return text[:20].strip("_")

# ========= 寫入 Markdown =========
for i, segment in enumerate(tqdm(segments, desc="寫入主題段落"), 1):
    text_block = "\n".join(segment)
    summary_input = text_block[:MAX_TEXT_LEN]
    summary_prompt = f"""請寫出這一段最重要的事情，不要加標點或解釋：
---
{summary_input}
---
主題："""
    messages = [{"role": "user", "content": summary_prompt}]
    topic_title = ai_response(messages, max_tokens=1000)
    filename_title = sanitize_filename(topic_title)
    filename = f"{i:02d}_{filename_title}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {topic_title}\n\n")
        f.write(text_block)

    print(f"✅ 寫入：{filename}")

print(f"\n🎉 共切出 {len(segments)} 段主題，儲存在：{output_dir}")
print("time cost", time.time() - starttime)
