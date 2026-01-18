#!/usr/bin/env python3
"""
10remove_isolated_name_lists.py - 刪除孤立的人名列表

問題：
AI 生成的報告中，每個主題開頭都會出現一段無意義的人名列表：
```
## 2. 專案 / 案件進度與追蹤

*   蔡宗哲
*   林以凡
*   Brenda Tsai
*   Chris Ho
*   Vandose Chen

*   **報告分享:**
    ...
```

這些孤立的人名列表沒有任何說明，應該刪除。

特徵：
1. 緊接在 ## 標題之後（可能有空行）
2. 只有人名，沒有冒號、說明、子彈點內容
3. 列表後有空行，然後才是真正的內容

用法：
python 10remove_isolated_name_lists.py --input report.md --output report_clean.md
"""

import argparse
import re
from pathlib import Path


def is_isolated_name_line(line: str) -> bool:
    """判斷是否是孤立的人名列表項"""
    stripped = line.strip()

    # 必須是列表項
    if not stripped.startswith('*'):
        return False

    # 移除列表符號
    content = stripped.lstrip('*').strip()

    # 空的列表項
    if not content:
        return False

    # 有冒號或說明文字（在冒號後有內容），不是孤立人名
    if ':' in content or '：' in content:
        # 但如果冒號後面是空的（如「**參與者：**」），這不算
        colon_idx = max(content.find(':'), content.find('：'))
        if colon_idx > 0 and colon_idx < len(content) - 1:
            after_colon = content[colon_idx+1:].strip()
            if after_colon and not after_colon.startswith('*'):
                return False

    # 有子列表（嵌套的 *），不是孤立人名
    if content.count('*') > 2:  # 允許 **XX** 格式
        return False

    # 檢查是否像人名
    # 特徵：
    # - 包含中文或英文名字
    # - 可能有括號（英文名）
    # - 長度不會太長（人名通常 < 30 字）
    # - 沒有明顯的動詞、數字、單位

    if len(content) > 30:
        return False

    # 包含明顯的報告內容關鍵詞，不是人名
    report_keywords = [
        '報告', '確認', '追蹤', '負責', '完成', '進度',
        '金額', '萬', '億', '元', '月', '日',
        '已', '將', '需', '應', '可', '會', '要', '能',
        '案', '專案', '合約', '訂單', '發票'
    ]
    for keyword in report_keywords:
        if keyword in content:
            return False

    # 符合人名模式
    # 中文名 或 英文名 或 中英文混合
    name_pattern = r'^[\u4e00-\u9fff\sA-Za-z()（）]+$'
    if re.match(name_pattern, content):
        return True

    return False


def remove_isolated_name_lists(content: str) -> str:
    """刪除孤立的人名列表"""
    lines = content.split('\n')
    result = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # 檢測是否進入主題標題
        if re.match(r'^##\s+\d+\.', line.strip()):
            result.append(line)
            i += 1

            # 跳過標題後的空行
            while i < len(lines) and lines[i].strip() == '':
                result.append(lines[i])
                i += 1

            # 檢查是否是孤立人名列表
            name_list_start = i
            name_count = 0

            while i < len(lines):
                current_line = lines[i]

                # 空行，可能是列表結束
                if current_line.strip() == '':
                    i += 1
                    continue

                # 是孤立人名
                if is_isolated_name_line(current_line):
                    name_count += 1
                    i += 1
                else:
                    # 不是人名，列表結束
                    break

            # 如果找到孤立人名列表（至少3個人名），跳過它們
            if name_count >= 3:
                print(f"  🗑️  刪除孤立人名列表（{name_count} 個人名）", flush=True)
                # i 已經指向非人名行，繼續處理
                continue
            else:
                # 不是孤立列表，恢復處理
                i = name_list_start
                continue

        result.append(line)
        i += 1

    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(
        description='刪除報告中孤立的人名列表'
    )

    parser.add_argument('--input', required=True, help='輸入 MD 文件')
    parser.add_argument('--output', help='輸出文件（默認：input_no_name_lists.md）')

    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        print(f"❌ 文件不存在：{input_file}")
        return

    # 讀取
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("=" * 60)
    print("🧹 刪除孤立人名列表")
    print("=" * 60)

    # 處理
    cleaned = remove_isolated_name_lists(content)

    # 輸出路徑
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = input_file.parent / f"{input_file.stem}_no_name_lists.md"

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
