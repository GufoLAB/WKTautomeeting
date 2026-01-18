#!/usr/bin/env python3
"""
11remove_participant_lists.py - 刪除「參與者」或類似的孤立人名列表

問題：
報告中經常出現這種無意義的人名列表：

## 7. 合作 / 協調 / 會議

**參與者：**
*   蔡宗哲
*   Vandose Chen
*   Scott Chen
*   April Lee
*   ...

**重點議程與細節：**
    ...

解決方案：
檢測「**參與者：**」或「**人員：**」後緊跟的純人名列表，整塊刪除。

用法：
python 11remove_participant_lists.py --input report.md --output report_clean.md
"""

import argparse
import re
from pathlib import Path


def remove_participant_lists(content: str) -> str:
    """刪除參與者/人員列表區塊"""
    lines = content.split('\n')
    result = []

    i = 0
    removed_count = 0

    while i < len(lines):
        line = lines[i]

        # 檢測是否是「參與者」或「人員」標題
        stripped = line.strip()

        # 匹配模式：**參與者：**、**人員：**、**與會者：**
        if re.match(r'^\*\*\s*(?:參與者|人員|與會者|與會人員)\s*[：:]\s*\*\*\s*$', stripped):
            print(f"  🔍 發現參與者列表標題：Line {i+1}")

            # 記錄標題位置
            title_line = i
            i += 1

            # 收集後續的人名列表
            name_list_lines = []

            while i < len(lines):
                current = lines[i].strip()

                # 空行，繼續
                if not current:
                    i += 1
                    continue

                # 列表項且是純人名
                if current.startswith('*'):
                    content = current.lstrip('*').strip()

                    # 檢查是否是純人名（沒有冒號、沒有說明）
                    # 人名特徵：只有中文、英文、空格、括號
                    if re.match(r'^[\u4e00-\u9fff\sA-Za-z()（）]+$', content):
                        # 確保不包含關鍵詞
                        if not any(kw in content for kw in ['報告', '負責', '確認', '追蹤', '協助', '建議']):
                            name_list_lines.append(i)
                            i += 1
                            continue

                # 不是人名列表，停止
                break

            # 如果找到至少 3 個人名，刪除整塊（包括標題）
            if len(name_list_lines) >= 3:
                print(f"  🗑️  刪除參與者列表：標題 + {len(name_list_lines)} 個人名")
                removed_count += 1
                # i 已經指向非人名行，繼續
                continue
            else:
                # 不夠多，保留標題
                result.append(lines[title_line])
                # 恢復 i 到標題後
                i = title_line + 1
                continue

        result.append(line)
        i += 1

    print(f"\n  📊 總共刪除 {removed_count} 個參與者列表區塊")

    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(
        description='刪除報告中的參與者/人員列表區塊'
    )

    parser.add_argument('--input', required=True, help='輸入 MD 文件')
    parser.add_argument('--output', help='輸出文件（默認：input_no_participants.md）')

    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        print(f"❌ 文件不存在：{input_file}")
        return

    # 讀取
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("=" * 60)
    print("🧹 刪除參與者/人員列表")
    print("=" * 60)

    # 處理
    cleaned = remove_participant_lists(content)

    # 輸出路徑
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = input_file.parent / f"{input_file.stem}_no_participants.md"

    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned)

    # 統計
    original_lines = len(content.split('\n'))
    cleaned_lines = len(cleaned.split('\n'))
    removed_lines = original_lines - cleaned_lines

    print(f"\n✅ 完成！")
    print(f"  - 原始行數：{original_lines}")
    print(f"  - 清理後：{cleaned_lines}")
    print(f"  - 刪除：{removed_lines} 行")
    print(f"\n💾 已儲存：{output_file}")
    print("=" * 60)


if __name__ == '__main__':
    main()
