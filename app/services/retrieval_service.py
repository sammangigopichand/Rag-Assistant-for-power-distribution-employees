from pathlib import Path
import pickle
import threading
import faiss

from app.services.embedding_service import generate_embeddings

BASE_DIR = Path(__file__).resolve().parents[2]

FAISS_PATH = BASE_DIR / "faiss_index" / "knowledge.index"
METADATA_PATH = BASE_DIR / "faiss_index" / "metadata.pkl"
_index_cache = None
_index_cache_key = None
_index_lock = threading.Lock()

def load_index():
    global _index_cache, _index_cache_key
    cache_key = (FAISS_PATH.stat().st_mtime_ns, METADATA_PATH.stat().st_mtime_ns)
    if _index_cache is None or cache_key != _index_cache_key:
        with _index_lock:
            cache_key = (FAISS_PATH.stat().st_mtime_ns, METADATA_PATH.stat().st_mtime_ns)
            if _index_cache is None or cache_key != _index_cache_key:
                index = faiss.read_index(str(FAISS_PATH))
                with open(METADATA_PATH, "rb") as file:
                    metadata = pickle.load(file)
                _index_cache = (index, metadata)
                _index_cache_key = cache_key
    return _index_cache


def search_knowledge_base(query: str, k: int = 5):
    # Reload after administrator reindexing so the running app sees new data.
    index, metadata = load_index()
    # Convert employee question into embedding
    query_embedding = generate_embeddings([query]).astype("float32")

    # Search FAISS
    scores, indices = index.search(query_embedding, k)

    results = []

    for score, idx in zip(scores[0], indices[0]):

        if idx == -1:
            continue

        item = metadata[idx]

        # Handle dictionary metadata
        if isinstance(item, dict):
            result = item.copy()
        else:
            result = {
                "text": str(item)
            }

        result["score"] = float(score)

        results.append(result)

    return results
