#python Condense.py /home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2/chunks_summaries_brief_output/chunks_summaries_brief_reindexed.csv --cluster auto
#!/usr/bin/env python3
"""Condense.py

1️⃣ 為每列 `summary` 產生 10–20 字中文主題（`topic`）
2️⃣ *可選* 語意分群：先讓 LLM 思考分群，再以第二次呼叫格式化為 JSON

> 原則：需要推理的任務先讓 LLM 自由組織，再要求 JSON 輸出

--------
用法
```
python Condense.py <input_csv> [--output <out_csv>] [--cluster [N|auto]]
```
- `<input_csv>`   必含 `summary` 欄；若存在 `chunk_id` 欄會自動帶入。
- `--output`      不給則預設為 `原檔名_condense_topics.csv`。
- `--cluster N`   指定期望群數 (正整數)。
- `--cluster auto` 讓 AI 決定群數 (預期 3–10 組)。

輸出
- CSV：新增 `topic`；若分群則再新增 `cluster_name`
- JSON：若分群，輸出 `<out_stem>_clusters.json` (cluster→ids)
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from zhconv_rs import zhconv
import ollama

from config import AI_MODEL, OLLAMA_URL

load_dotenv()

MAX_CHARS = 1600  # 最長上下文

# ---------- AI 包裝 ----------

def ai_response(messages, max_tokens: int = 256) -> str:
    """呼叫 Ollama(OpenAI compatible) 並轉繁體。"""
    resp = ollama.Client(host=OLLAMA_URL).chat(
        model=AI_MODEL,
        messages=messages,
        options={"temperature": 0.3, "max_tokens": max_tokens},
    )
    txt = resp["message"]["content"].strip()
    if AI_MODEL.startswith("deepseek"):
        txt = re.sub(r"<think>[\s\S]*?</think>", "", txt, flags=re.DOTALL)
    return zhconv(txt, "zh-tw")

# ---------- 工具函數 ----------

def _extract_json(text: str) -> str:
    """從 LLM 輸出抓出第一段 {...} JSON，移除 ```json 區塊。"""
    # 去除 ```json ... ``` 或 ``` ... ```
    text = re.sub(r"```(?:json)?[\s\S]*?```", lambda m: m.group(0).strip('`'), text, flags=re.I)
    # 抓第一段 { ... }
    match = re.search(r"\{[\s\S]*\}", text)
    return match.group(0) if match else text.strip()

# ---------- Pipeline ----------

def condense_topics(df: pd.DataFrame) -> pd.DataFrame:
    if "summary" not in df.columns:
        raise ValueError("CSV must contain a 'summary' column")

    topics: List[str] = []
    for cid, summary in tqdm(zip(df.index, df["summary"]), total=len(df), desc="Condensing", unit="row"):
        if pd.isna(summary) or not str(summary).strip():
            topics.append("")
            continue
        context = str(summary)[:MAX_CHARS]
        prompt = (
            "請用 10 到 20 個中文字符，精煉概括以下摘要的主題。\n"
            "不要加入空格或換行，只輸出主題文字。\n\n"
            f"摘要：{context}\n\n主題："
        )
        topic = ai_response([{"role": "user", "content": prompt}]).replace("\n", "").replace(" ", "").strip()
        # 若有 chunk_id 欄，用實際 id；否則用 DataFrame index+1
        chunk_id = df.loc[cid, "chunk_id"] if "chunk_id" in df.columns else cid + 1
        topics.append(f"[{chunk_id}]{topic[:20]}")
        print(topics[-1])
    df["topic"] = pd.Series(topics, index=df.index)
    return df


def _llm_cluster_request(topic_lines: List[str], group_hint: str) -> Tuple[str, str]:
    """兩階段：先自由分群，再回傳 JSON。"""
    # 第一階段：自由分群
    sys1 = (
        "你將收到多行主題，每行格式為 '[id]主題'。請根據語意將它們分群，" + group_hint + "。\n"
        "格式示例：\n"
        "財務預算: 1,2,4\n展覽規劃: 5,6\n..."
    )
    free_output = ai_response([
        {"role": "user", "content": sys1 + "\n\n" + "\n".join(topic_lines)}
    ])

    # 第二階段：轉 JSON
    json_prompt = (
        "請將以下分群結果轉成 JSON，key 為群名，value 為 id 數字列表：\n\n" + free_output + "\n\n只回傳 JSON。"
    )
    json_output = ai_response([{"role": "user", "content": json_prompt}])
    clean_json = _extract_json(json_output)
    return free_output, clean_json


def cluster_topics(df: pd.DataFrame, cluster_arg: str) -> Tuple[pd.DataFrame, Dict[str, List[int]]]:
    topic_lines = df["topic"].tolist()
    group_hint = "群數 3–10" if cluster_arg == "auto" else f"分成 {cluster_arg} 群"

    free, raw_json = _llm_cluster_request(topic_lines, group_hint)

    try:
        mapping: Dict[str, List[int]] = json.loads(raw_json)
    except Exception as exc:
        raise ValueError(f"❌ 第二階段回傳非 JSON：\n{raw_json}") from exc

    # id → cluster 名
    id2cluster = {int(idx): name for name, lst in mapping.items() for idx in lst}
    df["cluster_name"] = df["topic"].apply(lambda t: id2cluster.get(int(re.match(r"\[(\d+)\]", t).group(1)), ""))
    return df, mapping

# ---------- CLI ----------

def parse_args():
    p = argparse.ArgumentParser(description="Condense summaries & optional clustering")
    p.add_argument("input", help="input CSV path with 'summary'")
    p.add_argument("--output", help="output CSV path")
    p.add_argument("--cluster", help="'auto' 或整數群數", default=None)
    return p.parse_args()


def main():
    args = parse_args()
    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(in_path)
    out_path = Path(args.output) if args.output else in_path.with_stem(in_path.stem + "_condense_topics")

    df = pd.read_csv(in_path)
    df = condense_topics(df)

    cluster_map = None
    if args.cluster:
        df, cluster_map = cluster_topics(df, args.cluster)

    df.to_csv(out_path, index=False)
    print(f"✔ CSV saved → {out_path}")

    if cluster_map:
        json_path = out_path.parent / f"{out_path.stem}_clusters.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cluster_map, f, ensure_ascii=False, indent=2)
        print(f"✔ Cluster JSON saved → {json_path}")


if __name__ == "__main__":
    main()

