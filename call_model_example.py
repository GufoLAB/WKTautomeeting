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


if __name__ == "__main__":
    conversation_history=[]
    while True:
        Userinput=input(":")
        #控制歷史紀錄只有最近兩輪4條
        if len(conversation_history)>4:
            conversation_history=conversation_history[1:]
        
        #把歷史紀錄合併為長文字型態
        history_str=""
        for i in conversation_history:
            history_str=history_str+" "+str(i)
        history_str=history_str+Userinput
        History_str=[{"role": "user", "content":history_str}]
        print("History_str",History_str)

        #建立第二線程
        stop_event = threading.Event()
        dot_thread = threading.Thread(target=print_dot, args=(stop_event,))
        dot_thread.start()

        try:
            response = ai_response(History_str, max_tokens=1000)
        finally:
            stop_event.set()
            dot_thread.join()

        print("\nDone.")
        conversation_history.append({"role": "user", "content":Userinput})
        conversation_history.append({"role": "user", "content":response})
        print(response)
