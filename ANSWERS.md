# 三個關鍵問題的完整解答

## 問題 1: text 是什麼？為什麼重要？

### text 是什麼

**`text` 欄位 = 原始逐字稿的片段**

在步驟1 (topic_spliter) 切割後，每個 topic_XX.md 包含：
- 標題（AI生成的主題名）
- **原始逐字稿內容**（說話人 + 時間戳 + 對話）

例如 chunk 06 的 text 內容（641字）：
```
# Grace請假
Brenda報告卓越宋文拓三週訂單統計收款發票...

好，那我想今天那個grace請假，那我們就開始進入會議程序...

Brenda Tsai (蔡素貞)   3:10
各位好，請問一下有看到我的畫面嗎？

Vandose Chen (陳銘宏)   3:13
No。

Brenda Tsai (蔡素貞)   3:15
謝謝，那我這邊就報告有關卓越跟宋文拓這兩呃，
這三週的訂單統計還有收款發票的部分。
這呃，這三週的卓越有242萬的訂單，那受文錯是7萬九...
```

對應的 summary（195字）：
```
會議中Brenda Tsai (蔡素貞) 報告卓越與宋文拓三週訂單、收款及發票狀況：
*   **卓越**三週訂單242萬，總訂單9325萬。
*   **宋文拓**三週訂單7.9萬，總訂單2562萬。
*   已開發票代收款2085萬，10月700多萬、11月1400多萬...
```

### 為什麼 text 重要？

**關鍵對比：資訊完整度**

| 來源 | 內容 | 資訊量 |
|------|------|--------|
| **text (原始逐字稿)** | 641字完整對話，包含：<br>- 說話人語氣與確認過程<br>- "受文錯是7萬九"（口誤）<br>- 具體時間戳 "3:10, 3:13, 3:15"<br>- 完整數字來源脈絡 | **100%** |
| **summary (AI摘要)** | 195字精煉重點，僅保留：<br>- 關鍵數字<br>- 主要人物<br>- 核心事項 | **30-40%** |

**實例說明**：

❌ **只看 summary 時**（現狀）：
```
Gemma3 看到: "卓越三週訂單242萬"
Gemma3 不知道: 這是 Brenda 報告的？還是討論決定的？
                是否有人質疑這個數字？
                有沒有後續追蹤要求？
```

✅ **看 text + summary 時**（優化後）：
```
Gemma3 看到 summary: "卓越三週訂單242萬"
Gemma3 參考 text: "Brenda Tsai (蔡素貞) 3:15 報告：
                  '這三週的卓越有242萬的訂單'"
Gemma3 理解:
  - 是 Brenda 的報告（不是決議）
  - 時間點在會議 3:15 分
  - 是陳述事實（不是討論議題）
  - 可以準確記錄："Brenda Tsai (蔡素貞) 報告卓越訂單242萬"
```

### 為什麼步驟3刪除 text 是致命錯誤

**現狀數據分析**：
```
步驟2產出: chunks_summaries.csv
  - chunk_id: 36個
  - summary: 平均 137字/個
  - text: 平均 592字/個 (最大1884字)
  - 檔案大小: ~80KB

步驟3產出: chunks_summaries_brief_reindexed.csv
  - chunk_id: 36個 (重新編號)
  - summary: 平均 137字/個
  - ❌ text: 已刪除
  - 檔案大小: ~20KB (省了60KB)
```

**代價計算**：
- 省下空間: 60KB
- 遺失資訊: 36個 chunks × 592字 = 21,312字原始對話
- 遺失比例: **78%的原始資訊**

**後果**：
```
步驟5 (pipeline_meeting_report.py) 生成報告時：

❌ 只能看：
  - 100-150字的 summary
  - 前文15行 (約300字)
  - 總輸入 < 500字

✅ 應該看：
  - 100-150字的 summary
  - 500-600字的 text 片段
  - 前文15行 (約300字)
  - 總輸入 ≈ 1000字（仍在 Gemma3 窗口內）
```

**品質影響實測**：

Topic版缺失的資訊（因為沒有 text）：
1. **衛福部案討論細節**（QUALITY_REPORT.md 測試案例D）
   - summary: "327萬延遲2個月"
   - text有: Brenda說"我還是希望業務這邊再去了解一下到底是有什麼樣的狀況"
   - Topic版缺失: Brenda的「希望」與「要求了解原因」

2. **消防局MOU決策過程**
   - summary: "與協會簽署MOU"
   - text有: 蔡宗哲的猶豫、翁國倫的詳細說明、費用討論
   - Topic版缺失: 整個決策推導過程

---

## 問題 2: 100字升級到150字會不會溢出？合理字元應該多少？

### 當前 Pipeline 字元流分析

#### 步驟5 的輸入計算（現狀）

**初始生成階段** (pipeline_meeting_report.py:99-108):
```python
init = group.head(args.num_initial)  # 預設前10個chunks
list_init = init['summary'].tolist()
```

**字元消耗**:
```
System Prompt: ~200字
User Prompt 模板: ~50字
10個 summary × 137字 = 1,370字
─────────────────────────
總計: ~1,620字
```
✅ 在 Gemma3 2000字窗口內：**安全**

#### 續寫階段 (pipeline_meeting_report.py:116-126):

**字元消耗**:
```
System Prompt: ~150字
前文最後15行: ~300字
User Prompt 模板: ~100字
4個新 summary × 137字 = 548字
─────────────────────────
總計: ~1,098字
```
✅ 在 Gemma3 2000字窗口內：**安全**

### 優化後（150字 summary + text 片段）字元計算

#### 初始生成（優化版）

**方案A: 保守方案**
```
System Prompt (詳細版): ~400字
User Prompt 模板: ~100字
────────────────────────────
每個 chunk 包含:
  - summary (150字)
  - structured_info (50字)
  - text片段 (400字)
  = 600字/chunk
────────────────────────────
建議處理: 3個chunks
3 × 600 = 1,800字
─────────────────────────
總計: 400 + 100 + 1,800 = 2,300字
```
❌ **超出** Gemma3 2000字窗口 (-300字)

**方案B: 實用方案（推薦）**
```
System Prompt (詳細版): ~400字
User Prompt 模板: ~100字
────────────────────────────
每個 chunk 包含:
  - summary (150字)
  - structured_info (50字)
  - text片段 (300字) ← 縮短
  = 500字/chunk
────────────────────────────
建議處理: 3個chunks
3 × 500 = 1,500字
─────────────────────────
總計: 400 + 100 + 1,500 = 2,000字
```
✅ **剛好** Gemma3 2000字窗口

**方案C: 激進方案**
```
只在「有關鍵資訊」時才附 text：
  - 有金額/決策: summary (150) + text (500)
  - 一般內容: summary (150) + text (200)

平均每 chunk: 350字
可處理: 4-5個 chunks
總計: 400 + 100 + (350×4) = 1,900字
```
✅ 在窗口內，**最優**

#### 續寫階段（優化版）

**方案B（推薦）**:
```
System Prompt: ~200字
前文最後15行: ~300字
前文摘要: ~150字 ← 新增
User Prompt 模板: ~100字
────────────────────────────
每個新 chunk:
  - summary (150字)
  - structured_info (50字)
  - text片段 (250字)
  = 450字/chunk
────────────────────────────
處理 2個chunks
2 × 450 = 900字
─────────────────────────
總計: 200+300+150+100+900 = 1,650字
```
✅ 在 Gemma3 2000字窗口內：**安全且有餘裕**

### 合理字元配置建議

基於以上分析，推薦配置：

| 階段 | 項目 | 字數 | 說明 |
|------|------|------|------|
| **步驟2摘要** | summary長度 | **150-180字** | 從100字增加，容納6大要素 |
| | text保留 | 完整保留 | 步驟3不刪除 |
| **步驟5初始生成** | System Prompt | 350-400字 | 詳細指引（含few-shot） |
| | 處理chunks數 | **3個** | 從10個降低 |
| | 每chunk-summary | 150字 | |
| | 每chunk-text | **300字** | text[:300] 取前段 |
| | 總輸入 | ~1,900字 | 留100字buffer |
| **步驟5續寫** | System Prompt | 200字 | 簡化版 |
| | 前文context | 450字 | 15行+摘要 |
| | 處理chunks數 | **2個** | 從4個降低 |
| | 每chunk總和 | 450字 | summary+info+text |
| | 總輸入 | ~1,650字 | 安全 |

### 具體修改建議

#### 修改 2chunks_summary.py

```python
# 原: MAX_CHARS = 6000
MAX_CHARS = 2000  # 實際Gemma3處理能力

def generate_summary_tags_natural(text):
    # 限制輸入
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    prompt = f"""..."""  # 優化後的prompt

    # ⚠️ 關鍵：增加 max_tokens
    return ai_response(messages, max_tokens=250)  # 原180 → 250
```

#### 修改 pipeline_meeting_report.py

```python
# 初始生成：從10個降到3個
parser.add_argument('--num-initial', type=int,
                   default=3,  # 原10 → 3
                   help='每topic生成初始報告數量')

# 續寫：從4個降到2個
parser.add_argument('--chunk-size', type=int,
                   default=2,  # 原4 → 2
                   help='續寫摘要批次大小')

# 在構建prompt時限制text長度
for _, row in init.iterrows():
    if 'text' in row:
        # ⚠️ 限制text片段長度
        text_snippet = row['text'][:300]  # 只取前300字
        prompt_init += f"**原文參考**: {text_snippet}\n"
```

---

## 問題 3: 優先級3「改進生成Prompt」具體方法

### 核心策略：三層資訊架構

```
Layer 1: Summary (精煉層) - 150字
  ↓ 提供：主要事項、關鍵數字

Layer 2: Structured Info (結構層) - 50字
  ↓ 提供：金額[]、人名[]、日期[]、決策[]

Layer 3: Text Snippet (證據層) - 300字
  ↓ 提供：原始對話、語境、確認過程
```

讓 Gemma3 可以「交叉驗證」三個來源，減少幻覺。

### 具體實現

#### Step 1: 修改 SYSTEM_PROMPT_INIT

**原版（不足）**:
```python
SYSTEM_PROMPT_INIT = """
你負責根據多條100字左右的會議摘要，
撰寫一段條列式的 Markdown 會議報告節選，
必須詳盡列出人事時地物與金錢費用等細節，
且能清晰呈現各重點。
"""
```

**優化版（詳細）**:
```python
SYSTEM_PROMPT_INIT = """
你是專業會議記錄AI。你將收到每個會議片段的三層資訊：
1. 摘要（Summary）- 精煉的重點
2. 結構化資訊（Structured）- 關鍵數據
3. 原文參考（Text）- 對話證據

【你的任務】：
整合三層資訊，撰寫專業的 Markdown 會議報告。

【品質要求】：
1. **數字準確度 100%**
   - 從「結構化資訊」或「原文」直接引用數字
   - 格式：「XXX萬」「YY%」（不用「約」「大概」）
   - 錯誤示例：原文「327萬」→ 寫成「三百多萬」❌

2. **人名完整格式**
   - 格式：「中文名（英文名）」如「翁國倫（Wallace Weng）」
   - 職稱在首次出現時標註
   - 引用原文中的完整姓名

3. **責任歸屬明確**
   - 格式：「由XXX負責YYY」「XXX表示ZZZ」
   - 從原文確認是「決定」還是「建議」
   - 錯誤示例：「單位決定」→ 應寫「翁國倫負責」✅

4. **時程具體化**
   - 格式：「X月X日」「X月底前」
   - 不用「近期」「即將」「盡快」等模糊詞
   - 從原文或結構化資訊提取日期

5. **決策邏輯保留**
   - 如果原文有討論過程，簡述「因...所以...」
   - 例：「因合約變動，簽約延遲至本週」

【格式規範】：
```markdown
## 主題名稱

### 小標題
* **關鍵項目**：內容
  * 子項目：細節
  * 責任人：XXX（YYY）
  * 時程：X月X日前完成
```

【範例】：
**輸入**：
```
Summary: 翁國倫報告衛福部案延遲2個月327萬需追蹤
Structured: {"金額":["327萬"],"人名":["翁國倫"],"決策":["翁國倫負責追蹤"]}
Text: Brenda說"衛福部第2期款...已經延了2個月...有327萬...
      還是希望業務這邊再去了解一下到底是有什麼樣的狀況"
      翁國倫回"對我，我會去追"
```

**輸出**：
```markdown
### 衛福部第2期款延遲追蹤

* **延遲款項**：327萬
  * 延遲時間：2個月（自8月13日）
  * 原因：行政簽程未完成
* **責任人**：翁國倫（Wallace Weng）負責追蹤行政程序狀況
* **要求**：Brenda要求了解延遲具體原因
```

【禁止事項】：
❌ 不要添加原文沒有的推測
❌ 不要改寫數字（327萬 ≠ 三百多萬）
❌ 不要使用縮寫（北市教育局 ✅，北教局 ❌）
❌ 不要省略責任人（「業務負責」❌ → 「翁國倫負責」✅）

現在開始處理實際會議內容。
"""
```

**改進點分析**：
1. ✅ 明確告知會收到「三層資訊」
2. ✅ 5大品質要求（數字、人名、責任、時程、邏輯）
3. ✅ 每項要求都有「格式」+「錯誤示例」
4. ✅ 完整的輸入輸出範例（few-shot）
5. ✅ 禁止事項明確

#### Step 2: 修改 user prompt 構建邏輯

**原版（只有summary）**:
```python
prompt_init = "以下為本主題前 {} 項摘要：\n".format(len(list_init)) + \
              '\n'.join(f"- {s}" for s in list_init) + \
              "\n請根據上述摘要撰寫 Markdown 條列會議報告節選。"
```

**優化版（三層資訊）**:
```python
def build_initial_prompt(init_df):
    """構建初始生成的三層資訊prompt"""

    prompt = f"以下是本主題的 {len(init_df)} 個會議片段，每個包含三層資訊：\n\n"
    prompt += "="*60 + "\n\n"

    for idx, row in init_df.iterrows():
        chunk_id = row['chunk_id']
        summary = row['summary']

        # Layer 1: Summary
        prompt += f"### 片段 [{chunk_id}]\n\n"
        prompt += f"**【摘要】**（精煉重點）:\n{summary}\n\n"

        # Layer 2: Structured Info (如果有)
        if 'structured_info' in row and pd.notna(row['structured_info']):
            try:
                info = json.loads(row['structured_info'])
                prompt += "**【結構化資訊】**（關鍵數據）:\n"
                if info.get('金額'):
                    prompt += f"- 金額: {', '.join(info['金額'])}\n"
                if info.get('人名'):
                    prompt += f"- 人員: {', '.join(info['人名'])}\n"
                if info.get('日期'):
                    prompt += f"- 日期: {', '.join(info['日期'])}\n"
                if info.get('決策'):
                    prompt += f"- 決策: {', '.join(info['決策'])}\n"
                prompt += "\n"
            except:
                pass

        # Layer 3: Text Snippet
        if 'text' in row and pd.notna(row['text']):
            text = str(row['text'])
            # ⚠️ 智能截取：優先保留有數字、人名的部分
            text_snippet = smart_truncate(text, max_len=300)
            prompt += f"**【原文參考】**（對話證據）:\n{text_snippet}\n\n"

        prompt += "-"*60 + "\n\n"

    # 最後的指令
    prompt += """
請整合以上 {} 個片段，撰寫本主題的完整 Markdown 報告。

要求：
1. 按邏輯分組（不要逐條翻譯）
2. 所有數字直接從「結構化資訊」或「原文」引用
3. 人名使用「中文（英文）」格式
4. 責任人明確標註
5. 保持條列清晰（使用 *, ** 層級）

開始撰寫：
""".format(len(init_df))

    return prompt

def smart_truncate(text, max_len=300):
    """智能截取text：優先保留關鍵資訊"""
    if len(text) <= max_len:
        return text

    # 策略1: 如果文本有明確的對話分隔，優先保留關鍵對話
    lines = text.split('\n')

    # 找出包含數字或決策關鍵詞的行
    important_lines = []
    for line in lines:
        if any(keyword in line for keyword in ['萬', '月', '日', '決定', '負責', '追蹤']):
            important_lines.append(line)

    # 如果找到重要行，優先包含
    if important_lines:
        result = '\n'.join(important_lines[:5])  # 最多5行
        if len(result) <= max_len:
            return result + '\n...'

    # 否則，取前max_len字
    return text[:max_len] + '...'
```

**改進點**：
1. ✅ 明確標示三層資訊（用粗體區分）
2. ✅ 結構化資訊按類別展示
3. ✅ text使用「智能截取」保留關鍵資訊
4. ✅ 最後指令明確（5點要求）
5. ✅ 總字數控制：3個chunks × 600字 = 1,800字（安全）

#### Step 3: 修改續寫 Prompt

**優化版（加入前文摘要）**:
```python
def build_continue_prompt(md_file, new_chunks_df):
    """構建續寫prompt，包含前文摘要"""

    # 讀取完整前文
    with open(md_file, 'r', encoding='utf-8') as f:
        full_content = f.read()

    prompt = ""

    # Part 1: 前文摘要（如果前文>800字）
    if len(full_content) > 800:
        # 生成前文摘要
        summary_prompt = f"""
請用200字摘要以下前文的主要內容：

{full_content[:500]}
...
{full_content[-300:]}

格式：
- 已討論議題：XXX、YYY
- 涉及人員：AAA、BBB
- 關鍵數字：X萬、Y%
"""
        前文摘要 = ai_response([{"role":"user","content":summary_prompt}], max_tokens=300)

        prompt += f"""
【前文摘要】（供了解已討論內容）:
{前文摘要}

"""

    # Part 2: 前文最後15行（供銜接）
    lines = full_content.split('\n')
    last_lines = lines[-15:] if len(lines)>=15 else lines

    prompt += f"""
【前文最後15行】（供自然銜接）:
{''.join(last_lines)}

{"="*60}

"""

    # Part 3: 新的會議片段（三層資訊）
    prompt += f"【新的會議片段】共 {len(new_chunks_df)} 個:\n\n"

    for idx, row in new_chunks_df.iterrows():
        prompt += f"### 片段 [{row['chunk_id']}]\n"
        prompt += f"摘要: {row['summary']}\n"

        if 'structured_info' in row and pd.notna(row['structured_info']):
            prompt += f"關鍵資訊: {row['structured_info']}\n"

        if 'text' in row and pd.notna(row['text']):
            text_snippet = smart_truncate(str(row['text']), max_len=250)
            prompt += f"原文: {text_snippet}\n"

        prompt += "\n" + "-"*60 + "\n\n"

    # Part 4: 續寫指令
    prompt += """
請續寫報告，要求：

1. **自然銜接**：修改「前文最後15行」使其與新內容流暢連接
2. **整合新片段**：將新片段的關鍵資訊整合進報告
3. **保持格式**：維持 Markdown 條列式
4. **數字準確**：直接引用原文中的數字
5. **完整輸出**：輸出「修改後的最後15行 + 完整新內容」

開始續寫：
"""

    return prompt
```

**字元控制**：
```
前文摘要: ~200字
前文15行: ~300字
分隔線: ~50字
2個新chunks × (150+50+250) = 900字
指令: ~150字
─────────────────────────
總計: ~1,600字 ✅ 安全
```

### 完整代碼整合

以上三個步驟整合進 `pipeline_meeting_report.py`:

```python
# 在文件開頭增加
import json

# 修改 SYSTEM_PROMPT
SYSTEM_PROMPT_INIT = """..."""  # 使用上面的優化版

SYSTEM_PROMPT_CONT = """
你是會議記錄續寫專家。你將收到：
1. 前文摘要 - 了解已討論內容
2. 前文最後15行 - 確保自然銜接
3. 新的會議片段（含三層資訊）

請整合並續寫，要求：
- 修改最後15行以流暢銜接
- 整合新片段的所有關鍵資訊
- 保持數字與人名準確
- 維持 Markdown 格式
"""

# 修改主流程
if __name__ == '__main__':
    # ... (參數解析)

    # ⚠️ 降低批次大小
    parser.add_argument('--num-initial', type=int, default=3)
    parser.add_argument('--chunk-size', type=int, default=2)

    # ... (讀取CSV)

    for topic, group in df.groupby('cluster_name'):
        out_md = os.path.join(args.output, f"{safe}.md")

        # 1) 初始生成（使用三層資訊）
        init = group.head(args.num_initial)
        prompt_init = build_initial_prompt(init)  # ← 新函數

        msgs = [{'role':'system','content':SYSTEM_PROMPT_INIT},
                {'role':'user','content':prompt_init}]

        print(f"生成初始: {out_md}")
        reply_init = ai_response(msgs, max_tokens=1200)  # 增加輸出長度

        with open(out_md, 'w', encoding='utf-8') as f:
            f.write(reply_init)

        # 2) 續寫（使用前文摘要+三層資訊）
        remaining = group.iloc[args.num_initial:]
        if remaining.empty:
            continue

        for i in range(0, len(remaining), args.chunk_size):
            chunk = remaining.iloc[i:i+args.chunk_size]

            # 構建續寫prompt
            prompt_cont = build_continue_prompt(out_md, chunk)  # ← 新函數

            msgs2 = [{'role':'system','content':SYSTEM_PROMPT_CONT},
                     {'role':'user','content':prompt_cont}]

            # 顯示進度
            stop = threading.Event()
            t = threading.Thread(target=print_dot, args=(stop,))
            t.start()

            try:
                reply2 = ai_response(msgs2, max_tokens=1000)
            finally:
                stop.set()
                t.join()

            # 更新文件（替換最後15行）
            with open(out_md, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if len(lines) >= 15:
                new_content = lines[:-15] + [reply2 + '\n']
            else:
                new_content = [reply2 + '\n']

            with open(out_md, 'w', encoding='utf-8') as f:
                f.writelines(new_content)

            print(f"  續寫完成 {i+1}-{i+len(chunk)}")

    print("全部完成")
```

---

## 總結：三個問題的答案

### Q1: text是什麼
**答**: 原始逐字稿片段（平均592字），包含完整對話、說話人、時間戳。是 summary（137字）的「證據來源」，保留78%的原始資訊。

### Q2: 150字會溢出嗎
**答**: 不會。只要：
- 初始生成：處理3個chunks（從10個降低）
- 續寫：處理2個chunks（從4個降低）
- text片段：限制300字（不用完整592字）
- 總輸入控制在 1,900字內

### Q3: 如何改進生成Prompt
**答**: 三層資訊架構
1. **System Prompt**: 詳細指引（400字含few-shot）
2. **User Prompt**: 三層資訊
   - Layer 1: Summary (150字)
   - Layer 2: Structured Info (50字)
   - Layer 3: Text Snippet (300字)
3. **續寫Prompt**: 加入前文摘要（200字）

讓 Gemma3 可以「交叉驗證」三個來源，而不是「單一來源推測」。

**關鍵**: 給 Gemma3「少而精」的資訊（3個chunks），但每個chunk有「多層次」的資訊（summary+info+text），比給「多而淺」的資訊（10個summary）效果好。
