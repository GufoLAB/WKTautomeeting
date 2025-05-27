import re
import argparse


def clean_meeting_markdown(md_text):
    def remove_duplicates(header):
        matches = list(re.finditer(fr'{re.escape(header)}', md_text_nonlocal[0]))
        if len(matches) > 1:
            for m in reversed(matches[1:]):
                start, end = m.span()
                md_text_nonlocal[0] = md_text_nonlocal[0][:start] + md_text_nonlocal[0][end:]

    md_text_nonlocal = [md_text]
    remove_duplicates("## 會議紀錄")
    remove_duplicates("## 會議紀錄摘錄")

    # 刪除會議基本欄位中無意義的內容
    md_text_nonlocal[0] = re.sub(r'\*\*會議時間：\*\*\s*未詳.*?\n?', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\*\*會議地點：\*\*\s*未詳.*?\n?', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\*\*與會人員：\*\*\s*未詳.*?\n?', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\*\*紀錄者：\*\*\s*未詳.*?\n?', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'## 會議紀錄間：\*\*\s*未註明.*?\n?', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\*\*紀錄地點：\*\*\s*未註明.*?\n?', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\*\*主題：\*\*\s*34-38項議題討論\n?', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\*\*時間：\*\*\s*\(請填寫會議時間\)\n?', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\*\*地點：\*\*\s*\(請填寫會議地點\)\n?', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\*\*與會者：\*\*\s*\(請填寫與會者姓名及職稱\)\n?', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\*\*與會人員：\*\*\s*未註明（提及.*?）\n?', '', md_text_nonlocal[0])

    # 移除括號內提示語與中括號欄位（請填寫、原文未提供）
    md_text_nonlocal[0] = re.sub(r'（請填寫.*?）', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'（原文未提供.*?）', '', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\[.*?\]', '', md_text_nonlocal[0])

    # 移除空的粗體欄位
    md_text_nonlocal[0] = re.sub(r'\*\*(.*?)：\*\*\s*(?=\n|$)', '', md_text_nonlocal[0])

    # 移除段落編號開頭的項目標示（含粗體與非粗體）
    md_text_nonlocal[0] = re.sub(r'^[一二三四五六七八九十]{1,3}[、.．)]\s*', '', md_text_nonlocal[0], flags=re.MULTILINE)
    md_text_nonlocal[0] = re.sub(r'^\(?[一二三四五六七八九十]{1,3}\)?\s*', '', md_text_nonlocal[0], flags=re.MULTILINE)
    md_text_nonlocal[0] = re.sub(r'^\(?\d+\)?[.、)]\s*', '', md_text_nonlocal[0], flags=re.MULTILINE)
    md_text_nonlocal[0] = re.sub(r'\*\*[一二三四五六七八九十]{1,3}[、.．)]\s*', '**', md_text_nonlocal[0])
    md_text_nonlocal[0] = re.sub(r'\*\*\(?\d+\)?[.、)]\s*', '**', md_text_nonlocal[0])

    # ### 議程X：標題 轉成 ## 標題
    md_text_nonlocal[0] = re.sub(r'^###\s*議程[一二三四五六七八九十]{1,3}[：:]\s*(.*)', r'## \1', md_text_nonlocal[0], flags=re.MULTILINE)

    # 清除多餘空行
    md_text_nonlocal[0] = re.sub(r'\n{3,}', '\n\n', md_text_nonlocal[0])

    return md_text_nonlocal[0]


def main():
    parser = argparse.ArgumentParser(description="清理會議紀錄 Markdown 格式雜訊")
    parser.add_argument("input_file", help="要清理的 Markdown 檔案路徑")
    parser.add_argument("-o", "--output", help="輸出檔案路徑，預設為 <input>_cleaned.md")
    args = parser.parse_args()

    with open(args.input_file, "r", encoding="utf-8") as f:
        raw_md = f.read()

    cleaned = clean_meeting_markdown(raw_md)
    output_path = args.output or args.input_file.replace(".md", "_cleaned.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"✅ 淨化完成，已寫入：{output_path}")


if __name__ == "__main__":
    main()
