#python my_script.py --ps
#預設不影響原始行為，不加 --ps 就讓 GPT 自行探索主題
#輸出的資料夾會完全等於輸入檔名需注意
import os
from dotenv import load_dotenv
from openai import OpenAI
import argparse
import time
start_time = time.time()
# 命令列參數解析
parser = argparse.ArgumentParser(description="進行結晶式整理")
parser.add_argument("input_file", help="輸入的 .txt 檔案，例如 20250327下午蒐研組_修正版.txt")
parser.add_argument("--ps", action="store_true", help="啟用 presummary（預設為關閉）")
args = parser.parse_args()

input_file_path = args.input_file
print("take", input_file_path, "as input file")

# 依照 CMD 參數決定是否啟用 presummary
USE_PRESUMMARY= args.ps


# 載入環境變數
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 「已校正」的檔案路徑
import os


# 建立資料夾存儲每次的結晶結果
folder_name = input_file_path.replace(".txt","")
os.makedirs(folder_name, exist_ok=True)

# 最終結晶總結輸出檔
# 取出原始檔名，不含路徑
basename = os.path.basename(input_file_path).replace(".txt", ".md")

# 組合出新檔名
finalcrystalname = "final_結晶總結_" + basename
summary_output_path = os.path.join(folder_name, finalcrystalname)



# 讀取修正後內容
with open(input_file_path, "r", encoding="utf-8") as f:
    corrected_content = f.read()

# 文本重疊分割為 chunks
chunk_size = 2000
overlap_size = 300
text_chunks = []
start = 0

while start < len(corrected_content):
    end = min(start + chunk_size, len(corrected_content))
    text_chunks.append(corrected_content[start:end])
    start += chunk_size - overlap_size

# 若最後一個chunk太短，則合併回前一個chunk
if len(text_chunks) > 1:
    last_chunk_len = len(text_chunks[-1])
    # 假設以 chunk_size 的一半為門檻
    if last_chunk_len < chunk_size * 0.5:
        text_chunks[-2] += text_chunks[-1]
        text_chunks.pop()

# 初始化結晶整理結果
crystallized_summary = ""

# 完整的系統提示詞（含詳細結晶式整理流程與示範範例）
initial_system_msg = """
你是一個協助進行『結晶式整理』的專業AI輔助工具。你的任務是逐步閱讀和分析使用者提供的長篇文本，每一次使用者會提供一段文本（稱為Chunk），你需要執行以下步驟：

結晶法的意義與用途：
由於對話記錄很長 且口語對談主題可能很分散 因此要向長出結晶一樣 逐字閱讀時 把新的重要主題列為晶核  當有再次閱讀到相關主題時 若有近一步的資訊則更新蓋主題訊息 如果完全重複的話則略過 如果是新主題則是新的晶核
最終每個晶核應該越長越多以豐富又完整且有意義為目標

結晶式整理的流程：
1. 逐行仔細閱讀文本，看到新主題時建立一個新「晶核」。
2. 再次遇到相同主題且有新資訊時，更新該「晶核」。
3. 若重複資訊，與舊的相比選擇寫入更具有代表性的或兩者皆保留；若全新且不屬於現有主題，則新增新的「晶核」。
4. 不要隨便移除已經長出的結晶的內容 尤其是Quotes 部分不可以移除 除非這個結晶完全可以和另一個結晶融合
5. 每個晶核應該越長越多，以豐富又完整且有意義的還原對Problem的描述為目標．
紀錄方法：
- 在每個主題下，使用 Problem / Quotes / Summary 結構歸納。
- Quotes要紀錄Speaker例如：[Speaker_03]「實際上你的本來是3月11號要完成，現在已經是4月。」

結晶過程範例：

#晶核 [專案進度與組織圖同步]
- ## Problem
  - 組織圖的同步延遲導致專案進度的延後。
  - 組織圖的導入是專案的基本步驟，目前僅完成85%。
  - 專案進度延遲由於合作公司新人類的工程師更換及回覆遲緩。
  - 飛騰雲端系統與新人類系統的兼容問題影響進度。
  
- ## Quotes
  - [Speaker_05]「為什麼組織圖同步或是組織圖本身的導入到現在只完成了85%？」
  - [Speaker_05]「新人類的組織圖導入如果未完成，會影響後面的專案進行。」
  - [Speaker_03]「實際上你的本來是3月11號要完成，現在已經是4月。」
  - [Speaker_03]「因為這個看起來是，組織圖的導入是交給新人類，問題整個delay是噪音於新人類。」

  - ## Summary

#晶核 [專案進度與組織圖同步]
- ## Problem
  - 組織圖的同步延遲導致專案進度的延後。
  - 組織圖的導入是專案的基本步驟，目前僅完成85%。
  - 專案進度延遲原因包含新人類的工程師更換及回覆遲緩，和飛騰雲端系統的內部調整。
  - 飛騰雲端系統的修改也同樣影響組織圖進度。
  - 組織圖和流程的關聯性影響進一步專案進行。

- ## Quotes
  - [Speaker_03]「為什麼組織圖同步或是組織圖本身的導入到現在只完成了85%？」
  - [Speaker_03]「新人類的組織圖導入如果未完成，會影響後面的專案進行。」
  - [Speaker_03]「實際上你的本來是3月11號要完成，現在已經是4月。」
  - [Speaker_03]「因為這個看起來是，組織圖的導入是交給新人類，問題整個delay是噪音於新人類。」
  - [Speaker_03]「所以不完全噪音於新人類，因為我們就發現到飛騰雲端沒辦法直接過去。」
  - [Speaker_04]「組織圖要先把hierarchic設好，我才能往下，流程才有辦法往下跑。」

- ## Summary
  - 與新人類公司就工程師經驗不足和回覆問題進行進一步協商。
  - 調整飛騰雲端的系統，以促進與新人類系統的兼容性。
  - 邀請相關公司進行面對面的進度檢視會議，加快問題解決。
  - 預測剩下15%的組織圖導入工作在月底前預計完成。

請注意：
- Quotes 部分僅能通順原話語句，不可改變原話太多。
- 每次輸出都需完整呈現目前所有主題的最新整理結果。
- 最終輸出的整理結果應條理清晰，方便高層快速理解和掌握主題及其重要細節。
- 不要隨便移除已經長出的結晶的內容 尤其是Quotes 部分不可以移除 除非這個結晶完全可以和另一個結晶融合
- solution應該要是檔案中真的有出現的句子而且屬於該類別的對應解決方案
- 每個晶核應該越長越多，以豐富又完整且有意義的還原對Problem的描述為目標．
- 除了以上結晶的輸出還需要關於這一段文字的總結，與結晶法無關的一般詳細總結，幫助別人立刻了解這個段落的詳細內容。

"""



# 預設的初始晶核清單（可手動編輯）這分清單建議讓notebookLM整理
presummary = """
這裡是已經整理過的恰當的全文件主題清單(初始晶核)：

"""

# 針對第一個 chunk 的處理方式，根據 USE_PRESUMMARY 是否啟用
def get_prompt_for_first_chunk(chunk):
    if USE_PRESUMMARY:
        print("Using_PRESUMMARY")
        # 使用 presummary 作為「已存在的結晶式整理結果」
        return f"""
這是已經存在的結晶式整理結果 (presummary)：
==================
{presummary}
==================

現在請你以此為基礎，並根據下方文本更新或新增主題/晶核，保持原有清單同時進行結晶：

文本內容 (Chunk #1)：
{chunk}
"""
    else:
        # 不啟動 presummary，使用原始流程
        return f"""
這是第一個Chunk，請依照結晶式整理步驟建立初始主題整理：

文本內容 (Chunk #1)：
{chunk}
"""




def get_prompt_for_next_chunk(prev_summary, new_chunk_text, chunk_index):
    return f"""
這是上一輪的結晶式整理結果：
==================
{prev_summary}
==================

現在有新的文本 (Chunk #{chunk_index+1})，請保留舊主題的同時根據新內容更新主題名稱或新增主題，確保每個主題均包含Problem、Quotes，以及Solution（如適用） 並在最後一樣給出與結晶法無關的總結：

新的文本內容：
{new_chunk_text}

請注意：
- Quotes 部分僅能通順原話語句，不可改變原話太多。
- 每次輸出都需完整呈現目前所有主題的最新整理結果。
- 最終輸出的整理結果應條理清晰，方便高層快速理解和掌握主題及其重要細節。
- 不要隨便移除已經長出的結晶的內容 尤其是Quotes 部分不可以移除 除非這個結晶完全可以和另一個結晶融合
- solution應該要是檔案中真的有出現的句子而且屬於該類別的對應解決方案
- 每個晶核應該越長越多，以豐富又完整且有意義的還原對Problem的描述為目標．
- 除了以上結晶的輸出還需要關於這一段文字的總結，與結晶法無關的一般詳細總結，幫助別人立刻了解這個段落的詳細內容。

"""

# 處理每個 Chunk
# 處理每個 Chunk
for idx, chunk in enumerate(text_chunks):
    print(f"正在處理第 {idx+1}/{len(text_chunks)} 個 Chunk...")

    if idx == 0:
        user_prompt = get_prompt_for_first_chunk(chunk)
    else:
        user_prompt = get_prompt_for_next_chunk(crystallized_summary, chunk, idx)

    messages = [
        {"role": "system", "content": initial_system_msg},
        {"role": "user", "content": user_prompt}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )

    updated_summary = response.choices[0].message.content
    crystallized_summary = updated_summary

    evolving_filename = os.path.join(folder_name, f"crystallized_after_chunk_{idx+1}.md")
    with open(evolving_filename, "w", encoding="utf-8") as f:
        f.write(crystallized_summary)

    print(f"已將第 {idx+1} 個 Chunk 的結晶後狀態存入 {evolving_filename}")

# ==============================
# 最終結晶總結階段
# ==============================

# 讀取所有 chunk 的中間輸出文件
all_summaries = []
for idx in range(1, len(text_chunks) + 1):
    intermediate_filename = os.path.join(folder_name, f"crystallized_after_chunk_{idx}.md")
    with open(intermediate_filename, "r", encoding="utf-8") as f:
        all_summaries.append(f.read())

# 合併所有 summary 為最終總結的輸入
# 先計算所有結晶段落合併結果
combined_summaries = "\n".join(all_summaries)

# 構建最終總結的 Prompt
final_summary_prompt = (
    "以下是所有分段處理後的結晶結果，請你整合並產出最終完整總結：\n"
    "=========================\n"
    f"{combined_summaries}\n"
    "=========================\n"
    "請確保：\n"
    "- 內容條理清晰，合併重複晶核Quotes與但保留所有重要資訊。\n"
    "- 不要遺漏任何主題，確保所有主題都有完整的問題 (Problem)、引用 (Quotes) 和解決方案 (Solution)。\n"
    "- 選擇最具代表性跟主題關聯且資訊明確的 Quotes，並根據所有段落進行歸納整理。\n"
    "- 將“晶核”這個文字改成 “討論主題”。\n"
    "- 請在最終寫出一份完整的給高層看的會議報告。\n"
    
)



# 呼叫 GPT 進行最終總結
messages = [
    {"role": "system", "content": initial_system_msg},
    {"role": "user", "content": final_summary_prompt}
]

response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)

final_summary = response.choices[0].message.content

# 將最終總結結果存入 summary_output_path
with open(summary_output_path, "w", encoding="utf-8") as f:
    f.write(final_summary)

print(f"最終結晶整理已完成，存放於 {summary_output_path}")
end_time = time.time()
elapsed_time = end_time - start_time
print(f"🚀 總執行時間：{elapsed_time:.2f} 秒")