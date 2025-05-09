#這是一個逐句閱讀文章每次新增幾個原文中的幾行讓ＡＩ回傳true or false來建立分段程式
import os
import re
import argparse
import time
from dotenv import load_dotenv
from tqdm import tqdm
starttime=time.time()
# 參數設定
parser = argparse.ArgumentParser(description="用 GPT 將逐字稿依主題分段並輸出 md 檔")
parser.add_argument("input_file", help="輸入逐字稿檔案（每行格式為 speakerX: 說話內容）")
args = parser.parse_args()

input_file = args.input_file
MAX_TEXT_LEN = 3000
#有分兩個ＡＩ一個切斷一個寫結論 可以search model修改


# 輸出資料夾
output_dir = os.path.splitext(os.path.basename(input_file))[0] + "_topics"
os.makedirs(output_dir, exist_ok=True)


# 讀入逐字稿
with open(input_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

# 🔁 主題生長式切段
start = 0
topic_indices = [0]
step = 3
initial_len = 4
# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------


import os, re
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import ollama
from zhconv_rs import zhconv

from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# 設定 統一system prompt，並動態記錄版本資訊
#import system_prompt
#global prompt_choice, prompt_version
#prompt_function = system_prompt.system_prompt  # 取得 system_prompt 函式
#prompt_choice = prompt_function()  # 執行函式以取得提示內容
#prompt_version = f"{prompt_function.__module__}.{prompt_function.__name__}"


def ai_response(conversation_history, max_tokens=1000):
    if BACK_END_MODEL == 'openai':
        response = openai_client.chat.completions.create(
            model=AI_MODEL, 
            messages=conversation_history
        )
        print("model = openai")
        assistant_reply = response.choices[0].message.content
    elif BACK_END_MODEL == 'ollama':
        response = ollama.Client(host=OLLAMA_URL).chat(
            model=AI_MODEL, 
            messages=conversation_history
        )
        print("model = ollama "+str(AI_MODEL))
        assistant_reply = response['message']['content'].strip()
        if AI_MODEL.startswith("deepseek"):
            assistant_reply = re.sub(r'<think>(.*)</think>', '', assistant_reply, flags=re.DOTALL).strip()
    assistant_reply = zhconv(assistant_reply, "zh-tw")
    return assistant_reply
# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------


while start < len(lines):
    cur_len = initial_len
    while start + cur_len < len(lines):
        block = "\n".join(lines[start:start+cur_len])
        prompt = f"""以下是一段逐字稿段落。請判斷這段是否只有描述一個討論主題。
如果討論內容都是同一個主題請回傳 True．若討論內容包含多個主題，則請回傳 False：
---
{block}
---
輸出只有True or False兩種，其他文字都不需要："""

        messages = [{"role": "user", "content": prompt}]
        print(f"\n⏳ 檢查段落 [{start}:{start+cur_len}]")
        reply = ai_response(messages, max_tokens=1000).strip().lower()
        print(f"🔍 回覆：{reply}")

        if "false" in reply or cur_len >= 20:
            break
        cur_len += step

    # 安全保障：萬一模型太快回 false，至少切下一段，不卡死
    if cur_len == initial_len:
        print("⚠️ 模型提早回 False，強制切出一小段")
        cur_len = step

    start += cur_len
    topic_indices.append(start)
    print(f"✅ 新切點：{start}")


# ✅ 根據切點切段，加入上下文 padding
padding = 2
topic_indices = sorted(set(topic_indices))
segments = []

for i in range(len(topic_indices)):
    seg_start = topic_indices[i]
    seg_end = topic_indices[i+1] if i+1 < len(topic_indices) else len(lines)

    real_start = max(0, seg_start - padding)
    real_end = min(len(lines), seg_end + padding)
    segments.append(lines[real_start:real_end])

# 🔖 清理錯誤字元
def sanitize_filename(text):
    # 移除所有不合法檔名字元
    text = re.sub(r'[\\/*?:"<>|（）()【】「」、，。！？~`\'\s]+', '_', text)
    # 僅保留中英文與數字（避免 emoji）
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
    # 限制長度
    return text[:20].strip("_")

# 📝 寫入每段＋主題摘要
for i, segment in enumerate(tqdm(segments, desc="寫入主題段落"), 1):
    text_block = "\n".join(segment)
    summary_input = text_block[:MAX_TEXT_LEN]

    summary_prompt = f"""請寫出這一段最重要的事情，不要加標點或解釋：
---
{summary_input}
---
主題："""


    messages=[{"role": "user", "content": summary_prompt}]
    
    topic_title = ai_response(messages, max_tokens=1000)
    filename_title = sanitize_filename(topic_title)
    filename = f"{i:02d}_{filename_title}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {topic_title}\n\n")
        f.write(text_block)

    print(f"✅ 寫入：{filename}")

print(f"\n🎉 共切出 {len(segments)} 段主題，儲存在：{output_dir}")
Endtime=time.time()
print("time cost",Endtime-starttime)