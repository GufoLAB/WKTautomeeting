#!/usr/bin/env python3
"""
7timeline_continuous_writing.py - 按时间顺序续写会议记录

从 CSV 读取 chunks，按 chunk_id 顺序（时间顺序）使用 continuous writing 生成完整会议记录

用法：
python 7timeline_continuous_writing.py --csv /path/to/chunks_summaries_brief.csv --output timeline_report.md
"""

import argparse
import os
import re
import time
import threading
import pandas as pd
from pathlib import Path
import ollama
from zhconv_rs import zhconv
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL


# ==================== 工具函数 ====================

def print_dot(stop_event):
    """显示进度点"""
    while not stop_event.is_set():
        print('.', end='', flush=True)
        time.sleep(0.8)


def ai_response(messages, max_tokens=2000):
    """调用 AI 模型"""
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

    # 移除 deepseek 的 <think> 标签
    if AI_MODEL.startswith('deepseek'):
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    return zhconv(text.strip(), 'zh-tw')


# ==================== Prompt 设计 ====================

SYSTEM_PROMPT_INIT = """你是專業的會議記錄撰寫專家。

請根據第一段會議摘要，撰寫會議記錄的開頭部分。

要求：
1. 提取會議基本信息（日期、與會者、時長）
2. 使用正式的會議記錄格式
3. 詳細列出重點內容
4. 使用 Markdown 格式
5. 不要添加原文沒有的內容

直接輸出內容，不需要其他說明。
"""


SYSTEM_PROMPT_CONTINUE = """你是專業的會議記錄續寫專家。

我會給你：
1. 前文的最後 15 行
2. 新的會議片段摘要
3. 當前 chunk 編號

請自然地續寫會議記錄：
- 保持所有重要細節（人事時地物、金額、時程等）
- 自然的段落銜接
- 可以適當修改最後 15 行使銜接更流暢
- 使用 Markdown 格式
- 不要添加多餘的說明文字

請輸出整合後的最終內容（包含修改後的前文末段 + 新內容）。
"""


# ==================== 核心功能 ====================

def initialize_report(first_chunk: dict, output_path: Path):
    """初始化会议记录"""
    print(f"\n🔄 初始化會議記錄")
    print(f"  📄 使用第一個 chunk: {first_chunk['chunk_id']}")

    user_prompt = f"""這是會議的第一段內容：

{first_chunk['summary']}

請撰寫會議記錄的開頭部分。"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_INIT},
        {"role": "user", "content": user_prompt}
    ]

    # AI 处理
    print(f"  🤖 AI 正在處理", end='')
    stop_event = threading.Event()
    dot_thread = threading.Thread(target=print_dot, args=(stop_event,))
    dot_thread.start()

    try:
        initial_content = ai_response(messages, max_tokens=2000)
    finally:
        stop_event.set()
        dot_thread.join()

    print(f" ✅")

    # 添加报告头部
    final_content = f"""# 會議記錄（按時間順序）

---

{initial_content}
"""

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"  💾 初始記錄已建立")


def integrate_next_chunk(output_path: Path, chunk: dict, chunk_index: int, total_chunks: int):
    """整合下一个 chunk"""
    print(f"\n🔄 整合 Chunk {chunk_index}/{total_chunks}")
    print(f"  📄 {chunk['chunk_id']}")

    # 读取当前报告的最后 15 行
    with open(output_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    last_15_lines = ''.join(lines[-15:] if len(lines) >= 15 else lines)

    # 检查字数
    summary_text = chunk['summary']
    total_chars = len(last_15_lines) + len(summary_text)
    print(f"  📊 輸入字數：前文 {len(last_15_lines)} + 新內容 {len(summary_text)} = {total_chars} 字")

    if total_chars > 4000:
        print(f"  ⚠️  警告：總字數超過 4000，可能影響處理效果")

    # 构建 prompt
    user_prompt = f"""前文最後 15 行：

{last_15_lines}

---

新的會議片段（chunk {chunk_index}）：

{summary_text}

---

請自然地將新內容接續到前文，輸出完整的最終內容。"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CONTINUE},
        {"role": "user", "content": user_prompt}
    ]

    # AI 处理
    print(f"  🤖 AI 正在整合", end='')
    stop_event = threading.Event()
    dot_thread = threading.Thread(target=print_dot, args=(stop_event,))
    dot_thread.start()

    try:
        merged_content = ai_response(messages, max_tokens=2000)
    finally:
        stop_event.set()
        dot_thread.join()

    print(f" ✅")

    # 更新文件：替换最后 15 行
    if len(lines) >= 15:
        new_lines = lines[:-15] + [merged_content + '\n']
    else:
        new_lines = [merged_content + '\n']

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"  💾 已更新記錄")

    # 每 10 个 chunks 保存一次备份
    if chunk_index % 10 == 0:
        backup_path = output_path.parent / f"{output_path.stem}_backup_{chunk_index}.md"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"  💾 已保存備份：{backup_path.name}")


def timeline_continuous_write(csv_file: Path, output_path: Path):
    """主流程：按时间顺序续写"""

    print("="*60)
    print("🚀 開始按時間順序續寫會議記錄")
    print("="*60)

    # 读取 CSV
    df = pd.read_csv(csv_file)
    total_chunks = len(df)

    print(f"📊 總共 {total_chunks} 個 chunks")
    print(f"📄 輸出：{output_path}")

    # 步骤 1：初始化
    first_chunk = df.iloc[0].to_dict()
    initialize_report(first_chunk, output_path)

    # 步骤 2：逐个整合
    for i in range(1, total_chunks):
        chunk = df.iloc[i].to_dict()
        integrate_next_chunk(output_path, chunk, i+1, total_chunks)

    print("\n" + "="*60)
    print("✅ 時間線會議記錄生成完成！")
    print("="*60)

    # 显示统计
    with open(output_path, 'r', encoding='utf-8') as f:
        final_lines = f.readlines()

    file_size = output_path.stat().st_size / 1024
    print(f"📄 最終報告：{output_path}")
    print(f"📊 總行數：{len(final_lines)}")
    print(f"📦 檔案大小：{file_size:.1f} KB")


# ==================== 主程序 ====================

def main():
    parser = argparse.ArgumentParser(
        description='按時間順序續寫會議記錄'
    )

    parser.add_argument('--csv', required=True,
                       help='chunks_summaries_brief.csv 文件路径')
    parser.add_argument('--output', default='timeline_report.md',
                       help='输出文件路径')

    args = parser.parse_args()

    start_time = time.time()

    # 检查输入文件
    csv_file = Path(args.csv)
    if not csv_file.exists():
        print(f"❌ CSV 文件不存在：{csv_file}")
        return

    # 确定输出路径
    if args.output == 'timeline_report.md':
        output_path = csv_file.parent.parent / args.output
    else:
        output_path = Path(args.output)

    # 执行续写
    timeline_continuous_write(csv_file, output_path)

    # 总结
    elapsed = time.time() - start_time
    print(f"\n⏱️  總耗時：{elapsed:.1f} 秒 ({elapsed/60:.1f} 分鐘)")


if __name__ == '__main__':
    main()
