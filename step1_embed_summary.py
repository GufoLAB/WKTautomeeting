import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import argparse
import os

def main(csv_path, model_name="all-MiniLM-L6-v2"):
    # 讀取 CSV
    df = pd.read_csv(csv_path)
    summaries = df["summary"].tolist()
    chunk_ids = df["chunk_id"].tolist()

    # 建立嵌入模型
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)

    # 計算摘要向量
    print(f"Encoding {len(summaries)} summaries...")
    embeddings = model.encode(summaries, show_progress_bar=True)

    # 儲存向量與 chunk_id
    base_dir = os.path.dirname(csv_path)
    np.save(os.path.join(base_dir, "summary_embeddings.npy"), embeddings)
    np.save(os.path.join(base_dir, "chunk_ids.npy"), chunk_ids)
    print("✅ Embedding saved to:")
    print("   - summary_embeddings.npy")
    print("   - chunk_ids.npy")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed summaries for clustering")
    parser.add_argument("csv_path", help="Path to CSV with chunk_id, summary columns")
    args = parser.parse_args()
    main(args.csv_path)
