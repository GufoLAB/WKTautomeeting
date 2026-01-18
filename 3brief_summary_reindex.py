import os, sys, argparse, pathlib
import pandas as pd
def run(input_CSV: str) -> pathlib.Path:
    # === Step 1: Get input path from argv ===

    # === Step 2: Read input file with format correction ===
    # 使用 skip_blank_lines=True 忽略空行，並確保 quotechar 和 quoting 正確處理多行文字
    df = pd.read_csv(
        input_CSV,
        skip_blank_lines=True,  # 忽略空行
        quotechar='"',         # 確保雙引號包圍的多行文字正確解析
        quoting=0,             # 強制使用引號（0 表示 QUOTE_MINIMAL）
        escapechar='\\',       # 如果有轉義字元，可視情況調整
        on_bad_lines='skip'    # 如果有格式錯誤的行，自動跳過
    )
    
    # === Step 2.5: Clean summary column (remove extra newlines and strip whitespace) ===
    if 'summary' in df.columns:
        df['summary'] = df['summary'].astype(str).apply(lambda x: ' '.join(x.split()))  # 移除多餘換行與空白，轉為單行文字
        # === Step 3: Drop title column and re-index chunk_id ===
        #df = df.drop(columns=['title', 'tags'])
        df['chunk_id'] = range(1, len(df) + 1)

    # === Step 4: Reorder columns ===
    # ⚠️ V2 優化：保留 text 欄位！提供 78% 更多信息給後續步驟
    df = df[['chunk_id', 'summary', 'text']]

    # === Step 5: Create output folder and path ===
    input_dir = os.path.dirname(input_CSV)
    input_file = os.path.basename(input_CSV)
    filename_wo_ext = os.path.splitext(input_file)[0]
    output_dir = os.path.join(input_dir, f"{filename_wo_ext}_output")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{filename_wo_ext}_reindexed.csv")

    # === Step 6: Save output file ===
    df.to_csv(output_path, index=False)
    print(f"Saved: {output_path}", file=sys.stderr)
    return pathlib.Path(output_path)

def main():
    parser = argparse.ArgumentParser(
        description="從主題 md 資料夾產生摘要 CSV 並回傳路徑"
    )
    parser.add_argument(
        "folder",
        help="上一步輸出的主題 md 資料夾路徑"
    )
    args = parser.parse_args()
    out_csv = run(args.folder)
    # ★ stdout 只印這一行，讓主控腳本抓
    print(out_csv)

if __name__ == "__main__":
    main()
