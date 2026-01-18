#!/usr/bin/env python3
"""
main_part2_test.py - 测试主题 MD 合并功能

功能：
1. 逐个判断 MD 文件的价值（适合 Gemma3，每次 ≤ 4000 字）
2. 根据摘要排序主题
3. 合并成单一会议记录

用法：
python main_part2_test.py --input-dir /path/to/md/files
"""

import argparse
import os
import re
import json
import time
import threading
from pathlib import Path
from typing import List, Dict, Tuple
import ollama
from zhconv_rs import zhconv
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL


# ==================== AI 交互函数 ====================

def print_dot(stop_event):
    """显示进度点"""
    while not stop_event.is_set():
        print('.', end='', flush=True)
        time.sleep(0.8)


def ai_response(messages, max_tokens=1000):
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


# ==================== 步骤 7.1：价值判断 ====================

SYSTEM_PROMPT_FILTER = """你是會議記錄審查專家。
請判斷這個會議主題是否應該保留在正式會議記錄中。

【保留標準】(true)：
- 包含實質業務內容（專案、財務、採購、合約等）
- 有明確的決議、行動項目或重要討論
- 涉及金錢、時程、人員安排等關鍵資訊

【移除標準】(false)：
- 僅是簡單的人事問候、感謝
- 標註為「錯誤」、「無關」的內容
- 無實質內容的技術問題記錄
- 過於瑣碎的細節

請只回覆 JSON 格式（不要其他說明）：
{"keep": true, "reason": "一句話說明原因"}
或
{"keep": false, "reason": "一句話說明原因"}
"""


def judge_topic_value(md_file: Path) -> Dict:
    """
    判断单个主题的价值

    返回: {"keep": true/false, "reason": "..."}
    """
    # 读取文件内容
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查字数（Gemma3 限制）
    char_count = len(content)
    if char_count > 4000:
        print(f"⚠️  警告：{md_file.name} 超過 4000 字（{char_count} 字），可能影響判斷準確度")

    # 构建 prompt
    user_prompt = f"""主題檔名：{md_file.name}

內容：
{content}

請判斷是否保留此主題。"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_FILTER},
        {"role": "user", "content": user_prompt}
    ]

    # 调用 AI（带进度点）
    print(f"\n🤔 判斷：{md_file.name} ({char_count} 字)", end='')
    stop_event = threading.Event()
    dot_thread = threading.Thread(target=print_dot, args=(stop_event,))
    dot_thread.start()

    try:
        response = ai_response(messages, max_tokens=200)
    finally:
        stop_event.set()
        dot_thread.join()

    # 解析 JSON
    try:
        # 尝试直接解析
        result = json.loads(response)
    except json.JSONDecodeError:
        # 尝试提取 JSON 部分
        json_match = re.search(r'\{.*?\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            # 如果完全失败，手动判断
            print(f"\n⚠️  無法解析回應，使用預設判斷")
            if '錯誤' in md_file.name or '無關' in md_file.name or '感謝' in md_file.name:
                result = {"keep": False, "reason": "根據檔名判斷"}
            else:
                result = {"keep": True, "reason": "根據檔名判斷"}

    # 添加文件信息
    result['filename'] = md_file.name
    result['char_count'] = char_count

    # 显示结果
    emoji = "✅" if result['keep'] else "❌"
    print(f" {emoji} {result['reason']}")

    return result


# ==================== 步骤 7.2：排序 ====================

SYSTEM_PROMPT_ORDER = """你是會議流程專家。
請根據合理的會議流程，為這些主題排序。

【一般會議順序】：
1. 重要報告（財務、專案進度）
2. 討論議題（採購、合約）
3. 行政事項（檔案、報告處理）
4. 合規事項（消防、安全）
5. 其他事項

請只回覆檔名的順序列表，用逗號分隔，例如：
專案進度與財務.md,採購_合約_訂單.md,檔案_郵件_報告處理.md

不要其他說明，只要檔名列表。
"""


def sort_topics(md_files: List[Path]) -> List[Path]:
    """
    根据主题摘要排序

    为了控制 Gemma3 的输入长度，每个主题只取前 200 字作为摘要
    """
    # 构建摘要
    summaries = []
    for f in md_files:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            preview = content[:200] + '...' if len(content) > 200 else content
            summaries.append(f"【{f.name}】\n{preview}")

    summaries_text = "\n\n".join(summaries)
    total_chars = len(summaries_text)

    print(f"\n📊 排序任務：{len(md_files)} 個主題，總計 {total_chars} 字")

    if total_chars > 3000:
        print(f"⚠️  警告：摘要總長度超過 3000 字，可能影響排序準確度")

    user_prompt = f"""以下是各主題的摘要：

{summaries_text}

請給出合理的排序（只要檔名，用逗號分隔）。"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_ORDER},
        {"role": "user", "content": user_prompt}
    ]

    # 调用 AI
    print(f"🤔 正在排序", end='')
    stop_event = threading.Event()
    dot_thread = threading.Thread(target=print_dot, args=(stop_event,))
    dot_thread.start()

    try:
        response = ai_response(messages, max_tokens=500)
    finally:
        stop_event.set()
        dot_thread.join()

    print(f" ✅")

    # 解析回应（提取文件名）
    # 尝试按逗号分割
    filenames = [name.strip() for name in response.split(',')]

    # 构建文件名到路径的映射
    file_map = {f.name: f for f in md_files}

    # 按顺序排列（忽略不存在的文件名）
    sorted_files = []
    for fname in filenames:
        if fname in file_map:
            sorted_files.append(file_map[fname])

    # 添加未被排序的文件（防止遗漏）
    for f in md_files:
        if f not in sorted_files:
            sorted_files.append(f)
            print(f"⚠️  {f.name} 未被 AI 排序，追加到末尾")

    return sorted_files


# ==================== 步骤 7.3：合并 ====================

def merge_reports(sorted_files: List[Path], output_path: Path):
    """
    合并报告（简单拼接，不需要 AI）
    """
    print(f"\n📝 合併 {len(sorted_files)} 個主題到：{output_path}")

    with open(output_path, 'w', encoding='utf-8') as out:
        # 写入标题
        out.write("# 會議記錄\n\n")
        out.write(f"**主題數量：** {len(sorted_files)}\n\n")
        out.write("---\n\n")

        # 逐个写入主题
        for i, md_file in enumerate(sorted_files, 1):
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # 提取主题名称（从文件名）
            topic_name = md_file.stem.replace('_', ' ')

            print(f"  {i}. {topic_name}")

            out.write(f"## {i}. {topic_name}\n\n")
            out.write(content)
            out.write("\n\n")

            # 添加分隔线（除了最后一个）
            if i < len(sorted_files):
                out.write("---\n\n")

    print(f"\n✅ 合併完成！")


# ==================== 主流程 ====================

def main():
    parser = argparse.ArgumentParser(description='测试主题 MD 合并功能')
    parser.add_argument('--input-dir', required=True, help='包含 MD 文件的目录')
    parser.add_argument('--output', help='输出文件路径（默认：input-dir/final_report.md）')
    parser.add_argument('--skip-filter', action='store_true', help='跳过价值判断，保留所有主题')
    parser.add_argument('--skip-sort', action='store_true', help='跳过排序，按文件名排序')
    args = parser.parse_args()

    start_time = time.time()

    # 获取所有 MD 文件
    input_dir = Path(args.input_dir)
    all_md_files = list(input_dir.glob('*.md'))

    # 排除系统文件
    exclude_keywords = ['CLAUDE', 'README', 'PATENT', 'cleaned', 'final']
    md_files = [
        f for f in all_md_files
        if not any(exc in f.name for exc in exclude_keywords)
    ]

    if not md_files:
        print(f"❌ 在 {input_dir} 中未找到 MD 文件")
        return

    print("="*60)
    print("🚀 開始測試主題合併功能")
    print("="*60)
    print(f"📁 輸入目錄：{input_dir}")
    print(f"📄 找到 {len(md_files)} 個主題檔案：")
    for f in md_files:
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.1f} KB)")

    # ==================== 步骤 7.1：价值判断 ====================
    if not args.skip_filter:
        print("\n" + "="*60)
        print("📋 步驟 7.1：價值判斷")
        print("="*60)

        judgments = []
        for md_file in md_files:
            result = judge_topic_value(md_file)
            judgments.append(result)

        # 保存判断结果
        judgment_file = input_dir / 'topic_judgments.json'
        with open(judgment_file, 'w', encoding='utf-8') as f:
            json.dump(judgments, f, ensure_ascii=False, indent=2)
        print(f"\n💾 判斷結果已儲存：{judgment_file}")

        # 过滤
        kept_files = [
            Path(input_dir / j['filename'])
            for j in judgments if j['keep']
        ]
        removed_files = [
            Path(input_dir / j['filename'])
            for j in judgments if not j['keep']
        ]

        print(f"\n📊 過濾結果：")
        print(f"  ✅ 保留：{len(kept_files)} 個")
        print(f"  ❌ 移除：{len(removed_files)} 個")

        if removed_files:
            print(f"\n❌ 已移除的主題：")
            for f in removed_files:
                reason = next(j['reason'] for j in judgments if j['filename'] == f.name)
                print(f"  - {f.name}: {reason}")

        md_files = kept_files

    # ==================== 步骤 7.2：排序 ====================
    if not args.skip_sort and len(md_files) > 1:
        print("\n" + "="*60)
        print("📋 步驟 7.2：主題排序")
        print("="*60)

        sorted_files = sort_topics(md_files)

        print(f"\n📝 排序結果：")
        for i, f in enumerate(sorted_files, 1):
            print(f"  {i}. {f.name}")
    else:
        # 按文件名排序
        sorted_files = sorted(md_files, key=lambda x: x.name)
        print(f"\n⏭️  跳過排序，使用檔名順序")

    # ==================== 步骤 7.3：合并 ====================
    print("\n" + "="*60)
    print("📋 步驟 7.3：合併報告")
    print("="*60)

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_dir / 'Final_report.md'

    merge_reports(sorted_files, output_path)

    # ==================== 总结 ====================
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print("🎉 測試完成！")
    print("="*60)
    print(f"⏱️  總耗時：{elapsed:.1f} 秒")
    print(f"📄 最終報告：{output_path}")
    print(f"📊 包含主題數：{len(sorted_files)}")

    # 显示文件大小
    if output_path.exists():
        size_kb = output_path.stat().st_size / 1024
        print(f"📦 檔案大小：{size_kb:.1f} KB")


if __name__ == '__main__':
    main()
