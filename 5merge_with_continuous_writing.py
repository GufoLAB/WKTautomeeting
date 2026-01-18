#!/usr/bin/env python3
"""
5merge_with_continuous_writing.py - 使用 Continuous Writing 技术整合多主题 MD

这是步骤 7.4 - 使用 continuous writing 技术将多个主题 MD 自然整合成单一完整报告

特点：
- 使用类似 continuous_writing.py 的技术
- 逐个主题自然衔接
- 保留所有重要细节
- 输出流畅的专业会议记录

用法：
python 5merge_with_continuous_writing.py --input-dir /path/to/md/files --output integrated_report.md

或者接续 main_part2_test.py 的结果：
python 5merge_with_continuous_writing.py --from-judgment /path/to/topic_judgments.json --output integrated_report.md
"""

import argparse
import os
import re
import json
import time
import threading
from pathlib import Path
from typing import List, Dict
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


# ==================== Continuous Writing 整合 ====================

SYSTEM_PROMPT_INIT = """你是專業的會議記錄撰寫專家。

請根據提供的會議主題內容，撰寫一份專業的會議記錄開頭部分。

要求：
1. 使用正式的會議記錄格式
2. 詳細列出所有重要細節（人事時地物、金額、時程等）
3. 使用 Markdown 條列式格式
4. 保持客觀專業的語氣
5. 不要添加原文沒有的內容

直接輸出內容，不需要其他說明。
"""


SYSTEM_PROMPT_CONTINUE = """你是專業的會議記錄整合專家。

我會給你：
1. 前文的最後 15 行
2. 新的會議主題內容

請將新主題自然地接續到前文，要求：
1. **保持所有重要細節**（人事時地物、金額、時程等）
2. **自然的段落銜接**（不要突兀，適當的過渡語句）
3. **統一的格式風格**（與前文保持一致）
4. **可以適當修改最後 15 行**，使銜接更流暢
5. 使用 Markdown 格式
6. 不要添加多餘的說明文字

直接輸出整合後的最終內容（包含修改後的前文末段 + 新內容）。
"""


def initialize_report(first_file: Path, output_path: Path, total_topics: int):
    """
    初始化报告 - 使用第一个主题
    """
    print(f"\n🔄 初始化報告")
    print(f"  📄 使用第一個主題：{first_file.name}")

    # 读取第一个主题
    with open(first_file, 'r', encoding='utf-8') as f:
        first_content = f.read().strip()

    # 构建 prompt
    user_prompt = f"""這是會議的第一個主題（共 {total_topics} 個主題）：

{first_content}

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
    final_content = f"""# 完整會議記錄

**會議主題數：** {total_topics}

---

{initial_content}
"""

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"  💾 初始報告已建立")


def integrate_next_topic(output_path: Path, next_file: Path, topic_index: int, total_topics: int):
    """
    整合下一个主题 - 使用 continuous writing 技术
    """
    print(f"\n🔄 整合主題 {topic_index}/{total_topics}")
    print(f"  📄 {next_file.name}")

    # 读取当前报告的最后 15 行
    with open(output_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    last_15_lines = ''.join(lines[-15:] if len(lines) >= 15 else lines)

    # 读取新主题内容
    with open(next_file, 'r', encoding='utf-8') as f:
        next_content = f.read().strip()

    # 检查字数
    total_chars = len(last_15_lines) + len(next_content)
    print(f"  📊 輸入字數：前文 {len(last_15_lines)} + 新內容 {len(next_content)} = {total_chars} 字")

    if total_chars > 4000:
        print(f"  ⚠️  警告：總字數超過 4000，可能影響 Gemma3 處理效果")

    # 构建 prompt
    user_prompt = f"""前文最後 15 行：

{last_15_lines}

---

新的會議主題：

{next_content}

---

請自然地將新主題接續到前文，輸出完整的最終內容。"""

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

    # 更新文件：替换最后 15 行 + 添加新内容
    if len(lines) >= 15:
        new_lines = lines[:-15] + [merged_content + '\n']
    else:
        new_lines = [merged_content + '\n']

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"  💾 已更新報告")


def continuous_merge(sorted_files: List[Path], output_path: Path):
    """
    主流程：使用 continuous writing 整合所有主题
    """
    total_topics = len(sorted_files)

    print("="*60)
    print("🚀 開始 Continuous Writing 整合")
    print("="*60)
    print(f"📊 總共 {total_topics} 個主題")
    print(f"📄 輸出：{output_path}")

    # 步骤 1：初始化（使用第一个主题）
    initialize_report(sorted_files[0], output_path, total_topics)

    # 步骤 2：逐个整合剩余主题
    for i, next_file in enumerate(sorted_files[1:], 2):
        integrate_next_topic(output_path, next_file, i, total_topics)

    print("\n" + "="*60)
    print("✅ Continuous Writing 整合完成！")
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
        description='使用 Continuous Writing 技术整合多主题 MD 文件'
    )

    # 输入方式 1：指定目录
    parser.add_argument('--input-dir', help='包含 MD 文件的目录')

    # 输入方式 2：从 judgment 结果读取
    parser.add_argument('--from-judgment', help='从 topic_judgments.json 读取已过滤的文件列表')

    # 输出
    parser.add_argument('--output', default='final_report_integrated.md',
                        help='输出文件路径')

    args = parser.parse_args()

    start_time = time.time()

    # ==================== 获取文件列表 ====================

    if args.from_judgment:
        # 方式 2：从 judgment JSON 读取
        judgment_file = Path(args.from_judgment)
        if not judgment_file.exists():
            print(f"❌ Judgment 文件不存在：{judgment_file}")
            return

        with open(judgment_file, 'r', encoding='utf-8') as f:
            judgments = json.load(f)

        # 获取保留的文件
        input_dir = judgment_file.parent
        kept_files = [
            input_dir / j['filename']
            for j in judgments if j['keep']
        ]

        print(f"📁 從 judgment 結果讀取：{judgment_file}")
        print(f"📊 保留 {len(kept_files)} 個主題")

        # 需要排序信息
        # 假设在同一目录下查找 final_report.md 中的顺序
        final_report = input_dir / 'final_report.md'
        if final_report.exists():
            with open(final_report, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取顺序
            ordered_filenames = []
            for match in re.finditer(r'## \d+\. (.+)', content):
                topic_name = match.group(1).strip()
                # 匹配文件名
                for f in kept_files:
                    if topic_name.replace(' ', '_') in f.name or \
                       topic_name.replace(' ', '') in f.name:
                        if f not in ordered_filenames:
                            ordered_filenames.append(f)
                            break

            # 添加未匹配的文件
            for f in kept_files:
                if f not in ordered_filenames:
                    ordered_filenames.append(f)

            sorted_files = ordered_filenames
        else:
            # 没有排序信息，按文件名排序
            sorted_files = sorted(kept_files, key=lambda x: x.name)

    elif args.input_dir:
        # 方式 1：从目录读取
        input_dir = Path(args.input_dir)
        if not input_dir.exists():
            print(f"❌ 目錄不存在：{input_dir}")
            return

        # 获取所有 MD 文件（排除系统文件）
        all_md_files = list(input_dir.glob('*.md'))
        exclude_keywords = ['CLAUDE', 'README', 'PATENT', 'cleaned', 'final', 'integrated']

        md_files = [
            f for f in all_md_files
            if not any(exc in f.name for exc in exclude_keywords)
        ]

        if not md_files:
            print(f"❌ 在 {input_dir} 中未找到 MD 文件")
            return

        # 按文件名排序（简单方式）
        sorted_files = sorted(md_files, key=lambda x: x.name)

        print(f"📁 輸入目錄：{input_dir}")
        print(f"📄 找到 {len(sorted_files)} 個 MD 文件")

    else:
        print("❌ 請指定 --input-dir 或 --from-judgment")
        return

    # 显示文件列表
    print(f"\n📝 處理順序：")
    for i, f in enumerate(sorted_files, 1):
        size_kb = f.stat().st_size / 1024
        print(f"  {i}. {f.name} ({size_kb:.1f} KB)")

    # ==================== 确定输出路径 ====================

    if args.output == 'final_report_integrated.md':
        # 默认输出到 input_dir
        if args.from_judgment:
            output_path = judgment_file.parent / args.output
        else:
            output_path = input_dir / args.output
    else:
        output_path = Path(args.output)

    # ==================== 执行整合 ====================

    continuous_merge(sorted_files, output_path)

    # ==================== 总结 ====================

    elapsed = time.time() - start_time
    print(f"\n⏱️  總耗時：{elapsed:.1f} 秒")
    print(f"\n💡 提示：")
    print(f"  - 可以用文本編輯器打開查看：{output_path}")
    print(f"  - 與原始拼接版本比較：diff final_report.md {output_path.name}")


if __name__ == '__main__':
    main()
