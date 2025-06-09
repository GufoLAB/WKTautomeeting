#python RAG_retrieve.py /home/henry/automeeting/民族學街訪/逐字稿_修正版.txt
#python RAG_retrieve.py /home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2/chunks_summariesv3.jsonl
"""正確做法：
假設你是這樣建的：

python RAG_Embedding.py /home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2/chunks_summariesv3.jsonl
這會產生

/home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2/rag_embed_chunks_summariesv3
    ├── faiss.index
    └── documents.txt
查詢時要用 chunks_summariesv3.jsonl 作為參數：

python RAG_retreive.py /home/henry/automeeting/2025Feb_NSTM_meet/shorten_topicsv2/chunks_summariesv3.jsonl"""
import sys
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

def load_documents(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def search(query, docs, index, model, top_k=3):
    query_vec = model.encode([query]).astype('float32')
    distances, indices = index.search(query_vec, top_k)
    results = []
    for i, score in zip(indices[0], distances[0]):
        if i < len(docs):
            results.append((docs[i], score))
    return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python search_rag.py <輸入檔.txt>")
        sys.exit(1)

    input_file = sys.argv[1]

    # 構造路徑
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    base_dir = os.path.dirname(input_file)
    output_dir = os.path.join(base_dir, f"rag_embed_{base_name}")
    index_path = os.path.join(output_dir, "faiss.index")
    doc_path = os.path.join(output_dir, "documents.txt")

    # 載入
    model = SentenceTransformer('all-MiniLM-L6-v2')
    index = faiss.read_index(index_path)
    docs = load_documents(doc_path)

    print(f"\n✅ 成功載入 {len(docs)} 段文件，開始查詢！輸入空白即可結束。\n")
    
    while True:
        query = input("請輸入查詢問題：").strip()
        if not query:
            break

        results = search(query, docs, index, model)

        print(f"\n🔍 查詢：「{query}」")
        for i, (text, score) in enumerate(results, 1):
            print(f"\n#{i} 相似度: {score:.4f}")
            print(text)