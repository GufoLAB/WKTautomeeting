# 🚀 AuMeet_package 快速使用指南

## 30秒快速開始

### 1. 安裝依賴
```bash
pip install -r requirements-core.txt
```

### 2. 設定環境
```bash
# 複製環境檔案
cp .env.example .env

# 編輯 .env 檔案，設定你的API金鑰
BACK_END_MODEL=openai
AI_MODEL=gpt-4o  
OPENAI_API_KEY=your-api-key-here
```

### 3. 執行處理
```bash
# 完整自動化處理
python integrated_main.py /path/to/your/transcript.txt

# 或測試現有資料
python integrated_main.py --test
```

## 🎯 輸入檔案準備

### 支援的格式
```
[Speaker_1] 大家好，今天我們要討論預算問題。
[Speaker_2] 根據財務報告，我們需要削減20%的開支。
[Speaker_1] 具體要削減哪些項目？
```

### 快速清理原始逐字稿
```bash
# 如果你的檔案有時間戳，先清理
python shorten_transcript.py raw_transcript.txt > clean_transcript.txt
```

## 📊 處理結果

執行完成後，你會得到：
- `📄 topic_name.md` - 各主題的結構化報告
- `📄 topic_name_cleaned.md` - 清理後的最終報告
- `📊 *.csv` - 中間處理資料（用於調試）

## ⚡ 常用指令

```bash
# 完整處理（推薦）
python integrated_main.py transcript.txt

# 測試模式
python integrated_main.py --test

# 實驗性增強處理
python enhanced_pipeline.py transcript.txt

# 單獨清理已生成的報告
python clean_md.py report.md -o report_cleaned.md
```

## 🔧 快速調整

### 調整處理品質
```bash
# 每主題處理更多摘要（提高品質，但較慢）
python pipeline_meeting_report.py --csv data.csv --num-initial 15 --chunk-size 3

# 每主題處理較少摘要（較快，但品質可能較低）
python pipeline_meeting_report.py --csv data.csv --num-initial 5 --chunk-size 6
```

### 切換AI模型
```bash
# 在 .env 中修改
AI_MODEL=gpt-3.5-turbo     # 便宜但品質較低
AI_MODEL=gpt-4o           # 平衡選擇
AI_MODEL=deepseek:r1-32b   # 如使用本地Ollama
```

## 🚨 常見問題解決

### Q: 顯示 "API key not found"
```bash
# 檢查 .env 檔案是否存在且格式正確
cat .env
# 確保沒有多餘空格，格式為：
OPENAI_API_KEY=sk-your-key-here
```

### Q: 處理中斷或失敗
```bash
# 檢查錯誤訊息，通常是網路或API額度問題
# 可以從中斷的步驟繼續：
python 4Condense.py path/to/previous/output.csv
```

### Q: 輸出品質不滿意
```bash
# 嘗試調整參數
python pipeline_meeting_report.py --csv data.csv --num-initial 12 --chunk-size 2
```

## 📁 檔案結構速查

```
你的專案/
├── transcript.txt           # 輸入：清理後的逐字稿
├── transcript_topics/       # 自動生成的主題分段
├── *.csv                   # 中間資料檔案
├── 主題名稱.md              # 各主題報告
└── 主題名稱_cleaned.md      # 最終清理版報告
```

## 🎨 自定義提示

如需修改AI的處理方式，編輯這些檔案：
- `pipeline_meeting_report.py` - 修改報告生成提示
- `4Condense.py` - 修改主題聚類邏輯
- `1topic_spliterG3v2.py` - 修改主題分段策略

## 📞 需要幫助？

1. 檢查 `README.md` 獲得完整文檔
2. 查看 `CLAUDE.md` 了解技術細節
3. 參考 `PATENT_TECHNICAL_SPECS.md` 了解核心技術

---

**快速開始完成！** 🎉 現在你可以開始處理會議記錄了。