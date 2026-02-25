# rag_server.py — retrieval-augmented Q&A over your saved facts
from flask import Flask, request, jsonify
from flask_cors import CORS
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data/knowledge")
DATA_DIR.mkdir(parents=True, exist_ok=True)

embedder = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma"))
collection = chroma_client.get_or_create_collection(name="ii_kb", metadata={"hnsw:space":"cosine"})

app = Flask(__name__)
CORS(app)  # allow calls from your 3D page or Flask UI

def retrieve(query: str, k: int = 5):
    qvec = embedder.encode([query]).tolist()[0]
    res = collection.query(
        query_embeddings=[qvec],
        n_results=k,
        include=["documents", "metadatas", "distances"]
    )
    docs  = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    return list(zip(docs, metas, dists))

def simple_answer(query: str, contexts):
    # Transparent “grounded” response (no cloud call).
    lines = [f"Q: {query}", "Context used:"]
    for i, (doc, meta, dist) in enumerate(contexts, 1):
        ctype = (meta or {}).get("type", "fact")
        lines.append(f"{i}. ({ctype}) {doc}")
    lines.append("")
    lines.append("Answer (grounded):")
    if not contexts:
        lines.append("I don’t have enough info recorded yet. Please add more facts or answers.")
    else:
        stitched = " ".join(doc for doc, _, _ in contexts[:2])
        lines.append(stitched)
    return "\n".join(lines)

@app.get("/ask")
def ask():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "missing q"}), 400
    ctx = retrieve(q, k=5)
    ans = simple_answer(q, ctx)
    return jsonify({
        "ok": True,
        "answer": ans,
        "used": [{"text": d, "type": (m or {}).get("type","fact"), "score": float(1 - dist)} for d,m,dist in ctx]
    })

@app.get("/")
def index():
    return "rag_server up — GET /ask?q=..."

if __name__ == "__main__":
    app.run(port=5052, debug=True)
