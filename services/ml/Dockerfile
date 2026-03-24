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

EXPOSE 5002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5002"]
