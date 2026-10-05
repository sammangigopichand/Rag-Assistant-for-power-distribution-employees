from pathlib import Path

import pandas as pd
from docx import Document
from pypdf import PdfReader


def load_pdf(file_path):
    reader = PdfReader(file_path)

    documents = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()

        if text and text.strip():
            documents.append({
                "source": file_path.name,
                "type": "pdf",
                "page": page_number,
                "text": text.strip()
            })

    return documents


def load_docx(file_path):
    doc = Document(file_path)

    text = "\n".join(
        paragraph.text
        for paragraph in doc.paragraphs
        if paragraph.text.strip()
    )

    if not text:
        return []

    return [{
        "source": file_path.name,
        "type": "docx",
        "page": None,
        "text": text
    }]


def load_txt(file_path):
    text = file_path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    if not text.strip():
        return []

    return [{
        "source": file_path.name,
        "type": "txt",
        "page": None,
        "text": text.strip()
    }]


def load_csv(file_path):
    df = pd.read_csv(file_path)

    text = df.to_string(index=False)

    if not text.strip():
        return []

    return [{
        "source": file_path.name,
        "type": "csv",
        "page": None,
        "text": text
    }]


def load_all_documents(folder="knowledge_base", strict=False):
    folder_path = Path(folder)

    documents = []

    for file_path in folder_path.rglob("*"):

        if not file_path.is_file():
            continue

        extension = file_path.suffix.lower()

        try:
            loaded = []

            if extension == ".pdf":
                loaded = load_pdf(file_path)

            elif extension == ".docx":
                loaded = load_docx(file_path)

            elif extension == ".txt":
                loaded = load_txt(file_path)

            elif extension == ".csv":
                loaded = load_csv(file_path)

            else:
                if strict:
                    raise ValueError(f"Unsupported file type: {file_path}")
                print(f"Skipping unsupported file: {file_path.name}")

            if strict and extension in {".pdf", ".docx", ".txt", ".csv"} and not loaded:
                raise ValueError(f"No extractable text found in {file_path}")
            documents.extend(loaded)

        except Exception as e:
            if strict:
                raise RuntimeError(f"Failed to process {file_path}: {e}") from e
            print(
                f"Error reading {file_path.name}: {e}"
            )

    return documents
