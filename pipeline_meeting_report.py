#!/usr/bin/env python3
"""
pipeline_meeting_report.py (V2.1 - 可切換報告風格)

一支程式完成：
1. 從 chunks_summaries_brief_reindexed_condense_topics.csv 讀取帶有「chunk_id, summary, topic」欄位的資料
2. 依 topic 分組：
   a) 前 num_initial 條：生成初始 Markdown 報告章節
   b) 其餘按 chunk_size 條分批續寫到同一文件
3. 可設定輸出資料夾、初始筆數、續寫批次大小
4. V2.1 新增：可切換 4 種報告風格（財務稽核、決策流程、完整記錄、執行摘要）

用法示例：
# 完整記錄版（預設）
python pipeline_meeting_report.py \
  --csv /path/to/chunks_summaries_brief_reindexed_condense_topics.csv \
  --output /path/to/continuous_report \
  --num-initial 3 \
  --chunk-size 2

# 財務稽核版（無情的會計稽核員）
python pipeline_meeting_report.py \
  --csv /path/to/data.csv \
  --output /path/to/output \
  --style financial_audit

# 決策流程版（追蹤誰決定什麼、為什麼）
python pipeline_meeting_report.py \
  --csv /path/to/data.csv \
  --style decision_focused

# 執行摘要版（CEO 專用，<3 分鐘閱讀）
python pipeline_meeting_report.py \
  --csv /path/to/data.csv \
  --style executive_summary
"""
import argparse
import os
import re
import pandas as pd
import threading
import time
from dotenv import load_dotenv
import ollama
from zhconv_rs import zhconv
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL

# V2 新增：導入 Prompt 模板系統
from prompt_templates import PromptTemplates, ReportStyle

# ============ V2 新增：智能文本截取函數 ============
def smart_truncate(text, max_len=300):
    """智能截取文本，優先保留數字、人名、關鍵詞周圍的句子"""
    if len(text) <= max_len:
        return text

    # 關鍵模式：數字、人名、金額、日期
    import re

    # 找出所有包含關鍵信息的句子
    sentences = re.split(r'[。\n]', text)
    important_sentences = []

    for sent in sentences:
        # 包含數字、金額、人名、日期的句子視為重要
        if re.search(r'\d+|萬|億|元|月|日|\([^)]+\)', sent):
            important_sentences.append(sent)

    # 拼接重要句子直到接近 max_len
    result = ""
    for sent in important_sentences:
        if len(result) + len(sent) <= max_len:
            result += sent + "。"
        else:
            break

    # 如果還是太長，直接截斷
    if len(result) > max_len:
        result = result[:max_len] + "..."

    return result.strip()

def extract_structured_info(text, summary):
    """從 text 和 summary 中提取結構化信息"""
    import re

    # 提取金額
    amounts = re.findall(r'\d+\.?\d*\s*[萬億千百]?\s*元?', text + summary)
    amounts = list(set(amounts))[:5]  # 最多5個，去重

    # 提取人名（中英文格式）
    names = re.findall(r'[\u4e00-\u9fff]+\s*\([A-Za-z\s]+\)', text + summary)
    names = list(set(names))[:3]  # 最多3個

    # 提取日期
    dates = re.findall(r'\d+月\d+[日號]?', text + summary)
    dates = list(set(dates))[:3]

    return {
        '金額': amounts if amounts else ['無'],
        '人名': names if names else ['無'],
        '日期': dates if dates else ['無']
    }

# 顯示進度點
def print_dot(stop_event):
    while not stop_event.is_set():
        print('.', end='', flush=True)
        time.sleep(0.8)

# 與 AI 互動
def ai_response(messages, max_tokens=1000):
    if BACK_END_MODEL == 'openai':
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            max_tokens=max_tokens
        )
        text = resp.choices[0].message.content
    else:
        client = ollama.Client(host=OLLAMA_URL)
        resp = client.chat(
            model=AI_MODEL,
            messages=messages
        )
        text = resp['message']['content']
    if AI_MODEL.startswith('deepseek'):  # 移除 <think>
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return zhconv(text.strip(), 'zh-tw')

# ============ V2.1 動態 Prompt 系統 ============
# System Prompts 現在由 prompt_templates.py 動態提供
# 支援 4 種風格：財務稽核版、決策流程版、完整記錄版、執行摘要版

# 主程式
if __name__ == '__main__':
    start_time=time.time()
    parser = argparse.ArgumentParser(description='一支程式從 CSV 到會議報告')
    parser.add_argument('--csv',        required=True, help='Condense後CSV路徑')
    parser.add_argument('--output', required=False, help='報告輸出資料夾（預設為CSV所在目錄的上一層）')
    # ⚠️ V2 優化：減少批次大小以適應 Gemma3 2000字窗口 + 三層資訊架構
    parser.add_argument('--num-initial',type=int, default=3, help='每topic生成初始報告數量（V2: 10→3）')
    parser.add_argument('--chunk-size', type=int, default=2, help='續寫摘要批次大小（V2: 4→2）')
    # V2.1 新增：可切換報告風格
    parser.add_argument('--style',
                        choices=['financial_audit', 'decision_focused', 'comprehensive', 'executive_summary'],
                        default='comprehensive',
                        help='報告風格：financial_audit (財務稽核版), decision_focused (決策流程版), comprehensive (完整記錄版), executive_summary (執行摘要版)')
    args = parser.parse_args()
#
    # V2.1：初始化 Prompt 模板系統
    style = ReportStyle(args.style)
    templates = PromptTemplates(style=style)
    print(f"✅ 使用報告風格：{templates.get_style_description()}")

    # 動態獲取 System Prompts
    SYSTEM_PROMPT_INIT = templates.get_system_prompt_init()
    SYSTEM_PROMPT_CONT = templates.get_system_prompt_continue()

    # 如果沒有指定輸出路徑，預設使用CSV檔案所在目錄的上兩層
    if args.output is None:
        csv_dir = os.path.dirname(os.path.abspath(args.csv))
        csv_dir = os.path.dirname(csv_dir)
        args.output = os.path.dirname(csv_dir)
        print(f"預設輸出路徑，預設使用CSV檔案所在目錄的上兩層：{args.output}")
    df = pd.read_csv(args.csv)
    os.makedirs(args.output, exist_ok=True)

    for topic, group in df.groupby('cluster_name'):
        # 乾淨的檔名
        safe = re.sub(r"[^0-9A-Za-z一-鿿_-]", '_', topic)
        out_md = os.path.join(args.output, f"{safe}.md")

        # 1) 初始報告 - V2 三層資訊架構
        init = group.head(args.num_initial)

        # 構建三層資訊 prompt
        prompt_init = f"本主題的會議片段（共 {len(init)} 個）：\n\n"

        for idx, row in init.iterrows():
            chunk_id = row['chunk_id']
            summary = row['summary']
            text = row.get('text', '')  # V2 新增：讀取 text

            # Layer 1: Summary
            prompt_init += f"### 片段 [{chunk_id}]\n\n"
            prompt_init += f"**【摘要】**: {summary}\n\n"

            # Layer 2: Structured Info
            if text:
                info = extract_structured_info(text, summary)
                prompt_init += "**【結構化資訊】**:\n"
                prompt_init += f"- 金額: {', '.join(info['金額'])}\n"
                prompt_init += f"- 人員: {', '.join(info['人名'])}\n"
                prompt_init += f"- 日期: {', '.join(info['日期'])}\n\n"

                # Layer 3: Text Snippet
                text_snippet = smart_truncate(text, max_len=300)
                prompt_init += f"**【原文參考】**: {text_snippet}\n\n"

        # ⚠️ Gemma3 特性：指令放在內容之後！
        prompt_init += "=" * 50 + "\n"
        prompt_init += SYSTEM_PROMPT_INIT + "\n\n"
        prompt_init += "請立即根據上述所有片段，撰寫 Markdown 格式的專業會議報告：\n"

        # 使用 user role（不需要 system，因為指令已在內容中）
        msgs = [{ 'role':'user','content':prompt_init }]
        print(f"生成初始: {out_md} (使用 {len(init)} 個片段，三層資訊架構)")
        reply_init = ai_response(msgs)
        with open(out_md, 'w', encoding='utf-8') as f:
            f.write(reply_init)

        # 2) 續寫後續摘要 - V2 三層資訊架構
        remaining = group.iloc[args.num_initial:]
        if remaining.empty:
            continue
        for i in range(0, len(remaining), args.chunk_size):
            chunk = remaining.iloc[i:i+args.chunk_size]

            # 讀檔取最後 context
            with open(out_md, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            context = lines[-15:] if len(lines)>=15 else lines

            # 構建續寫 prompt（三層資訊）
            user_cont = "【前文最後15行】：\n"
            user_cont += ''.join(context)
            user_cont += "\n" + "=" * 50 + "\n\n"
            user_cont += "【新的會議片段】：\n\n"

            for idx, row in chunk.iterrows():
                chunk_id = row['chunk_id']
                summary = row['summary']
                text = row.get('text', '')

                # Layer 1: Summary
                user_cont += f"### 片段 [{chunk_id}]\n\n"
                user_cont += f"**【摘要】**: {summary}\n\n"

                # Layer 2 & 3
                if text:
                    info = extract_structured_info(text, summary)
                    user_cont += "**【結構化資訊】**: "
                    user_cont += f"金額 {', '.join(info['金額'][:2])}; "  # 最多2個
                    user_cont += f"人員 {', '.join(info['人名'][:2])}\n\n"

                    text_snippet = smart_truncate(text, max_len=200)  # 續寫用較短的 snippet
                    user_cont += f"**【原文參考】**: {text_snippet}\n\n"

            # ⚠️ Gemma3 特性：指令放在最後！
            user_cont += "=" * 50 + "\n"
            user_cont += SYSTEM_PROMPT_CONT + "\n\n"
            user_cont += "請立即無縫續寫報告：\n"

            msgs2 = [{ 'role':'user','content':user_cont }]

            # 顯示進度點
            stop = threading.Event(); t = threading.Thread(target=print_dot,args=(stop,)); t.start()
            try:
                reply2 = ai_response(msgs2)
            finally:
                stop.set(); t.join()

            # 合併並覆寫
            if len(lines)>=15:
                new_content = lines[:-15] + [ln+'\n' for ln in reply2.splitlines()]
            else:
                new_content = [ln+'\n' for ln in reply2.splitlines()]
            with open(out_md, 'w', encoding='utf-8') as f:
                f.writelines(new_content)
            print(f"  已續寫 items {i+1}-{i+len(chunk)} 到 {out_md}")

    print("全部完成，報告生成於：", args.output)
    print(time.time()-start_time,"sec")