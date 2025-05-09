import os
import re
import argparse
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

# 初始化 GPT client
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 參數設定
parser = argparse.ArgumentParser(description="用 GPT 將逐字稿依主題分段並輸出 md 檔")
parser.add_argument("input_file", help="輸入逐字稿檔案（每行格式為 speakerX: 說話內容）")
args = parser.parse_args()

input_file = args.input_file
MAX_TEXT_LEN = 3000
#有分兩個ＡＩ一個切斷一個寫結論 可以search model修改
#model_choice="gpt-3.5-turbo" 
model_choice="gpt-4o"


# 輸出資料夾
output_dir = os.path.splitext(os.path.basename(input_file))[0] + "_topics"
os.makedirs(output_dir, exist_ok=True)


# 讀入逐字稿
with open(input_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

# 🔁 主題生長式切段
start = 0
topic_indices = [0]
step = 4
initial_len = 6

while start < len(lines):
    cur_len = initial_len
    while start + cur_len < len(lines):
        block = "\n".join(lines[start:start+cur_len])
        prompt = f"""以下是一段逐字稿段落。請判斷這段是否仍在描述同一個討論主題。
如果仍是同一主題請回傳 True，若已經包含新主題則請回傳 False：
---
{block}
---
回答："""

        res = client.chat.completions.create(
            model=model_choice,
            messages=[{"role": "user", "content": prompt}]
        )
        reply = res.choices[0].message.content.strip().lower()
        if "false" in reply:
            break
        cur_len += step

    start += cur_len
    topic_indices.append(start)

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

    summary_prompt = f"""請寫出這一段最重要的事情，一字不漏，不要加標點或解釋：
---
{summary_input}
---
主題："""

    summary_res = client.chat.completions.create(
        model=model_choice,
        messages=[{"role": "user", "content": summary_prompt}]
    )
    topic_title = summary_res.choices[0].message.content.strip()
    filename_title = sanitize_filename(topic_title)
    filename = f"{i:02d}_{filename_title}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {topic_title}\n\n")
        f.write(text_block)

    print(f"✅ 寫入：{filename}")

print(f"\n🎉 共切出 {len(segments)} 段主題，儲存在：{output_dir}")
