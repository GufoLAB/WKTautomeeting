import os
import sys
import faiss
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

def ensure_output_folder(input_file):
    base_dir = os.path.dirname(input_file)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_dir = os.path.join(base_dir, f"rag_embed_{base_name}")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def load_documents(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines

def build_faiss_index(docs, model_name='all-MiniLM-L6-v2'):
    model = SentenceTransformer(model_name)
    embeddings = []
    for doc in tqdm(docs, desc="Embedding documents"):
        embedding = model.encode(doc)
        embeddings.append(embedding)
    embeddings = np.array(embeddings).astype('float32')
    
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index, embeddings

def save_index(index, path):
    faiss.write_index(index, path)

def save_documents(docs, path):
    with open(path, 'w', encoding='utf-8') as f:
        for doc in docs:
            f.write(doc + '\n')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python embed_rag.py <input.txt>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = ensure_output_folder(input_file)

    documents = load_documents(input_file)
    index, _ = build_faiss_index(documents)

    save_index(index, os.path.join(output_dir, "faiss.index"))
    save_documents(documents, os.path.join(output_dir, "documents.txt"))

    print(f"完成：共處理 {len(documents)} 段，結果已存入：{output_dir}")
