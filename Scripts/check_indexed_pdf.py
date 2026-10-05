from pathlib import Path
import pickle

BASE_DIR = Path(__file__).resolve().parents[1]

KNOWLEDGE_BASE = BASE_DIR / "knowledge_base"
METADATA_PATH = BASE_DIR / "faiss_index" / "metadata.pkl"

# -----------------------------
# 1. Get all PDF files
# -----------------------------
all_pdfs = list(KNOWLEDGE_BASE.rglob("*.pdf"))

print("\n==============================")
print("PDF FILES IN KNOWLEDGE BASE")
print("==============================")

for pdf in all_pdfs:
    print(pdf.relative_to(KNOWLEDGE_BASE))

print(f"\nTotal PDF files found: {len(all_pdfs)}")


# -----------------------------
# 2. Load FAISS metadata
# -----------------------------
with open(METADATA_PATH, "rb") as f:
    metadata = pickle.load(f)

print(f"Total metadata/chunks stored: {len(metadata)}")


# -----------------------------
# 3. Extract source files
# -----------------------------
indexed_sources = set()

for item in metadata:

    # If metadata is a dictionary
    if isinstance(item, dict):

        source = (
            item.get("source")
            or item.get("file")
            or item.get("filename")
            or item.get("path")
        )

        if source:
            indexed_sources.add(Path(str(source)).name)


# -----------------------------
# 4. Compare PDFs
# -----------------------------
pdf_names = {pdf.name for pdf in all_pdfs}

missing = pdf_names - indexed_sources


print("\n==============================")
print("INDEXED PDF FILES")
print("==============================")

for name in sorted(indexed_sources):
    print("✓", name)


print("\n==============================")
print("MISSING PDF FILES")
print("==============================")

if missing:
    for name in sorted(missing):
        print("✗", name)
else:
    print("✓ All PDFs are present in metadata")


print("\n==============================")
print("SUMMARY")
print("==============================")

print("PDFs in knowledge_base :", len(pdf_names))
print("PDFs found in metadata :", len(indexed_sources))
print("PDFs missing           :", len(missing))