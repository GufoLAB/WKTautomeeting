#!/usr/bin/env python3
"""
pipeline_meeting_report.py

一支程式完成：
1. 從 chunks_summaries_brief_reindexed_condense_topics.csv 讀取帶有「chunk_id, summary, topic」欄位的資料
2. 依 topic 分組：
   a) 前 num_initial 條：生成初始 Markdown 報告章節
   b) 其餘按 chunk_size 條分批續寫到同一文件
3. 可設定輸出資料夾、初始筆數、續寫批次大小

用法示例：
python pipeline_meeting_report.py \
  --csv /path/to/chunks_summaries_brief_reindexed_condense_topics.csv \
  --output-dir /path/to/continuous_report \
  --num-initial 10 \
  --chunk-size 4
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

# 系統提示，可按需要調整
SYSTEM_PROMPT_INIT = """
你負責根據多條100字左右的會議摘要，
撰寫一段條列式的 Markdown 會議報告節選，
必須詳盡列出人事時地物與金錢費用等細節，
且能清晰呈現各重點。
"""

SYSTEM_PROMPT_CONT = """
你是會議紀錄續寫AI，
請結合前文提供的最後十五行內容與新的摘要：
保留並詳列所有與會細節，
以 Markdown 條列式輸出，
不添加任何額外說明文字。
"""

# 主程式
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='一支程式從 CSV 到會議報告')
    parser.add_argument('--csv',        required=True, help='Condense後CSV路徑')
    parser.add_argument('--output-dir', required=True, help='報告輸出資料夾')
    parser.add_argument('--num-initial',type=int, default=10, help='每topic生成初始報告數量')
    parser.add_argument('--chunk-size', type=int, default=4, help='續寫摘要批次大小')
    args = parser.parse_args()
#
    df = pd.read_csv(args.csv)
    os.makedirs(args.output_dir, exist_ok=True)

    for topic, group in df.groupby('cluster_name'):
        # 乾淨的檔名
        safe = re.sub(r"[^0-9A-Za-z一-鿿_-]", '_', topic)
        out_md = os.path.join(args.output_dir, f"{safe}.md")

        # 1) 初始報告
        init = group.head(args.num_initial)
        list_init = init['summary'].tolist()
        prompt_init = "以下為本主題前 {} 項摘要：\n".format(len(list_init)) + \
                      '\n'.join(f"- {s}" for s in list_init) + \
                      "\n請根據上述摘要撰寫 Markdown 條列會議報告節選。"
        msgs = [{ 'role':'system','content':SYSTEM_PROMPT_INIT },
                { 'role':'user','content':prompt_init }]
        print(f"生成初始: {out_md}")
        reply_init = ai_response(msgs)
        with open(out_md, 'w', encoding='utf-8') as f:
            f.write(reply_init)

        # 2) 續寫後續摘要
        remaining = group.iloc[args.num_initial:]
        if remaining.empty:
            continue
        for i in range(0, len(remaining), args.chunk_size):
            chunk = remaining.iloc[i:i+args.chunk_size]
            summ_lines = [f"{row['chunk_id']},{row['summary']}" for _,row in chunk.iterrows()]
            summary_text = '\n'.join(summ_lines)

            # 讀檔取最後 context
            with open(out_md, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            context = lines[-15:] if len(lines)>=15 else lines
            user_cont = ''.join(context) + \
                "\n以上是前文末十五行。\n以下為新摘要：\n" + summary_text + \
                "\n請續寫並產出完整段落。"
            msgs2 = [{ 'role':'system','content':SYSTEM_PROMPT_CONT },
                     { 'role':'user','content':user_cont }]

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

    print("全部完成，報告生成於：", args.output_dir)
