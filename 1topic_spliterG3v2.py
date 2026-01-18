#一次同時看一個片段並且給出覺得應該分割的點
#重要參數def batch_cut_by_chunk(lines, lines_per_chunk=40, stride=30, min_gap=6)60 50 6
#python topic_spliterG3v2.py /home/henry/automeeting/20250528會議通規格/0528會議通規格_shorten.txt
# 分析 chunk [0:60] 回覆：切換點：3, 4, 10, 19, 31, 35, 40, 55...
# 分析 chunk [50:110] 回覆：切換點：50, 55, 65, 78, 80, 92, 100...
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
import sys
# ========= INIT =========
# ---------------- core logic 包成函式 ----------------
def run(input_file: str) -> str:
    starttime = time.time()
    parser = argparse.ArgumentParser(description="用 GPT 將逐字稿依主題分段並輸出 md 檔")
    parser.add_argument("input_file", help="輸入逐字稿檔案（每行格式為 speakerX: 說話內容）")
    args = parser.parse_args()
    input_file = args.input_file
    MAX_TEXT_LEN = 3000
    base_name = os.path.splitext(os.path.basename(input_file))[0]  # 0609_shorten
    parent_dir = os.path.dirname(input_file)                       # /home/henry/automeeting/會議_20250609171235
    output_dir = os.path.join(parent_dir, base_name + "_topics")   # /home/henry/.../0609_shorten_topics
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

    # ========= 用 chunk 分段請 AI 偵測主題切點 =========claude
    #def batch_cut_by_chunk(lines, lines_per_chunk=60, stride=50, min_gap=10):
    def batch_cut_by_chunk(lines, lines_per_chunk=60, stride=50, min_gap=10, max_seg_len=60):
        """
        用 chunk 分段請 AI 偵測主題切點，並確保每個段落不超過 max_seg_len 行

        Args:
            lines: 逐字稿行列表
            lines_per_chunk: 每次分析的行數
            stride: 滑動步長
            min_gap: 切點間最小距離
            max_seg_len: 每個段落最大行數

        Returns:
            切點索引列表
        """
        split_indices = [0]
        idx = 0
        total_lines = len(lines)

        # 第一階段：用 AI 找出主題切點
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
    切換點之間要有適當的距離保持一個逐字稿中的主題完整性．
    請嚴格遵守，**不准輸出任何其他文字說明或換行符號**，否則視為錯誤。

    """

            messages = []
            messages.append({"role": "user", "content": prompt})
            reply = ai_response(messages).strip()
            print(f"🧪 分析 chunk [{idx}:{idx+lines_per_chunk}] 回覆：{reply[:50]}...", file=sys.stderr)

            match = re.search(r'切換點[:：]([\d,\s]+)', reply)
            if match:
                nums = match.group(1)
                new_points = [int(n.strip()) for n in nums.split(",") if n.strip().isdigit()]
                split_indices.extend(new_points)

            idx += stride

        # 第二階段：過濾過近的切點
        split_indices = sorted(set(split_indices + [len(lines)]))
        filtered = [split_indices[0]]
        for pt in split_indices[1:]:
            if pt - filtered[-1] >= min_gap:
                filtered.append(pt)

        # 第三階段：確保沒有段落超過 max_seg_len 行
        final_indices = [filtered[0]]
        for i in range(1, len(filtered)):
            start = final_indices[-1]
            end = filtered[i]
            seg_len = end - start

            # 如果段落太長，強制插入切點
            if seg_len > max_seg_len:
                # 從 start 開始，每 max_seg_len 行插入一個切點
                current = start
                while current + max_seg_len < end:
                    current += max_seg_len
                    final_indices.append(current)

            final_indices.append(end)

        return final_indices



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
    total_segments = len(segments)
    for i, segment in enumerate(tqdm(segments, desc="寫入主題段落"), 1):
        #text_block = "\n".join(segment)
        text_block = "\n".join(segment[:-1]) if i < total_segments else "\n".join(segment)
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

        print(f"✅ 寫入：{filename}", file=sys.stderr)

    print(f"\n🎉 共切出 {len(segments)} 段主題，儲存在：{output_dir}", file=sys.stderr)
    print("time cost", time.time() - starttime, file=sys.stderr)
    return output_dir

# ---------------- CLI 入口 ----------------
def main():
    p = argparse.ArgumentParser(description="用 GPT 將逐字稿依主題分段並輸出 md 檔")
    p.add_argument("input_file", help="輸入逐字稿檔案（每行格式為 speakerX: 內容）")
    args = p.parse_args()

    out_dir = run(args.input_file)
    print(out_dir)             # ★ stdout 僅剩這一行

if __name__ == "__main__":
    main()