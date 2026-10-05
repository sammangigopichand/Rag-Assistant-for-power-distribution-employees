from pathlib import Path
import pickle
import hashlib

import faiss
import numpy as np

from app.services.chunk_service import split_text
from app.services.data_loader import load_all_documents
from app.services.embedding_service import generate_embeddings

BASE_DIR = Path(__file__).resolve().parents[2]


def rebuild_index(progress=None, source_dirs=None, deduplicate=False, strict=True):
    """Rebuild FAISS from the selected document directories."""
    if source_dirs is None:
        source_dirs = [BASE_DIR / "knowledge_base", BASE_DIR / "raw"]
    documents = []
    for folder in source_dirs:
        documents.extend(load_all_documents(folder, strict=strict))
    if deduplicate:
        unique_documents = []
        seen = set()
        for document in documents:
            key = (document["source"], document["page"], hashlib.sha256(document["text"].encode("utf-8")).digest())
            if key not in seen:
                seen.add(key)
                unique_documents.append(document)
        documents = unique_documents
    chunks, metadata = [], []
    for document in documents:
        for number, chunk in enumerate(split_text(document["text"]), start=1):
            chunks.append(chunk)
            metadata.append({"source": document["source"], "type": document["type"],
                             "page": document["page"], "chunk_number": number, "content": chunk})
    if not chunks:
        raise RuntimeError("No text chunks found in knowledge_base.")
    if progress:
        progress("embedding", 0, len(chunks))
    vectors = []
    batch_size = 64
    for start in range(0, len(chunks), batch_size):
        vectors.append(generate_embeddings(chunks[start:start + batch_size]))
        if progress:
            progress("embedding", min(start + batch_size, len(chunks)), len(chunks))
    embeddings = np.asarray(np.concatenate(vectors, axis=0), dtype="float32")
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    target = BASE_DIR / "faiss_index"
    target.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(target / "knowledge.index"))
    with (target / "metadata.pkl").open("wb") as file:
        pickle.dump(metadata, file)
    if progress:
        progress("saving", len(chunks), len(chunks))
    return len(chunks)
