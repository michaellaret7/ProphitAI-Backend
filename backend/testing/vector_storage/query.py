# query_openai.py
import os, json, faiss, numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL = "text-embedding-3-large"
TOP_K = 5
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def load_index():
    index = faiss.read_index(os.path.join(BASE_DIR, "corpus.faiss"))
    X = np.load(os.path.join(BASE_DIR, "embeddings.npy"))
    id2text = {}
    with open(os.path.join(BASE_DIR, "docs.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            id2text[r["id"]] = r
    return index, X.shape[1], id2text

def embed_query(q):
    client = OpenAI(api_key=OPENAI_API_KEY)
    vec = client.embeddings.create(model=MODEL, input=[q]).data[0].embedding
    v = np.array([vec], dtype="float32")
    v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
    return v

def main():
    index, d, id2text = load_index()
    q = input("Query: ").strip()
    qv = embed_query(q)
    D, I = index.search(qv, TOP_K)

    for rank, (score, idx) in enumerate(zip(D[0], I[0]), start=1):
        r = id2text.get(int(idx))
        if r:
            print(f"{rank}. id={idx}  score(L2)={score:.4f}  src={r['source']}#{r['chunk']}\n   {r['text']}\n")

if __name__ == "__main__":
    main()
