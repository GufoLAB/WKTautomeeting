"""# 1. 把 stdout/stderr 分開抓
python 2chunks_summary.py /home/henry/AuMeet_package/2025Feb_NSTM_meet_copy/shorten_topics 1>step2_out.txt 2>step2_err.txt

# 2. 檢視 stdout
echo "=== STDOUT ==="
cat out.txt

# 3. 檢視 stderr（日誌）
echo "=== STDERR ==="
cat err.txt

# 4. 用 stdout 裡的路徑確認檔案存在
csv_path=$(cat out.txt)
echo "CSV 檔案列表："
ls -l "$csv_path"
如果：

out.txt 裡只有類似 /path/to/md_folder/chunks_summaries.csv

err.txt 裡有你的處理日誌

ls -l 能看到 chunks_summaries.csv 和 _brief.csv

就代表這支程式「沒壞」，可以安心交給 main.py 串接了！
"""


import os
import re
import argparse
import time
import pandas as pd
from dotenv import load_dotenv
import ollama
from tqdm import tqdm
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL
from zhconv_rs import zhconv
import  sys,  pathlib

def run(input_dir: str) -> pathlib.Path:
    load_dotenv()

    MAX_CHARS = 6000

    def ai_response(messages, max_tokens=6000):
        response = ollama.Client(host=OLLAMA_URL).chat(
            model=AI_MODEL,
            messages=messages
        )
        assistant_reply = response['message']['content'].strip()
        if AI_MODEL.startswith("deepseek"):
            assistant_reply = re.sub(r'<think>(.*)</think>', '', assistant_reply, flags=re.DOTALL).strip()
        return zhconv(assistant_reply, "zh-tw")

    def sort_key(fname):
        m = re.match(r'(\d+)_', fname)

        return int(m.group(1)) if m else float('inf')
    def generate_summary_tags_natural(text):
        # ⚠️ Gemma3 特性：指令必須放在內容之後！
        prompt = f"""逐字稿片段內容如下：
{text}

===== 以下是你的任務 =====
你是專業會議記錄AI。請用不超過150字準確摘要上述逐字稿的重點事項。

【必須包含】：
1. 所有重要數字、金額（含單位）
2. 完整人名（中文＋英文，如「Brenda Tsai (蔡素貞)」）
3. 決策事項與責任歸屬（誰負責什麼）
4. 具體時間與地點
5. 組織/單位名稱
6. 待辦事項與追蹤項目

【禁止】：
- 不可省略數字或改成「約」「大概」
- 不可省略責任人
- 不可使用「近期」「稍後」等模糊時間
- 無關內容則不寫

請立即開始摘要："""
        if len(text) > MAX_CHARS:
            print(f"⚠️ 超出字數限制（{len(text)}字），跳過", file=sys.stderr)
            return None
        messages = [{"role": "user", "content": prompt}]
        return ai_response(messages)

    def generate_summary_csv(md_folder):
        start_time = time.time()
        results = []
        md_files = sorted(os.listdir(md_folder), key=sort_key)##
        #for fname in sorted(os.listdir(md_folder)):
        for fname in md_files:  
            print("處理中：",fname, file=sys.stderr)
            if fname.endswith(".md"):
                with open(os.path.join(md_folder, fname), 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if len(content) < 2:
                        print(f"⚠️ 跳過內容不足：{fname}", file=sys.stderr)
                        continue
                    try:
                        summary = generate_summary_tags_natural(content)
                        if summary:
                            results.append({"chunk_id": fname[:-3], "summary": summary, "text": content})
                    except Exception as e:
                        print(f"❌ 處理 {fname} 時發生錯誤: {e}", file=sys.stderr)

        df = pd.DataFrame(results)
        
        if df.empty:
            print("⚠️ 沒有可用的摘要，未產生任何CSV", file=sys.stderr)
            return None
        csv_path = os.path.join(md_folder, "chunks_summaries.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        df[["chunk_id", "summary"]].to_csv(csv_path.replace(".csv", "_brief.csv"), index=False, encoding="utf-8-sig")
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"執行時間：{elapsed:.2f} 秒", file=sys.stderr)
        print(f"✅ 全部完成，寫入：\n{csv_path}\n{csv_path.replace('.csv', '_brief.csv')}", file=sys.stderr)
        return csv_path

   # 真的執行並回傳

    csv_path = generate_summary_csv(input_dir)

    if csv_path is None:
        sys.exit(1)
    return pathlib.Path(csv_path)





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