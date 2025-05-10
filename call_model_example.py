

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
