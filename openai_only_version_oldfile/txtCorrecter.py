from openai import OpenAI
import os
from dotenv import load_dotenv  # pip install python-dotenv
import re

# 加载 .env 文件中的 API 密钥
load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# 讀取 TXT 檔案內容
import os
import sys

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

# 每 3000 字拆分一次
chunk_size = 3000
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
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="gpt-4o"
    )
    
    # 取得修正後的內容
    corrected_text = chat_completion.choices[0].message.content
    fixed_text += corrected_text + "\n"
    
# 將修正後的內容寫入新檔案
with open(output_file_path, "w", encoding="utf-8") as file:
    file.write(fixed_text)

print(f"修正後的文本已保存至 {output_file_path}")
