import sys
import re

def extract_clean_sentences(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    sentences = []
    for line in lines:
        # 移除所有中括號標記及其內容
        line = re.sub(r"\[[^\]]*\]", "", line)
        # 去除前後空白
        line = line.strip()
        if line:
            sentences.append(line)
    return sentences

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("請提供輸入檔案路徑，如：python script.py input.txt")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = input_path.replace(".txt", "_cleaned.txt")

    result = extract_clean_sentences(input_path)

    with open(output_path, 'w', encoding='utf-8') as f:
        for sentence in result:
            f.write(sentence + "\n")

    print(f"已儲存乾淨句子到 {output_path}")
