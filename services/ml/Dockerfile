FROM python:3.11-slim-bookworm

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    sentence-transformers \
    faiss-cpu \
    numpy \
    pydantic

COPY app.py .

# Pre-download models at build time so startup is instant (no runtime download)
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
from sentence_transformers.cross_encoder import CrossEncoder; \
SentenceTransformer('all-MiniLM-L6-v2'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

EXPOSE 5002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5002"]
