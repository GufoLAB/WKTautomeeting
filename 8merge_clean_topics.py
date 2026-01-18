#!/usr/bin/env python3
"""
8merge_clean_topics.py - 快速修复并合并主题分类报告

功能：
1. 从所有主题 MD 中提取统一的会议元数据
2. 清理各主题的格式问题（重复标题、占位符等）
3. 生成漂亮的统一开头
4. 按排序合并成单一报告

特点：
- 不需要 AI（5秒完成）
- 不修改原始文件
- 生成干净的主题分类报告

用法：
python 8merge_clean_topics.py --input-dir /path/to/md/files --output topic_report.md
或
python 8merge_clean_topics.py --from-judgment /path/to/topic_judgments.json --output topic_report.md
"""

import argparse
import os
import re
import json
from pathlib import Path
from collections import Counter
from typing import List, Dict


# ==================== 元数据提取 ====================

def extract_metadata_from_files(md_files: List[Path]) -> Dict:
    """从所有 MD 文件中提取并统一会议元数据"""

    dates = []
    times = []
    locations = []
    durations = []
    attendees = set()
    meeting_names = []

    for md_file in md_files:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取日期
        date_patterns = [
            r'日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)',
            r'日期[：:]\s*(\d{4}/\d{1,2}/\d{1,2})',
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, content)
            dates.extend(matches)

        # 提取时间
        time_match = re.search(r'時間[：:]\s*([^\n]+)', content)
        if time_match:
            times.append(time_match.group(1))

        # 提取地点
        location_patterns = [
            r'地點[：:]\s*([^\n]+)',
            r'形式[：:]\s*([^\n]+)',
        ]
        for pattern in location_patterns:
            matches = re.findall(pattern, content)
            locations.extend(matches)

        # 提取时长
        duration_patterns = [
            r'時長[：:]\s*([^\n]+)',
            r'錄製時間[：:]\s*([^\n]+)',
            r'(\d+\s*分\s*\d+\s*秒)',
        ]
        for pattern in duration_patterns:
            matches = re.findall(pattern, content)
            durations.extend(matches)

        # 提取与会者（中英文姓名）
        # 中文姓名 2-4字
        cn_names = re.findall(r'[\u4e00-\u9fa5]{2,4}\s*\([A-Za-z\s]+\)', content)
        attendees.update(cn_names)

        # 英文姓名
        en_names = re.findall(r'[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+\([^)]+\))?', content)
        attendees.update(en_names)

        # 提取会议名称
        name_match = re.search(r'會議名稱[：:]\s*([^\n]+)', content)
        if name_match:
            meeting_names.append(name_match.group(1).strip())

    # 统计最常见的值
    most_common_date = Counter(dates).most_common(1)[0][0] if dates else "未提供"
    most_common_location = Counter(locations).most_common(1)[0][0] if locations else "Teams 線上會議"
    most_common_duration = Counter(durations).most_common(1)[0][0] if durations else "未記錄"
    most_common_name = Counter(meeting_names).most_common(1)[0][0] if meeting_names else "BSS 經營管理會議"

    # 清理与会者列表
    cleaned_attendees = sorted(list(attendees))

    return {
        'meeting_name': most_common_name,
        'date': most_common_date,
        'location': most_common_location,
        'duration': most_common_duration,
        'attendees': cleaned_attendees
    }


# ==================== 内容清理 ====================

def remove_first_h2_title(content: str) -> str:
    """删除第一个 ## 标题"""
    lines = content.split('\n')
    result = []
    first_h2_removed = False

    for line in lines:
        if not first_h2_removed and line.strip().startswith('## '):
            first_h2_removed = True
            continue
        result.append(line)

    return '\n'.join(result)


def clean_content(content: str) -> str:
    """清理内容中的格式问题"""

    # 1. 删除日期/时间/地点等元数据行（将在统一的开头中展示）
    content = re.sub(r'\*\*日期[：:]\*\*[^\n]*\n?', '', content)
    content = re.sub(r'\*\*時間[：:]\*\*[^\n]*\n?', '', content)
    content = re.sub(r'\*\*地點[：:]\*\*[^\n]*\n?', '', content)
    content = re.sub(r'\*\*與會者[：:]\*\*[^\n]*\n?', '', content)
    content = re.sub(r'\*\*會議名稱[：:]\*\*[^\n]*\n?', '', content)
    content = re.sub(r'\*\*形式[：:]\*\*[^\n]*\n?', '', content)
    content = re.sub(r'\*\*錄製時間[：:]\*\*[^\n]*\n?', '', content)
    content = re.sub(r'\*\*記錄人[：:]\*\*[^\n]*\n?', '', content)

    # 2. 删除占位符
    content = re.sub(r'\([未提供補充請]*[^)]*[）)]', '', content)

    # 3. 删除 "一、二、三、" 等编号（保留层级但去掉中文数字）
    content = re.sub(r'\*\*[一二三四五六七八九十]+、\s*', '**', content)

    # 4. 删除 "會議基本資訊" 等标题
    content = re.sub(r'\*\*[一二三四五六七八九十]+、會議基本資訊\*\*\n?', '', content)
    content = re.sub(r'\*\*[一二三四五六七八九十]+、與會人員\*\*\n?', '', content)

    # 5. 清理多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.strip()


def extract_topic_name(md_file: Path) -> str:
    """从文件名提取主题名称"""
    name = md_file.stem

    # 去除 _cleaned 后缀
    name = name.replace('_cleaned', '')

    # 将下划线替换为空格
    name = name.replace('_', ' / ')

    return name


# ==================== 格式化输出 ====================

def format_attendees(attendees: List[str], max_show: int = 10) -> str:
    """格式化与会者列表"""
    if not attendees:
        return "（詳見各主題）"

    if len(attendees) <= max_show:
        return '、'.join(attendees)
    else:
        return '、'.join(attendees[:max_show]) + f' 等 {len(attendees)} 人'


def create_report_header(metadata: Dict, topic_count: int) -> str:
    """创建报告头部"""

    header = f"""# BSS 經營管理會議 - 主題分類報告

**會議名稱**: {metadata['meeting_name']}
**日期**: {metadata['date']}
**地點**: {metadata['location']}
**會議時長**: {metadata['duration']}
**與會者**: {format_attendees(metadata['attendees'])}

---

## 會議摘要

本次會議討論了 **{topic_count} 個主要議題**，涵蓋財務收款、專案進度、採購標案、技術合作、系統管理等多個面向。以下按主題分類整理會議重點。

---

"""

    return header


# ==================== 主流程 ====================

def merge_clean_topics(md_files: List[Path], sorted_order: List[str], output_path: Path):
    """合并并清理主题报告"""

    print("="*60)
    print("🚀 開始合併並清理主題報告")
    print("="*60)

    # 1. 提取元数据
    print("\n📊 提取會議元數據...")
    metadata = extract_metadata_from_files(md_files)
    print(f"  ✅ 會議名稱: {metadata['meeting_name']}")
    print(f"  ✅ 日期: {metadata['date']}")
    print(f"  ✅ 地點: {metadata['location']}")
    print(f"  ✅ 與會者: {len(metadata['attendees'])} 人")

    # 2. 创建文件名到路径的映射
    file_map = {f.name: f for f in md_files}

    # 3. 按排序获取文件
    ordered_files = []
    for fname in sorted_order:
        if fname in file_map:
            ordered_files.append(file_map[fname])
        else:
            print(f"  ⚠️  警告：找不到文件 {fname}")

    print(f"\n📝 處理 {len(ordered_files)} 個主題...")

    # 4. 生成报告头部
    report = create_report_header(metadata, len(ordered_files))

    # 5. 逐个处理主题
    for i, md_file in enumerate(ordered_files, 1):
        print(f"  {i}. {md_file.name}")

        # 读取内容
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 清理内容
        content = remove_first_h2_title(content)
        content = clean_content(content)

        # 提取主题名
        topic_name = extract_topic_name(md_file)

        # 添加到报告
        report += f"\n## {i}. {topic_name}\n\n"
        report += content
        report += "\n\n---\n\n"

    # 6. 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ 報告已生成：{output_path}")

    # 7. 统计
    file_size = output_path.stat().st_size / 1024
    with open(output_path, 'r', encoding='utf-8') as f:
        line_count = len(f.readlines())

    print(f"📊 總行數：{line_count}")
    print(f"📦 檔案大小：{file_size:.1f} KB")


# ==================== 主程序 ====================

def main():
    parser = argparse.ArgumentParser(
        description='快速修復並合併主題分類報告'
    )

    # 输入方式 1：指定目录
    parser.add_argument('--input-dir', help='包含 MD 文件的目录')

    # 输入方式 2：从 judgment 结果读取
    parser.add_argument('--from-judgment', help='从 topic_judgments.json 读取')

    # 输出
    parser.add_argument('--output', default='topic_report_clean.md',
                       help='输出文件路径')

    args = parser.parse_args()

    # ==================== 获取文件列表 ====================

    if args.from_judgment:
        # 从 judgment JSON 读取
        judgment_file = Path(args.from_judgment)
        if not judgment_file.exists():
            print(f"❌ Judgment 文件不存在：{judgment_file}")
            return

        with open(judgment_file, 'r', encoding='utf-8') as f:
            judgments = json.load(f)

        input_dir = judgment_file.parent
        kept_files = [
            input_dir / j['filename']
            for j in judgments if j['keep']
        ]

        # 读取排序（从 final_report.md）
        final_report = input_dir / 'final_report.md'
        if final_report.exists():
            with open(final_report, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取顺序
            sorted_filenames = []
            for match in re.finditer(r'## \d+\. (.+)', content):
                topic_name = match.group(1).strip()
                # 匹配文件名
                for f in kept_files:
                    if topic_name.replace(' ', '_') in f.name or \
                       topic_name.replace(' / ', '_') in f.name:
                        if f.name not in sorted_filenames:
                            sorted_filenames.append(f.name)
                            break

            # 添加未匹配的
            for f in kept_files:
                if f.name not in sorted_filenames:
                    sorted_filenames.append(f.name)
        else:
            sorted_filenames = [f.name for f in sorted(kept_files, key=lambda x: x.name)]

        md_files = kept_files

    elif args.input_dir:
        # 从目录读取
        input_dir = Path(args.input_dir)
        if not input_dir.exists():
            print(f"❌ 目錄不存在：{input_dir}")
            return

        all_md_files = list(input_dir.glob('*.md'))
        exclude_keywords = ['CLAUDE', 'README', 'PATENT', 'cleaned', 'final', 'integrated', 'timeline', 'topic_report']

        md_files = [
            f for f in all_md_files
            if not any(exc in f.name for exc in exclude_keywords)
        ]

        if not md_files:
            print(f"❌ 在 {input_dir} 中未找到 MD 文件")
            return

        sorted_filenames = [f.name for f in sorted(md_files, key=lambda x: x.name)]

    else:
        print("❌ 請指定 --input-dir 或 --from-judgment")
        return

    # ==================== 确定输出路径 ====================

    if args.output == 'topic_report_clean.md':
        if args.from_judgment:
            output_path = judgment_file.parent / args.output
        else:
            output_path = input_dir / args.output
    else:
        output_path = Path(args.output)

    # ==================== 执行合并 ====================

    merge_clean_topics(md_files, sorted_filenames, output_path)

    print("\n" + "="*60)
    print("🎉 完成！")
    print("="*60)


if __name__ == '__main__':
    main()
