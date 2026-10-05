"""Build fresh embeddings and a FAISS index from knowledge_base and raw."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.index_service import rebuild_index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the utility knowledge FAISS index.")
    parser.add_argument("--raw-only", action="store_true", help="Rebuild from every file in raw only, including duplicate documents.")
    args = parser.parse_args()
    count = rebuild_index(
        progress=lambda stage, processed, total: print(
            f"{stage}: {processed}/{total} chunks"
        ),
        source_dirs=[Path(__file__).resolve().parents[1] / "raw"] if args.raw_only else None,
        deduplicate=False,
        strict=True,
    )
    print(f"FAISS indexing completed: {count} chunks.")
