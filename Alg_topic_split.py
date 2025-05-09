#python Alg_topic_split.py /home/henry/automeeting/民族學街訪/逐字稿_修正版.txt --method cosine --window 6 --threshold 0.25
#python Alg_topic_split.py /home/henry/automeeting/2025Feb_NSTM_meet/shorten.txt --method cosine --window 6 --threshold 0.25
"""主題切割演算法說明：

本程式可將逐字稿依照語意與主題自然切段，支援以下三種傳統 NLP 演算法：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【1】cosine 模式（餘弦相似度，適合調整敏感度）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
原理：

將每段文字轉換為 TF-IDF 向量，計算相鄰區塊之間的餘弦相似度。

若相似度低於指定閾值，即代表主題出現變化，視為「切點」。

參數：
--window：視窗大小，預設 5　每個區塊包含幾行（太小容易誤判、太大會漏切）

--threshold：相似度閾值，預設 0.3　範圍建議為 0.05 ～ 0.6　越大 → 越容易切段（更敏感）；越小 → 只切明顯不同主題

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【2】texttiling 模式（詞彙密度斷層法）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
原理：

將逐字稿每一行轉換為 TF-IDF 向量，並計算每行的總詞權重（密度）。

當相鄰行的密度出現劇烈變化，判定為主題斷點。

是一種早期常見於段落切割的基礎演算法。

參數：
--tt_ratio：變異倍率，預設 1.5　範圍建議為 1.0 ～ 3.0　相鄰密度變化值若超過全體變異平均值的幾倍，則切斷。　越小 → 越敏感（可能切得很碎）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【3】slope 模式（向量斜率轉折點法）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
原理：

將每行轉換為向量後，計算其向量長度（語意強度）。

分析長度變化的「斜率」，當斜率方向產生變化（如上升轉為下降），視為主題斷點。

適合找出「語意走向」的轉折。

參數：
--slope_window：轉折判斷範圍，預設 1　建議範圍為 1 ～ 5　計算平均斜率時所考慮的前後行數，越大越平滑。

--slope_smooth：平滑次數，預設 1　建議範圍為 1 ～ 5　對整體語意強度曲線做卷積平滑，去除雜訊。　越大 → 越不易誤判轉折點（但可能漏切）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

建議用法：

想要明確控制段落數量 → cosine 模式 + 嘗試不同 threshold。

想快速切大章節 → slope 模式，適合演講稿與議程類。

想處理新聞或對話 → texttiling 可視為 baseline。"""

import os
import re
import argparse
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

# ========== CLI 參數 ==========
parser = argparse.ArgumentParser(description="使用傳統方法切割逐字稿主題段落")
parser.add_argument("input_file", help="輸入逐字稿檔案（每行為一句）")
parser.add_argument("--method", choices=["cosine", "texttiling", "slope"], default="cosine", help="切割方法")
parser.add_argument("--window", type=int, default=5, help="視窗大小（適用 cosine）")
parser.add_argument("--threshold", type=float, default=0.3, help="切割閾值（適用 cosine）")
parser.add_argument("--tt_ratio", type=float, default=1.5, help="TextTiling 密度變化倍率")
parser.add_argument("--slope_window", type=int, default=1, help="Slope 檢查範圍寬度")
parser.add_argument("--slope_smooth", type=int, default=1, help="Slope 平滑次數")
args = parser.parse_args()

input_file = args.input_file
method = args.method
window_size = args.window
threshold = args.threshold

# ========== 讀入逐字稿 ==========
with open(input_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

# ========== 三種演算法 ==========
def traditional_cut(lines, method="cosine", window_size=5, threshold=0.3, tt_ratio=1.5, slope_window=1, slope_smooth=1):
    split_indices = [0]

    if method == "cosine":
        chunks = [(" ".join(lines[i:i + window_size]), i) for i in range(0, len(lines) - window_size + 1)]
        texts, indices = zip(*chunks)
        vec = TfidfVectorizer().fit_transform(texts)
        for i in range(len(chunks) - 1):
            sim = cosine_similarity(vec[i], vec[i + 1])[0][0]
            if sim < threshold:
                split_indices.append(indices[i + 1])

    elif method == "texttiling":
        vec = TfidfVectorizer().fit_transform(lines)
        density = np.array(vec.sum(axis=1)).flatten()
        diff = np.abs(np.diff(density))
        mean = np.mean(diff)
        for i, d in enumerate(diff):
            if d > mean * tt_ratio:
                split_indices.append(i + 1)

    elif method == "slope":
        vec = TfidfVectorizer().fit_transform(lines)
        norm = np.linalg.norm(vec.toarray(), axis=1)
        for _ in range(slope_smooth):
            norm = np.convolve(norm, np.ones(3)/3, mode='same')
        slopes = np.diff(norm)
        for i in range(slope_window, len(slopes) - slope_window):
            prev = slopes[i - slope_window:i]
            post = slopes[i:i + slope_window]
            if np.mean(prev) * np.mean(post) < 0:
                split_indices.append(i + 1)

    split_indices = sorted(set(split_indices + [len(lines)]))
    return split_indices

# ========== 切段 ==========
split_indices = traditional_cut(
    lines,
    method,
    window_size,
    threshold,
    args.tt_ratio,
    args.slope_window,
    args.slope_smooth
)
segments = []
for start, end in zip(split_indices[:-1], split_indices[1:]):
    segments.append(lines[start:end])

# ========== 儲存輸出 ==========
base_dir = os.path.dirname(input_file)
base_name = os.path.splitext(os.path.basename(input_file))[0]
folder_name = f"{method}_w{window_size}_t{threshold}_tt{args.tt_ratio}_sw{args.slope_window}_ss{args.slope_smooth}"
out_folder = os.path.join(base_dir, folder_name)
os.makedirs(out_folder, exist_ok=True)

for i, seg in enumerate(tqdm(segments, desc="儲存每段"), 1):
    preview = "".join(seg)[:10].strip().replace(" ", "")
    preview = re.sub(r'[\\/*?:"<>|（）()【】「」、，。！？~`\'\s]+', '_', preview) or "段落"
    filename = f"{i:02d}_{preview}.md"
    out_path = os.path.join(out_folder, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"### 段落 {i}\n\n")
        f.write("\n".join(seg))

print(f"\n✅ 共切出 {len(segments)} 段，已儲存在：{out_folder}")
