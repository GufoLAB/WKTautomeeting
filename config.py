# config.py
import os
import logging

from openai import OpenAI

from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# Logging 設定
LOGGING_FILE = os.getenv('LOGGING_FILE', "data/info.log")
logging.basicConfig(filename=LOGGING_FILE, level=logging.INFO, 
                    format='%(asctime)s %(levelname)s: %(message)s')

# 全域參數設定
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
TRANSCRIPT_DIR = os.getenv("TRANSCRIPT_DIR", "transcripts")

# 建立必要目錄
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# 模型與後端設定
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "large")
WHISPER_ENGINE = os.getenv("WHISPER_ENGINE", "openai")  # or faster
BACK_END_MODEL = os.getenv("BACK_END_MODEL", "openai")    # or ollama
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o")                # or deepseek:r1-32b
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-")  # 若使用 OpenAI API，請提供 API 金鑰

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Redis 與資料庫設定
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DATABASE_FILE = os.getenv('DATABASE_FILE', "data/dialogue.db")
os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)

SupportedAudioFormats = ("wav", "mp3", "m4a", "aac", "flv", "ogg", "flac", # "raw" not supported
                         "mp4", "wma", "aiff") # 必須是 tuple，不可以是 list

if __name__ == '__main__':
    print("Configuration:")
    print("BASE_URL:", BASE_URL)
    print("UPLOAD_DIR:", UPLOAD_DIR)
    print("TRANSCRIPT_DIR:", TRANSCRIPT_DIR)
    print("OLLAMA_URL:", OLLAMA_URL)
    print("WHISPER_MODEL_SIZE:", WHISPER_MODEL_SIZE)
    print("WHISPER_ENGINE:", WHISPER_ENGINE)
    print("BACK_END_MODEL:", BACK_END_MODEL)
    print("AI_MODEL:", AI_MODEL)
    print("REDIS_URL:", REDIS_URL)
    print("DATABASE_FILE:", DATABASE_FILE)
