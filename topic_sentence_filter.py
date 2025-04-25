import os
import tiktoken
import asyncio
import aiofiles
import time
import re
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 自訂主題清單
cus_topic = [
    "組織與職責劃分",
    "市場銷售與目標",
    "外部環境變動與關稅的影響",
    "公司未來發展方向",
    "人才培養與學習發展"
]

# 主題識別 prompt
INIT_PROMPT_TEMPLATE = """
你是一個逐航閱讀並尋找主題的ＡＩ
請嚴格按照格式列出本篇文本涉及的所有主題，不須額外任何說明：
逐行仔細閱讀文本，看到新主題時建立一個新主題名稱，然後根據全文重新思考以上主題哪些應該合併以後才輸出。
1. 主題名稱
2. 主題名稱
...
"""

def extract_topics(text):
    return re.findall(r"\d+\.\s*(.+)", text)

# GPT relevance 判斷 prompt
def make_relevance_prompt(sentence, topic, context=""):
    return f"""
你是一個語意判斷 AI。

請閱讀以下【句子】與【主題】，判斷這個句子是否與這個主題高度相關。

- 若相關（句子對該主題具有直接貢獻意義），請回覆：true
- 若無關或只是閒聊背景資訊，請回覆：false
- 不需要提供任何說明或其他文字，只要回覆 true 或 false。

主題：
{topic}

句子：
{sentence}

（可參考上下文資訊如下，但非必要）：
{context}
"""

# GPT 非同步呼叫
# 加入 token 統計
total_prompt_tokens = 0
total_completion_tokens = 0

def count_tokens(text, model="gpt-4o"):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

async def async_call_gpt(prompt, model="gpt-4o"):
    global total_prompt_tokens, total_completion_tokens
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    usage = response.usage
    if usage:
        total_prompt_tokens += usage.prompt_tokens
        total_completion_tokens += usage.completion_tokens
    return response.choices[0].message.content.strip().lower()

# 判斷是否相關
async def is_relevant_to_topic(sentence, topic, context=""):
    prompt = make_relevance_prompt(sentence, topic, context)
    result = await async_call_gpt(prompt)
    return result == "true"

# 切句工具（簡單句點斷句，可再加強）
def split_sentences(text):
    return re.split(r'[\n。！？]', text)

# 處理單一 chunk 的句子過濾
async def process_chunk(chunk_text, topic, output_dir, idx):
    sentences = split_sentences(chunk_text)
    relevant_sentences = []
    for sent in sentences:
        if sent.strip():
            relevant = await is_relevant_to_topic(sent, topic, context=chunk_text)
            if relevant:
                relevant_sentences.append(sent.strip())

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{topic}_chunk_{idx}.txt")
    async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
        await f.write("\n".join(relevant_sentences))
    print(f"✅ 主題【{topic}】Chunk {idx} 篩選完成，共 {len(relevant_sentences)} 句相關")

# 主程式
async def main(input_txt):
    start_time = time.time()

    async with aiofiles.open(input_txt, "r", encoding="utf-8") as f:
        full_text = await f.read()

    # 預估 token
    estimated_tokens = count_tokens(full_text)
    print(f"\U0001F4D0 估算原文 token 數: {estimated_tokens}")

    # GPT 主題辨識
    init_prompt = INIT_PROMPT_TEMPLATE + "\n\n文本內容:\n" + full_text
    ai_response = await async_call_gpt(init_prompt)
    topics = extract_topics(ai_response)
    topics += cus_topic
    topics = list(set(topics))
    print("\n🎯 主題列表:", topics)

    # 切 chunk
    chunks = split_chunks(full_text)

    # 輸出資料夾名稱
    output_dir = "topic_sentence_filter"

    # 處理每個主題與 chunk
    for topic in topics:
        for idx, chunk in enumerate(chunks, 1):
            await process_chunk(chunk, topic, output_dir, idx)

    end_time = time.time()
    print("\n📊 Token 使用統計：")
    print(f"- Prompt tokens: {total_prompt_tokens}")
    print(f"- Completion tokens: {total_completion_tokens}")
    print(f"- 總 token 數：{total_prompt_tokens + total_completion_tokens}")
    print(f"\U0001F680 總執行時間：{end_time - start_time:.2f} 秒")

# 分段邏輯
def split_chunks(text, chunk_size=2000, overlap=300):
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="根據主題過濾相關句子")
    parser.add_argument("input_file", help="輸入的 .txt 檔案")
    args = parser.parse_args()

    asyncio.run(main(args.input_file))