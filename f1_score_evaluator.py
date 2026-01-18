#!/usr/bin/env python3
"""
f1_score_evaluator.py - 使用 F1 Score 評估會議報告品質

以逐字稿為 Ground Truth，計算：
1. 關鍵實體提取準確率（數字、人名、日期、組織）
2. Precision（報告中有多少是正確的）
3. Recall（逐字稿中有多少被捕獲）
4. F1 Score（綜合指標）

用法：
python f1_score_evaluator.py \
    --ground-truth 會議BSS/BSS.txt \
    --report1 claude_meeting_summary.md \
    --report2 會議BSS/topic_report_final.md
"""

import argparse
import re
from pathlib import Path
from typing import Set, Dict, List, Tuple
from collections import defaultdict


class EntityExtractor:
    """實體提取器"""

    def __init__(self):
        # 編譯正則表達式
        self.patterns = {
            'amounts': re.compile(r'\d+\.?\d*\s*[萬億千百]?\s*元?(?=\D|$)'),
            'dates': re.compile(r'(?:\d{4}年)?\d{1,2}月\d{1,2}[日號]?'),
            # ✅ 修復：同時匹配「中文（英文）」和純中文名
            'names_with_en': re.compile(r'([\u4e00-\u9fff]{2,4})\s*[\(（]([A-Za-z\s]+)[\)）]'),
            'names_chinese_only': re.compile(r'(?:^|\s)([\u4e00-\u9fff]{2,4})(?=\s|$|[：:、，。])'),
            'names_english': re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'),
            # ✅ 修復：更嚴格的組織名匹配
            'orgs': re.compile(r'[\u4e00-\u9fff]{3,15}(?:局|署|部|會|院|司|處|科|組|中心|公司|銀行|協會|廳|委員會)(?=\D|$)'),
            'percentages': re.compile(r'\d+\.?\d*\s*[%％]'),
        }

        # 常見人名列表（用於過濾）
        self.common_names = set()

    def extract_amounts(self, text: str) -> Set[str]:
        """提取金額"""
        amounts = set()
        for match in self.patterns['amounts'].finditer(text):
            amount = match.group(0).strip()
            # 標準化
            amount = amount.replace(' ', '').replace('元', '')
            if amount:
                amounts.add(amount)
        return amounts

    def extract_dates(self, text: str) -> Set[str]:
        """提取日期"""
        dates = set()
        for match in self.patterns['dates'].finditer(text):
            date = match.group(0).strip()
            # 標準化：統一用「日」
            date = date.replace('號', '日')
            dates.add(date)
        return dates

    def extract_names(self, text: str) -> Set[str]:
        """✅ 修復：提取人名（支持多種格式）"""
        names = set()

        # 1. 提取「中文（英文）」格式
        for match in self.patterns['names_with_en'].finditer(text):
            chinese_name = match.group(1)
            english_name = match.group(2).strip()
            # 標準化格式
            full_name = f"{chinese_name} ({english_name})"
            names.add(full_name)
            # 同時記錄單獨的中文名和英文名
            names.add(chinese_name)
            names.add(english_name)

        # 2. 提取純英文名（如 "Brenda Tsai"）
        for match in self.patterns['names_english'].finditer(text):
            english_name = match.group(1).strip()
            if len(english_name.split()) >= 2:  # 至少兩個詞
                names.add(english_name)

        # 3. 從上下文提取純中文名（更智能）
        # 尋找特定模式：「XXX 報告」「XXX 負責」「XXX 表示」等
        name_context_patterns = [
            r'([\u4e00-\u9fff]{2,4})\s*(?:報告|負責|表示|說|追蹤|確認|協助|建議)',
            r'(?:由|請|找)\s*([\u4e00-\u9fff]{2,4})',
            r'\*\*\s*([\u4e00-\u9fff]{2,4})\s*[：:]',  # Markdown 格式
        ]

        for pattern in name_context_patterns:
            for match in re.finditer(pattern, text):
                name = match.group(1).strip()
                if len(name) >= 2 and name not in ['報告', '負責', '表示', '確認', '協助', '建議']:
                    names.add(name)

        return names

    def extract_orgs(self, text: str) -> Set[str]:
        """✅ 修復：提取組織名稱（更嚴格過濾）"""
        orgs = set()

        # 無意義片段黑名單
        blacklist = [
            '到時候', '他還是', '所以如果', '整個包含', '任何需要', '不足的部',
            '就會', '還是會', '可能會', '應該會', '能夠會',
            '的地方', '的部分', '的時候', '的情況',
            '進行部', '教育部', '外部', '內部', '全部', '局部',
        ]

        for match in self.patterns['orgs'].finditer(text):
            org = match.group(0).strip()

            # 過濾條件
            if len(org) < 3 or len(org) > 15:  # 長度限制
                continue

            # 檢查黑名單
            is_blacklisted = False
            for bad in blacklist:
                if bad in org:
                    is_blacklisted = True
                    break

            if not is_blacklisted:
                orgs.add(org)

        return orgs

    def extract_percentages(self, text: str) -> Set[str]:
        """提取百分比"""
        percentages = set()
        for match in self.patterns['percentages'].finditer(text):
            pct = match.group(0).strip().replace(' ', '').replace('％', '%')
            percentages.add(pct)
        return percentages

    def extract_all(self, text: str) -> Dict[str, Set[str]]:
        """提取所有類型實體"""
        return {
            'amounts': self.extract_amounts(text),
            'dates': self.extract_dates(text),
            'names': self.extract_names(text),
            'orgs': self.extract_orgs(text),
            'percentages': self.extract_percentages(text)
        }


def calculate_f1(predicted: Set, ground_truth: Set) -> Tuple[float, float, float]:
    """計算 Precision, Recall, F1 Score"""
    if not predicted and not ground_truth:
        return 1.0, 1.0, 1.0

    if not predicted:
        return 0.0, 0.0, 0.0

    if not ground_truth:
        # 如果 ground truth 是空的，但預測有內容，precision=0
        return 0.0, 1.0, 0.0

    true_positive = len(predicted & ground_truth)
    false_positive = len(predicted - ground_truth)
    false_negative = len(ground_truth - predicted)

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) > 0 else 0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) > 0 else 0

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)

    return precision, recall, f1


def evaluate_report(ground_truth_entities: Dict[str, Set[str]],
                   report_entities: Dict[str, Set[str]],
                   report_name: str) -> Dict:
    """評估單個報告"""
    print(f"\n{'=' * 60}")
    print(f"📊 評估報告：{report_name}")
    print('=' * 60)

    results = {}
    total_f1 = []

    for entity_type in ['amounts', 'dates', 'names', 'orgs', 'percentages']:
        gt = ground_truth_entities[entity_type]
        pred = report_entities[entity_type]

        precision, recall, f1 = calculate_f1(pred, gt)
        total_f1.append(f1)

        results[entity_type] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'gt_count': len(gt),
            'pred_count': len(pred),
            'correct': len(pred & gt)
        }

        # 顯示結果
        type_names = {
            'amounts': '金額',
            'dates': '日期',
            'names': '人名',
            'orgs': '組織',
            'percentages': '百分比'
        }
        print(f"\n{type_names[entity_type]}:")
        print(f"  Ground Truth: {len(gt)} 個")
        print(f"  報告提取: {len(pred)} 個")
        print(f"  正確匹配: {len(pred & gt)} 個")
        print(f"  Precision: {precision:.2%}")
        print(f"  Recall: {recall:.2%}")
        print(f"  F1 Score: {f1:.2%}")

        # 顯示錯誤
        if len(pred - gt) > 0:
            print(f"  ❌ 錯誤提取（False Positive）: {len(pred - gt)} 個")
            for item in list(pred - gt)[:3]:  # 只顯示前3個
                print(f"     - {item}")

        if len(gt - pred) > 0:
            print(f"  ⚠️  遺漏（False Negative）: {len(gt - pred)} 個")
            for item in list(gt - pred)[:3]:  # 只顯示前3個
                print(f"     - {item}")

    # 計算平均 F1
    avg_f1 = sum(total_f1) / len(total_f1)
    results['average_f1'] = avg_f1

    print(f"\n{'=' * 60}")
    print(f"🎯 平均 F1 Score: {avg_f1:.2%}")
    print('=' * 60)

    return results


def print_comparison(results1: Dict, results2: Dict, name1: str, name2: str):
    """打印比較表格"""
    print(f"\n\n{'=' * 80}")
    print("📈 綜合比較")
    print('=' * 80)

    print(f"\n{'實體類型':<12} | {name1:<20} | {name2:<20} | 差異")
    print('-' * 80)

    type_names = {
        'amounts': '金額',
        'dates': '日期',
        'names': '人名',
        'orgs': '組織',
        'percentages': '百分比'
    }

    for entity_type in ['amounts', 'dates', 'names', 'orgs', 'percentages']:
        f1_1 = results1[entity_type]['f1']
        f1_2 = results2[entity_type]['f1']
        diff = f1_2 - f1_1

        diff_str = f"{diff:+.2%}" if diff != 0 else " 持平"
        winner = "🏆" if diff > 0 else ("🔻" if diff < 0 else "⚖️")

        print(f"{type_names[entity_type]:<12} | {f1_1:>6.2%} (F1)        | {f1_2:>6.2%} (F1)        | {diff_str} {winner}")

    print('-' * 80)
    avg1 = results1['average_f1']
    avg2 = results2['average_f1']
    diff = avg2 - avg1
    winner = "🏆" if diff > 0 else ("🔻" if diff < 0 else "⚖️")

    print(f"{'平均 F1':<12} | {avg1:>6.2%}            | {avg2:>6.2%}            | {diff:+.2%} {winner}")
    print('=' * 80)

    # 顯示總結
    print(f"\n🏁 總結：")
    if diff > 0.05:
        print(f"   {name2} 明顯優於 {name1} (+{diff:.1%})")
    elif diff > 0.01:
        print(f"   {name2} 略優於 {name1} (+{diff:.1%})")
    elif diff > -0.01:
        print(f"   兩者表現相當（差異 {diff:.1%}）")
    elif diff > -0.05:
        print(f"   {name1} 略優於 {name2} ({diff:.1%})")
    else:
        print(f"   {name1} 明顯優於 {name2} ({diff:.1%})")


def main():
    parser = argparse.ArgumentParser(
        description='使用 F1 Score 評估會議報告品質'
    )

    parser.add_argument('--ground-truth', required=True, help='逐字稿文件（Ground Truth）')
    parser.add_argument('--report1', required=True, help='報告1（Claude版）')
    parser.add_argument('--report2', required=True, help='報告2（Pipeline版）')

    args = parser.parse_args()

    # 檢查文件
    gt_file = Path(args.ground_truth)
    r1_file = Path(args.report1)
    r2_file = Path(args.report2)

    for f in [gt_file, r1_file, r2_file]:
        if not f.exists():
            print(f"❌ 文件不存在：{f}")
            return

    # 讀取文件
    with open(gt_file, 'r', encoding='utf-8') as f:
        ground_truth_text = f.read()

    with open(r1_file, 'r', encoding='utf-8') as f:
        report1_text = f.read()

    with open(r2_file, 'r', encoding='utf-8') as f:
        report2_text = f.read()

    print("=" * 80)
    print("🔍 F1 Score 評估系統")
    print("=" * 80)
    print(f"\nGround Truth: {gt_file.name}")
    print(f"報告1: {r1_file.name}")
    print(f"報告2: {r2_file.name}")

    # 提取實體
    extractor = EntityExtractor()

    print(f"\n提取 Ground Truth 實體...")
    gt_entities = extractor.extract_all(ground_truth_text)

    print(f"提取報告1實體...")
    r1_entities = extractor.extract_all(report1_text)

    print(f"提取報告2實體...")
    r2_entities = extractor.extract_all(report2_text)

    # 顯示 Ground Truth 統計
    print(f"\n{'=' * 60}")
    print("📋 Ground Truth 統計")
    print('=' * 60)
    for entity_type, entities in gt_entities.items():
        type_names = {
            'amounts': '金額',
            'dates': '日期',
            'names': '人名',
            'orgs': '組織',
            'percentages': '百分比'
        }
        print(f"{type_names[entity_type]}: {len(entities)} 個")

    # 評估兩個報告
    results1 = evaluate_report(gt_entities, r1_entities, r1_file.name)
    results2 = evaluate_report(gt_entities, r2_entities, r2_file.name)

    # 比較
    print_comparison(results1, results2, r1_file.name, r2_file.name)


if __name__ == '__main__':
    main()
