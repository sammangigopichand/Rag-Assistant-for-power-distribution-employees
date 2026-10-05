from pathlib import Path
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE_DIR / "models" / "all-MiniLM-L6-v2"

print("Loading local embedding model...")

model = SentenceTransformer(
    str(MODEL_PATH),
    local_files_only=True
)

print("Embedding model loaded successfully.")


def generate_embeddings(texts):
    return model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )