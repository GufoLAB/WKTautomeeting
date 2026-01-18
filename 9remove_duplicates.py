#!/usr/bin/env python3
"""
9remove_duplicates.py - 非 LLM 智能去重算法

功能：
1. 检测报告中重复出现的段落、标题
2. 使用相似度算法（不依赖 LLM）
3. 智能保留第一次出现，删除后续重复

算法：
- 精确匹配：完全相同的行
- 模糊匹配：使用编辑距离判断相似段落
- 结构分析：识别重复的章节结构

用法：
python 9remove_duplicates.py --input report.md --output report_dedup.md
"""

import argparse
import re
from pathlib import Path
from typing import List, Set, Tuple
from difflib import SequenceMatcher


# ==================== 去重策略 ====================

class DuplicateRemover:
    """智能去重器"""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.seen_sections = set()  # 已见过的章节标题
        self.seen_lines = set()     # 已见过的行（精确匹配）
        self.seen_paragraphs = []   # 已见过的段落（模糊匹配）

        # 需要去重的标题模式（包含有冒號和沒冒號的）
        self.duplicate_headers = [
            r'\*\*會議基本資訊[：:]*\*\*',
            r'\*\*與會人員[：:]*\*\*',
            r'\*\*會議時間[：:]*\*\*',
            r'\*\*會議地點[：:]*\*\*',
            r'\*\*議程與重點摘要[：:]*\*\*',
            r'\*\*會議目的[：:]*\*\*',
        ]

    def similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度（0-1）"""
        return SequenceMatcher(None, text1, text2).ratio()

    def is_duplicate_header(self, line: str) -> bool:
        """检查是否是重复的标题"""
        for pattern in self.duplicate_headers:
            if re.search(pattern, line):
                return True
        return False

    def is_empty_or_useless(self, line: str) -> bool:
        """检查是否是空行或无用行"""
        stripped = line.strip()

        # 空行
        if not stripped:
            return False  # 保留空行用于格式

        # 只有星号的行
        if re.match(r'^[\*\s]+$', stripped):
            return True

        # 空的列表项
        if re.match(r'^\*\s*$', stripped):
            return True

        # 多层空列表
        if re.match(r'^\*\s+\*\s+\*\s+\*\s*$', stripped):
            return True

        return False

    def normalize_line(self, line: str) -> str:
        """标准化行（用于比较）"""
        # 去除多余空格
        normalized = ' '.join(line.split())
        # 去除标点符号的空格差异
        normalized = re.sub(r'\s*([：:，。])\s*', r'\1', normalized)
        return normalized

    def is_similar_to_seen(self, paragraph: str) -> bool:
        """检查段落是否与已见过的相似"""
        normalized = self.normalize_line(paragraph)

        for seen_para in self.seen_paragraphs:
            similarity = self.similarity(normalized, seen_para)
            if similarity >= self.similarity_threshold:
                return True

        return False

    def process_content(self, content: str) -> str:
        """处理内容，去除重复"""
        lines = content.split('\n')
        result = []
        current_paragraph = []
        in_topic_section = False
        topic_section_index = 0
        in_header_section = True  # 開頭區域標記

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检测主题分隔（## 数字.）
            if re.match(r'^##\s+\d+\.', stripped):
                in_topic_section = True
                in_header_section = False  # 離開開頭區域
                topic_section_index += 1

                result.append(line)
                continue

            # 检测会议摘要部分结束
            if stripped.startswith('## ') and '會議摘要' in stripped:
                in_header_section = False

            # 在主题内容中检测重复标题 - 全部刪除，不管是否出現過
            if in_topic_section and self.is_duplicate_header(line):
                # 直接跳過，不保留任何一次
                continue

            # 检查无用行
            if self.is_empty_or_useless(line):
                # 保留一定数量的空行用于格式
                if stripped == '' and result and result[-1].strip() != '':
                    result.append(line)
                continue

            # 段落级去重（用于较长的重复内容）
            if stripped and len(stripped) > 50:
                if self.is_similar_to_seen(stripped):
                    continue
                else:
                    # 只保留前 100 个段落用于比较（避免内存过大）
                    if len(self.seen_paragraphs) < 100:
                        self.seen_paragraphs.append(self.normalize_line(stripped))

            result.append(line)

        # 清理连续的多个空行
        cleaned = []
        prev_empty = False
        for line in result:
            is_empty = line.strip() == ''
            if is_empty and prev_empty:
                continue
            cleaned.append(line)
            prev_empty = is_empty

        return '\n'.join(cleaned)


# ==================== 统计分析 ====================

def analyze_duplicates(content: str) -> dict:
    """分析重复情况（不修改内容）"""
    lines = content.split('\n')

    # 统计标题出现次数
    header_counts = {}
    for line in lines:
        stripped = line.strip()
        if re.match(r'\*\*[^*]+\*\*', stripped):
            header_counts[stripped] = header_counts.get(stripped, 0) + 1

    # 找出重复的标题
    duplicates = {k: v for k, v in header_counts.items() if v > 1}

    # 统计空的列表项
    empty_list_items = sum(1 for line in lines if re.match(r'^\s*\*\s*\*\s*\*\s*\*\s*$', line.strip()))

    return {
        'total_lines': len(lines),
        'duplicate_headers': duplicates,
        'empty_list_items': empty_list_items
    }


# ==================== 主程序 ====================

def main():
    parser = argparse.ArgumentParser(
        description='智能去重报告内容（非 LLM）'
    )

    parser.add_argument('--input', required=True, help='输入文件')
    parser.add_argument('--output', help='输出文件（默认：input_dedup.md）')
    parser.add_argument('--similarity', type=float, default=0.85,
                       help='相似度阈值（0-1，默认 0.85）')
    parser.add_argument('--analyze-only', action='store_true',
                       help='只分析不修改')

    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        print(f"❌ 文件不存在：{input_file}")
        return

    # 读取内容
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("="*60)
    print("🔍 智能去重分析")
    print("="*60)

    # 分析重复
    stats = analyze_duplicates(content)
    print(f"\n📊 原始統計：")
    print(f"  - 總行數：{stats['total_lines']}")
    print(f"  - 重複標題：{len(stats['duplicate_headers'])} 種")

    if stats['duplicate_headers']:
        print(f"\n🔍 發現重複標題：")
        for header, count in sorted(stats['duplicate_headers'].items(),
                                    key=lambda x: x[1], reverse=True):
            if count > 2:  # 只显示重复 2 次以上的
                print(f"  - {header[:50]}... (出現 {count} 次)")

    print(f"  - 空列表項：{stats['empty_list_items']}")

    if args.analyze_only:
        print("\n✅ 分析完成（未修改文件）")
        return

    # 执行去重
    print(f"\n🔄 執行去重...")
    print(f"  - 相似度閾值：{args.similarity}")

    remover = DuplicateRemover(similarity_threshold=args.similarity)
    cleaned_content = remover.process_content(content)

    # 统计去重后
    stats_after = analyze_duplicates(cleaned_content)

    # 确定输出路径
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = input_file.parent / f"{input_file.stem}_dedup.md"

    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)

    print(f"\n✅ 去重完成！")
    print(f"\n📊 去重後統計：")
    print(f"  - 總行數：{stats_after['total_lines']} (減少 {stats['total_lines'] - stats_after['total_lines']} 行)")
    print(f"  - 重複標題：{len(stats_after['duplicate_headers'])} 種 (減少 {len(stats['duplicate_headers']) - len(stats_after['duplicate_headers'])} 種)")

    # 计算压缩率
    original_size = len(content)
    cleaned_size = len(cleaned_content)
    reduction = (1 - cleaned_size / original_size) * 100

    print(f"  - 檔案大小：{cleaned_size / 1024:.1f} KB (減少 {reduction:.1f}%)")
    print(f"\n💾 已儲存：{output_file}")

    print("\n" + "="*60)
    print("🎉 完成！")
    print("="*60)


if __name__ == '__main__':
    main()
