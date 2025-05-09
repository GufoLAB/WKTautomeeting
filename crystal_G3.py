#python crystal_G3.py --ps
#預設不影響原始行為，不加 --ps 就讓 GPT 自行探索主題
import os
from dotenv import load_dotenv
from openai import OpenAI
import argparse

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
chunk_size = 800
overlap_size = 100
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

# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------
import os, re
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import ollama
from zhconv_rs import zhconv

from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# 設定 統一system prompt，並動態記錄版本資訊
#import system_prompt
#global prompt_choice, prompt_version
#prompt_function = system_prompt.system_prompt  # 取得 system_prompt 函式
#prompt_choice = prompt_function()  # 執行函式以取得提示內容
#prompt_version = f"{prompt_function.__module__}.{prompt_function.__name__}"


def ai_response(conversation_history, max_tokens=1000):
    if BACK_END_MODEL == 'openai':
        response = openai_client.chat.completions.create(
            model=AI_MODEL, 
            messages=conversation_history
        )
        print("model = openai")
        assistant_reply = response.choices[0].message.content
    elif BACK_END_MODEL == 'ollama':
        response = ollama.Client(host=OLLAMA_URL).chat(
            model=AI_MODEL, 
            messages=conversation_history
        )
        print("model = ollama "+str(AI_MODEL))
        assistant_reply = response['message']['content'].strip()
        if AI_MODEL.startswith("deepseek"):
            assistant_reply = re.sub(r'<think>(.*)</think>', '', assistant_reply, flags=re.DOTALL).strip()
    assistant_reply = zhconv(assistant_reply, "zh-tw")
    return assistant_reply


def dialogue_summary(messages, summary_token_length=1000):
    summary_prompt = [
        {"role": "system", "content": "你是個摘要助理，請幫忙摘要以下對話內容。"},
        {"role": "user", "content": "請將以下對話摘要成簡短重點:"},
    ] + messages
    if BACK_END_MODEL == 'openai':
        response = openai_client.chat.completions.create(
            model=AI_MODEL,
            messages=summary_prompt,
            max_tokens=summary_token_length
        )
        summary = response.choices[0].message.content
    elif BACK_END_MODEL == 'ollama':
        response = ollama.Client(host=OLLAMA_URL).chat(
            model=AI_MODEL, 
            messages=[{"role": "user", "content": summary_prompt}]
        )
        summary = response['message']['content'].strip()
    return zhconv(summary, "zh-tw") # 轉換成繁體中文

import time
import threading


def print_dot(stop_event):
    while not stop_event.is_set():
        print(".", end="", flush=True)
        time.sleep(1)

#response = ai_response(History_str, max_tokens=1000)


# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------



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
5. 每個晶核應該越長越多，以豐富又完整且有意義的Summary為目標．
紀錄方法：
- 在每個主題下，使用 Quotes / Summary 結構歸納。

結晶過程範例：

#晶核 [票務（售票問題）]
- ## Quotes
- 「假日時我們售票大排長龍，常有民眾抱怨排隊時間太久。」

- ## Summary
- 假日售票排隊時間過長，導致民眾抱怨。


#晶核 [多語言溝通]
- ## Quotes
- 「還有外國遊客問的問題，我們都只能用破英文回應，很花時間。」
- ## Summary
- 外國遊客語言不通，依賴人工簡易英文回覆。



#晶核 [信息整合與系統更新]
- ## Quotes
  - 「是否有辦法自動整合各種平台信息，而不是人工輸入？」
  - 「我今天輸出的時候，我要有一些資料能夠提供給他。」
  - 「這其實就是今天的關鍵痛點啦。」
- ## Summary
  - 信息分散不同平台，影響服務台掌握活動訊息的能力。
  - 需系統化整合信息以降低人力負擔和提升運作效率。
  - 館內不同區域的活動信息需即時更新並簡單查詢。




最終結晶範例：
#晶核 [信息整合與系統更新]
- ## Quotes 
  -「是否能夠自動整合各種平台資訊，而非依賴人工輸入？」
  -「這正是我們今天討論的關鍵問題。」
  -「未來，我們應開發一個系統，統一搜索並有效管理資訊，以減少遺漏。」
  -「目前，封廳公告的發布方式不統一，可能導致資訊不清楚。」
  -「民眾可能會對這種狀況感到困惑。」
  -「我馬上想到三個重點。首先，應整合活動訊息，建立同仁可查詢的平台介面。」
  -「目前這些資訊多為紙本，應轉換為電子化管理。」
- ## Summary
  - 信息分散不同平台，影響服務台掌握活動訊息的能力。
  - 需系統化整合信息以降低人力負擔和提升運作效率。
  - 館內不同區域的活動信息需即時更新並簡單查詢。
  - 對場地和活動情報進行統一管理是應對關鍵痛點的方法。
  - 封廳或展廳的封閉信息需即時更新，以避免服務台的尷尬。
  - 線上客服系統需結合自動化方案，降低人力依賴和成本效益考量。
  - 需要將紙本資料轉成電子化以便管理和查詢。
  - 開發統一的搜索系統來統一各平台的活動信息管理，减少信息漏失。
  - 確保展廳封閉信息在最新消息中得到即時更新。
  - 提供查詢平台界面方便同仁查詢和更新。
  - 紙本資料轉成電子化以便查詢和管理。
---
#晶核 [智能館員與多語言溝通]
- ## Quotes
  -「訪客可以直接與這位虛擬館員對話，並可選擇使用中文、英文或日語。」
  -「我想像的是一位虛擬館員，能夠與訪客進行互動。」
  -「AI 可以加速語言翻譯，並可搭配現有的語音或圖像素材來生成字幕或其他輔助手段。」
  -「我們的初步規劃是支援中文、英文、日語、韓語和台語，是否還需要其他語言？」
- ##Summary
  - 外國遊客語言不通，目前依賴英文溝通面臨挑戰。
  - 設想虛擬智能館員可進行多語言對話。
  - 增加不同語言的支持，以適應來自各國的遊客需求。
  - 語言服務需除中英之外，擴展至日韓和台語。
  - 提供中英文對照的平板檔案或票價說明。
  - 使用電子化且多語言的查詢系統來解決語言問題。
  - 使用AI加速翻譯工作流程，協助生成草稿，最終由人校對。
---

請注意：
- Quotes 部分僅能通順原話語句，不可改變原話太多。
- 每次輸出都需完整呈現目前所有主題的最新整理結果。
- 最終輸出的整理結果應條理清晰，方便高層快速理解和掌握主題及其重要細節。
- 不要隨便移除已經長出的結晶的內容 尤其是Quotes 部分不可以移除 除非這個結晶完全可以和另一個結晶融合
- 每個晶核應該越長越多，以豐富又完整且有意義的還原對Summary的描述為目標．
- 除了以上結晶的輸出還需要關於這一段文字的總結，在文末最後一樣寫一段小總結，幫助別人立刻了解這個段落的詳細內容。

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
這是上一輪的結晶式整理結果請保留主題並依據規則更新和合併：
==================
{prev_summary}
==================

現在有新的文本 (Chunk #{chunk_index+1})，即時舊主題在這個Chunk之中沒有相關內容也要保留舊主題的同時根據新內容更新主題名稱或新增主題，確保每個主題均包含Quotes、Summary 並在文末最後一樣寫一段小總結：

新的文本內容：
{new_chunk_text}

請注意：
- Quotes 部分僅能通順原話語句，不可改變原話太多。
- 每次輸出都需完整呈現目前所有主題的最新整理結果。
- 最終輸出的整理結果應條理清晰，方便高層快速理解和掌握主題及其重要細節。
- 不要隨便移除已經長出的結晶的內容 尤其是Quotes 部分不可以移除 除非這個結晶完全可以和另一個結晶融合
- 每個晶核應該越長越多，以豐富又完整且有意義的還原對Summary的描述為目標．
- 除了以上結晶的輸出還需要關於這一段文字的總結，在文末最後一樣寫一段小總結，幫助別人立刻了解這個段落的詳細內容。

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

    updated_summary = ai_response(messages, max_tokens=1000)##呼叫Ｇ3
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
    "- 內容條理清晰，合併重複晶核但保留所有重要資訊。\n"
    "- 不要遺漏任何主題，確保所有主題都有完整的問題 (Problem)、引用 (Quotes) 和解決方案 (Solution)。\n"
    "- 保持原有的 Quotes，並根據所有段落進行歸納整理。\n"
)



# 呼叫 GPT 進行最終總結
messages = [
    {"role": "system", "content": initial_system_msg},
    {"role": "user", "content": final_summary_prompt}
]


final_summary =ai_response(messages, max_tokens=1000)##呼叫Ｇ3

# 將最終總結結果存入 summary_output_path
with open(summary_output_path, "w", encoding="utf-8") as f:
    f.write(final_summary)

print(f"最終結晶整理已完成，存放於 {summary_output_path}")
