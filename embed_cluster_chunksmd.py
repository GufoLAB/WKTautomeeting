import os
import re
import numpy as np
import pandas as pd
import json
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
import hdbscan
import umap.umap_ as umap
import matplotlib.pyplot as plt

# ==== 參數設定 ====
chunk_dir = "/home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2"
models = [
    "shibing624/text2vec-base-chinese",
    "BAAI/bge-m3"
]
kmeans_k = 4
hdbscan_min_cluster_size = 3

# ==== 輕量清洗函數 ====
def clean_text(text):
    text = re.sub(r"[，,。．\.]{2,}", "。", text)
    text = re.sub(r"\b(呃|那個|就是|然後|欸|喔|喂|蛤)+\b", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

# ==== 讀取 chunk 檔案 ====
chunk_ids, chunk_texts = [], []
for fname in sorted(os.listdir(chunk_dir)):
    if fname.endswith(".md"):
        chunk_id = os.path.splitext(fname)[0]
        with open(os.path.join(chunk_dir, fname), 'r', encoding='utf-8') as f:
            content = clean_text(f.read())
        chunk_ids.append(chunk_id)
        chunk_texts.append(content)

np.save(os.path.join(chunk_dir, "chunk_ids.npy"), chunk_ids)

# ==== 嵌入與聚類 ====
for model_name in models:
    print(f"\n🔹 Processing with {model_name}")

    # 嵌入
    model = SentenceTransformer(model_name)
    embeddings = model.encode(chunk_texts, show_progress_bar=True)
    np.save(os.path.join(chunk_dir, f"embeddings_{model_name.replace('/', '_')}.npy"), embeddings)

    # KMeans 聚類
    kmeans = KMeans(n_clusters=kmeans_k, random_state=42)
    kmeans_labels = kmeans.fit_predict(embeddings)
    kmeans_output = {}
    for idx, label in enumerate(kmeans_labels):
        kmeans_output.setdefault(f"Cluster_{label}", []).append(chunk_ids[idx])

    with open(os.path.join(chunk_dir, f"clusters_kmeans_{model_name.replace('/', '_')}_k{kmeans_k}.json"), "w", encoding="utf-8") as f:
        json.dump(kmeans_output, f, ensure_ascii=False, indent=2)

    # HDBSCAN 聚類
    hdb = hdbscan.HDBSCAN(min_cluster_size=hdbscan_min_cluster_size)
    hdb_labels = hdb.fit_predict(embeddings)
    hdbscan_output = {}
    for idx, label in enumerate(hdb_labels):
        label_name = f"Cluster_{label}" if label >= 0 else "Noise"
        hdbscan_output.setdefault(label_name, []).append(chunk_ids[idx])

    with open(os.path.join(chunk_dir, f"clusters_hdbscan_{model_name.replace('/', '_')}_min{hdbscan_min_cluster_size}.json"), "w", encoding="utf-8") as f:
        json.dump(hdbscan_output, f, ensure_ascii=False, indent=2)

    # UMAP 視覺化
    reducer = umap.UMAP(random_state=42)
    embedding_2d = reducer.fit_transform(embeddings)

    plt.figure(figsize=(12, 8))
    plt.scatter(embedding_2d[:, 0], embedding_2d[:, 1], c=kmeans_labels, cmap='tab10', s=50, alpha=0.7)
    plt.title(f"UMAP Visualization - {model_name} - KMeans")
    plt.colorbar()
    plt.savefig(os.path.join(chunk_dir, f"umap_kmeans_{model_name.replace('/', '_')}.png"))

    plt.figure(figsize=(12, 8))
    plt.scatter(embedding_2d[:, 0], embedding_2d[:, 1], c=hdb_labels, cmap='Spectral', s=50, alpha=0.7)
    plt.title(f"UMAP Visualization - {model_name} - HDBSCAN")
    plt.colorbar()
    plt.savefig(os.path.join(chunk_dir, f"umap_hdbscan_{model_name.replace('/', '_')}.png"))

print("\n✅ 完成嵌入、聚類及視覺化，所有結果儲存在:", chunk_dir)
