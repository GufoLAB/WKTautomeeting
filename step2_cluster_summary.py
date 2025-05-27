# Re-execute everything after kernel reset
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
import hdbscan
import json
import os

# Reload files
embedding_path = "/home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2/summary_embeddings.npy"
chunk_id_path = "/home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2/chunk_ids.npy"

embeddings = np.load(embedding_path)
chunk_ids = np.load(chunk_id_path)

# Output base
output_base = os.path.dirname(embedding_path)

# Parameters
kmeans_k = 4
hdbscan_min_cluster_size = 2

results = {}

# ▶ KMeans clustering
kmeans = KMeans(n_clusters=kmeans_k, random_state=42)
kmeans_labels = kmeans.fit_predict(embeddings)

kmeans_output = {}
for idx, label in enumerate(kmeans_labels):
    label_name = f"Cluster_{label}"
    if label_name not in kmeans_output:
        kmeans_output[label_name] = []
    kmeans_output[label_name].append(chunk_ids[idx])

kmeans_file = os.path.join(output_base, f"clusters_kmeans_k{kmeans_k}.json")
with open(kmeans_file, "w", encoding="utf-8") as f:
    json.dump(kmeans_output, f, ensure_ascii=False, indent=2)

results["kmeans"] = kmeans_file

# ▶ HDBSCAN clustering
hdb = hdbscan.HDBSCAN(min_cluster_size=hdbscan_min_cluster_size)
hdb_labels = hdb.fit_predict(embeddings)

hdbscan_output = {}
for idx, label in enumerate(hdb_labels):
    label_name = f"Cluster_{label}" if label >= 0 else "Noise"
    if label_name not in hdbscan_output:
        hdbscan_output[label_name] = []
    hdbscan_output[label_name].append(chunk_ids[idx])

hdbscan_file = os.path.join(output_base, f"clusters_hdbscan_min{hdbscan_min_cluster_size}.json")
with open(hdbscan_file, "w", encoding="utf-8") as f:
    json.dump(hdbscan_output, f, ensure_ascii=False, indent=2)

results["hdbscan"] = hdbscan_file

results
