FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
# Install the CPU-only PyTorch wheel before sentence-transformers so pip does
# not add CUDA runtime packages to this CPU-based application image.
RUN pip install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# The embedding service loads this exact local path at application startup.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').save('/app/models/all-MiniLM-L6-v2')"

RUN mkdir -p /app/faiss_index

EXPOSE 8000

# Create/migrate the database tables and populate a new persistent FAISS volume
# on first start. Railway provides PORT at runtime.
CMD ["sh", "-c", "python Scripts/migrate_roles.py && python Scripts/create_table.py && if [ ! -s /app/faiss_index/knowledge.index ] || [ ! -s /app/faiss_index/metadata.pkl ]; then python Scripts/index_documents.py; fi && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
