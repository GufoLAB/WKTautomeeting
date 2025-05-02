#一開始的主題檢索很關鍵 是要搜集大量小主題還是說 列出最重點的主題 
# 或是交由高階notebooklm判斷出來的主題呈現 均還能調整與測試
#這東西輸出基本根topic split差不多...
#目前採用cus_topic .append 到ＡＩ自動辨識主題
cus_topic=["組織與職責劃分","市場銷售與目標","外部環境變動與關稅的影響","公司未來發展方向","人才培養與學習發展"]
import os
import tiktoken
import asyncio
import aiofiles
import time
import re
from dotenv import load_dotenv
from openai import AsyncOpenAI
start_time = time.time()
load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 主題識別 prompt (可微調)
INIT_PROMPT_TEMPLATE = """
你是一個逐航閱讀並尋找主題的ＡＩ
請嚴格按照格式列出本篇文本涉及的所有主題，不須額外任何說明：
逐行仔細閱讀文本，看到新主題時建立一個新主題名稱，然後根據全文 重新思考以上主題哪些應該合併以後才輸出。
1. 主題名稱
2. 主題名稱
...


"""

# 主題處理 prompt 範本 (待你微調)
TOPIC_PROMPT_TEMPLATE = """
你是一個協助進行『結晶式整理』的專業AI輔助工具。你的任務是逐步閱讀和分析使用者提供的長篇文本，每一次使用者會提供一段文本（稱為Chunk），你需要執行以下步驟：

結晶法的意義與用途：
由於對話記錄很長 且口語對談主題可能很分散 因此要向長出結晶一樣 逐字閱讀時 把主題列為晶核  當有再次閱讀到相關主題時 若有近一步的資訊則更新蓋主題訊息 如果完全重複的話則略過 
最終晶核應該越長越多以豐富又完整且有意義為目標

結晶式整理的流程：
1. 逐行仔細閱讀文本，只尋找和你負責處理的主題高度相關的內文
2. 遇到你負責處理的主題且有新資訊時，更新Problem / Quotes。
4. 不要隨便移除已經長出的結晶的內容 尤其是Quotes 部分不可以移除
5. 每個晶核應該越長越多，以豐富又完整且有意義的還原對主題的描述為目標．
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
無相關就不需要更新現有內容，務必只求與主題相關的


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
    return re.findall(r"\d+\.\s*(.+)", text)

# 全域 token 計數器
total_prompt_tokens = 0
total_completion_tokens = 0

def count_tokens(text, model="gpt-4o"):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


# 非同步 GPT 呼叫
async def async_call_gpt(prompt, model="gpt-4o"):
    global total_prompt_tokens, total_completion_tokens
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt}
        ]
    )
    usage = response.usage
    if usage:
        total_prompt_tokens += usage.prompt_tokens
        total_completion_tokens += usage.completion_tokens
    return response.choices[0].message.content
# 建立主題資料夾
def create_topic_folders(topics, base_path):
    for topic in topics:
        topic_folder = os.path.join(base_path, topic)
        os.makedirs(topic_folder, exist_ok=True)

def get_prompt_for_next_chunk(prev_summary, new_chunk_text, chunk_index,topic):
    return f"""
請只聚焦在主題【{topic}】，僅從文本中擷取此主題的內容非常相關的部分做更新與擴充，若不相關就重複寫入上一輪的結晶式整理結果，可能整個chunk都沒有這個主題的事情會經常發生。
這是上一輪的結晶式整理結果：
==================
{prev_summary}
==================

現在有新的文本 (Chunk #{chunk_index})，請保留舊主題的同時根據新內容，只更新與【{topic}】相關的Problem、Quotes，若不相關就重複寫入上一輪的結晶式整理結果，可能整個chunk都沒有這個主題的事情會經常發生．
並在最後一樣給出總結．

新的文本內容：
{new_chunk_text}

請注意：
- Quotes 部分僅能通順原話語句，不可改變原話太多，且要寫出Speaker。
- 最終輸出的整理結果應條理清晰，方便高層快速理解和掌握主題及其重要細節。
- 不要隨便移除已經長出的主題的內容 尤其是Quotes 部分不可以移除 
- 每個主題應該越長越多，以豐富又完整且有意義的還原對Problem的描述為目標．
- 除了以上主題的輸出還需要關於這一段文字的總結，與主題無關的一般詳細總結，幫助別人立刻了解這個段落的詳細內容。
"""
#def get_prompt_for_next_chunk(prev_summary, new_chunk_text, chunk_index, topic):
#    return f"""
#你負責的主題是【{topic}】。
#
#請在輸出中**保留原有的 Problem / Quotes**（即使此 chunk 沒有新資訊也要回傳），
#你每次輸出的內容必須是「目前為止完整的主題結晶狀態」，不是只回應新的。
#
#這是上一輪的結晶式整理結果：
#==================
#{prev_summary}
#==================
#
#現在有新的文本 (Chunk #{chunk_index})，請保留原有內容的基礎上，僅對【{topic}】相關部分進行更新與擴充。
#如果本段內容與此主題無關，就不需改動原內容（仍請完整回傳）。
#
#新的文本內容：
#{new_chunk_text}
#
#請注意：
#- Quotes 部分僅能通順原話語句，不可改變原話太多，且要寫出Speaker。
#- 不要刪除已有的 Problem / Quotes 除非能合併並說得更完整。
#- 最終輸出的整理結果應條理清晰，方便高層快速理解。
#- 除了以上的Problem / Quotes輸出，請在最後提供此 chunk 的總結。
#"""


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


    # Step 1. 主題辨識 + 自訂主題 append
    init_prompt = INIT_PROMPT_TEMPLATE + "\n\n文本內容:\n" + full_text
    ai_response = await async_call_gpt(init_prompt)
    topics = extract_topics(ai_response)

    # ✅ 加入自訂主題
    topics += cus_topic

    # ✅ 去除重複主題（如果自動辨識和你自己加的有重疊）
    topics = list(set(topics))

    print("最終主題列表:", topics)
    # 預估 token 數
    estimated_tokens = count_tokens(full_text)
    estimated_total = estimated_tokens * len(topics)
    print(f"📐 估算原文 token 數: {estimated_tokens}")
    print(f"📐 預估總 token 消耗量（估算×主題數）: {estimated_total}")


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

    #計算時間
    end_time = time.time()
    elapsed_time = end_time - start_time
    # 實際 token 統計輸出
    print(f"📊 實際 token 使用統計：")
    print(f"- Prompt tokens: {total_prompt_tokens}")
    print(f"- Completion tokens: {total_completion_tokens}")
    print(f"- 總 token 數：{total_prompt_tokens + total_completion_tokens}")

    print(f"🚀 總執行時間：{elapsed_time:.2f} 秒")