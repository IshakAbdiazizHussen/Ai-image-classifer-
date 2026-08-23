# Build context is the repo root (docker-compose.yml uses `context: .`)
# because this image needs both backend/ and the shared ml/preprocessing
# module — the same byte-for-byte preprocessing used by training/eval
# (constraints.md rule 10). It does NOT need ml/training or ml/export
# (torch/torchvision) — only the two files below are copied in, keeping
# this image free of the heavy ML training stack.
FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY ml/__init__.py ml/preprocessing.py ml/

# The promoted model artifact (ml/artifacts/) is bind-mounted read-only
# at runtime, not baked in here — see docker-compose.yml. That's what
# lets a newly promoted model version be served without an image rebuild.

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
