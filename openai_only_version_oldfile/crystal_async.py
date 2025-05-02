#這是一個每一個主題由單一ＡＩ負責生成的結晶法
# 需要先克服ＡＩ在無相關主題的段落就會隨意找低相關性的東西溶入的問題才能運作
import os
import asyncio
import aiofiles
import re
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 主題識別 prompt (可微調)
INIT_PROMPT_TEMPLATE = """
你是一個逐航閱讀並尋找主題的ＡＩ
請嚴格按照格式列出本篇文本涉及的所有主題，不須額外任何說明：
逐行仔細閱讀文本，看到新主題時建立一個新主題名稱。
1. 主題名稱
2. 主題名稱
...

"""

# 主題處理 prompt 範本 (待你微調)
TOPIC_PROMPT_TEMPLATE = """
你是一個協助進行『結晶式整理』的專業AI輔助工具。你的任務是逐步閱讀和分析使用者提供的長篇文本，每一次使用者會提供一段文本（稱為Chunk），你需要執行以下步驟：

結晶法的意義與用途：
由於對話記錄很長 且口語對談主題可能很分散 因此要向長出結晶一樣 逐字閱讀時 把主題列為晶核  當有再次閱讀到相關主題時 若有近一步的資訊則更新蓋主題訊息 如果完全重複的話則保留現有的內容即可不必添加新資訊． 
最終晶核應該越長越多以豐富又完整且有意義為目標

結晶式整理的流程：
1. 逐行仔細閱讀文本，尋找和你負責處理的主題高度相關的內文
2. 遇到你負責處理的主題且有新資訊時，更新該「晶核」（主題）。
3. 若重複資訊，與舊的相比選擇寫入更具有代表性的或兩者皆保留。
4. 不要隨便移除已經長出的結晶的內容 尤其是Quotes 部分不可以移除
5. 每個晶核應該越長越多，以豐富又完整且有意義的還原對Problem的描述為目標．
紀錄方法：
- 在每個主題下，使用 Problem / Quotes 結構歸納。

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

請注意：
- Quotes 部分僅能通順原話語句，不可改變原話，且要寫出Speaker。
- 輸出的整理結果應條理清晰，方便高層快速理解和掌握主題及其重要細節。
- 不要隨便移除已經長出的結晶的內容 尤其是Quotes 部分不可以移除 
- 晶核應該越長越多，以豐富又完整且有意義的還原對Problem的描述為目標．
- 除了以上結晶的輸出還需要關於這一段文字的總結，與結晶法無關的一般詳細總結，幫助別人立刻了解這個段落的詳細內容。


你負責處理的主題是【{topic}】，僅從文本中擷取此主題的內容做結晶式整理。
無相關則回覆：「本段無更新」。


文本內容：
{chunk}
"""

# 拆分 chunk 邏輯
def split_chunks(text, chunk_size=2000, overlap=300):
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

# regex 抓取主題名稱清單
def extract_topics(text):
    print(re.findall(r"\d+\.\s*(.+)", text))
    return re.findall(r"\d+\.\s*(.+)", text)

# 非同步 GPT 呼叫
async def async_call_gpt(prompt, model="gpt-4o"):
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是專業的結晶式整理AI，嚴格遵守用戶提供的指引，逐行仔細分析文本並整理資訊。"},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# 建立主題資料夾
def create_topic_folders(topics, base_path):
    for topic in topics:
        topic_folder = os.path.join(base_path, topic)
        os.makedirs(topic_folder, exist_ok=True)

def get_prompt_for_next_chunk(prev_summary, new_chunk_text, chunk_index,topic):
    return f"""
請只聚焦在主題【{topic}】，僅從文本中擷取此主題的內容做結晶式更新與擴充。
這是上一輪的結晶式整理結果：
==================
{prev_summary}
==================

現在有新的文本 (Chunk #{chunk_index})，請保留舊主題的同時根據新內容更新主題名稱或新增主題，確保每個主題均包含Problem、Quotes 並在最後一樣給出與結晶法無關的總結：

新的文本內容：
{new_chunk_text}

請注意：
- Quotes 部分僅能通順原話語句，不可改變原話太多，且要寫出Speaker。
- 最終輸出的整理結果應條理清晰，方便高層快速理解和掌握主題及其重要細節。
- 不要隨便移除已經長出的結晶的內容 尤其是Quotes 部分不可以移除 
- 每個晶核應該越長越多，以豐富又完整且有意義的還原對Problem的描述為目標．
- 除了以上結晶的輸出還需要關於這一段文字的總結，與結晶法無關的一般詳細總結，幫助別人立刻了解這個段落的詳細內容。
"""


# 處理單一主題的chunk並儲存
async def process_topic_chunks(topic, chunks, base_path):
    topic_folder = os.path.join(base_path, topic)
    prev_summary = ""  # 初始為空
    for idx, chunk in enumerate(chunks, 1):
        prompt = get_prompt_for_next_chunk(prev_summary, chunk, idx, topic)
        result = await async_call_gpt(prompt)

        # 儲存本次結晶
        filename = os.path.join(topic_folder, f"chunk_{idx}.md")
        async with aiofiles.open(filename, "w", encoding="utf-8") as f:
            await f.write(result)

        # 更新累積結晶
        prev_summary = result

        print(f"✅ 主題【{topic}】Chunk {idx} 已更新完畢")

# 主程序
async def main(input_txt):
    base_path = input_txt.replace(".txt", "") + "_crystal_async"
    os.makedirs(base_path, exist_ok=True)
    # 讀取完整文本
    async with aiofiles.open(input_txt, "r", encoding="utf-8") as f:
        full_text = await f.read()

    # Step 1. 呼叫初始AI，識別所有主題
    init_prompt = INIT_PROMPT_TEMPLATE + "\n\n文本內容:\n" + full_text
    ai_response = await async_call_gpt(init_prompt)
    topics = extract_topics(ai_response)
    print("偵測到的主題:", topics)

    # Step 2. 建立主題資料夾
    create_topic_folders(topics, base_path)

    # Step 3. 將原始文本分割為 chunks
    chunks = split_chunks(full_text)

    # Step 4. 並行處理所有主題
    await asyncio.gather(*[
        process_topic_chunks(topic, chunks, base_path) for topic in topics
    ])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="並行結晶式整理")
    parser.add_argument("input_file", help="輸入的 .txt 檔案")
    args = parser.parse_args()

    asyncio.run(main(args.input_file))
