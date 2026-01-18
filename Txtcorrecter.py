import os
import re
import argparse
import time
from dotenv import load_dotenv
from tqdm import tqdm
from zhconv_rs import zhconv
import ollama
from config import BACK_END_MODEL, AI_MODEL, OLLAMA_URL
from openai import OpenAI
import sys
# ========= AI 初始化 =========
starttime=time.time()
print(starttime)
load_dotenv()
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def ai_response(conversation_history, max_tokens=3000):
    if BACK_END_MODEL == 'openai':
        response = openai_client.chat.completions.create(
            model=AI_MODEL,
            messages=conversation_history
        )
        assistant_reply = response.choices[0].message.content
    elif BACK_END_MODEL == 'ollama':
        response = ollama.Client(host=OLLAMA_URL).chat(
            model=AI_MODEL,
            messages=conversation_history
        )
        assistant_reply = response['message']['content'].strip()
        if AI_MODEL.startswith("deepseek"):
            assistant_reply = re.sub(r'<think>(.*)</think>', '', assistant_reply, flags=re.DOTALL).strip()
    assistant_reply = zhconv(assistant_reply, "zh-tw")
    return assistant_reply


if len(sys.argv) < 2:
    print("請提供輸入檔案路徑，例如：python your_script.py 檔名.txt")
    sys.exit(1)

input_file_path = sys.argv[1]
print("take "+input_file_path+' as input file')

# 生成修正後的檔案名稱
output_file_path = input_file_path.replace(".txt", "") + "_修正版.txt"

print(output_file_path)  # 應該輸出 "your_input_file_修正版.txt"

with open(input_file_path, "r", encoding="utf-8") as file:
    content = file.read()

# 每 1300 字拆分一次
chunk_size = 1300
text_chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

# 存儲修正後的內容
fixed_text = ""

for i, chunk in enumerate(text_chunks):
    print(f"Processing chunk {i+1}/{len(text_chunks)}...")
    
    # 呼叫 GPT-4o API
    messages = [
        {"role": "system", "content": "你是一個專業的校對助手，請幫助修正以下文本的錯別字和漏字，針對特別難以辨別的部分應參考上下文來猜測語意，但一般來情況盡量保留原語句僅修正錯字與漏字．不要輸出修正後的內容以外的其他文字會妨礙我寫進新的正式文檔"}
    ]
    #可以增加用戶指定的錯次轉換
    #if custome==True:
    #    messages.append()

    
    messages.append({"role": "user", "content": chunk})

    
    # 取得修正後的內容
    corrected_text = ai_response(messages)
    fixed_text += corrected_text + "\n"
    
# 將修正後的內容寫入新檔案
with open(output_file_path, "w", encoding="utf-8") as file:
    file.write(fixed_text)

print(f"修正後的文本已保存至 {output_file_path}")
endtime=time.time()
print(endtime-starttime)