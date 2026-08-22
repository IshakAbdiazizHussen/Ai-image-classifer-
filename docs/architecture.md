# Architecture

## Tech Stack

| Layer | Choice |
|---|---|
| ML framework | PyTorch + torchvision |
| Export format | ONNX (`torch.onnx.export`), served via `onnxruntime` |
| Backend framework | FastAPI (Python) |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Database | PostgreSQL |
| Cache | Redis |
| Frontend | Next.js (React, TypeScript) |
| Containerization | Docker Compose |

## Repository Layout

```
ml/
  data/
    raw/            source images (git-ignored, path configured via env/config)
    processed/      preprocessed images, if materialized to disk
    splits/         train/val/test manifest files (checked into git — file
                     lists, not image bytes)
  configs/          training config: hyperparameters, seed, class list
  training/         dataset.py, model.py, train.py
  export/           export.py (checkpoint -> ONNX), evaluate.py
  artifacts/        versioned model registry: <version>/model.onnx +
                     <version>/metadata.json (git-ignored; produced by CI/
                     the export step, mounted into the backend container)

backend/
  routers/          predict, history, health
  services/         inference_service, prediction_service, rate_limit
  models/           SQLAlchemy models (PredictionRecord)
  schemas/          Pydantic request/response models
  core/             config, database, redis, logging

frontend/
  app/
    upload/         upload + result view
    history/        paginated prediction history
  components/
    UploadForm, ResultCard, ProbabilityChart, HistoryTable
  lib/
    api/            typed API client

docker-compose.yml
```

## ML Pipeline

- Dataset location, class list, split ratios, seed, and hyperparameters
  all live in `ml/configs/` — never hardcoded inside training scripts.
- `ml/data/splits/` holds the persisted train/val/test manifest (file
  paths + labels) so the split is created once and is reproducible; the
  same image never appears in more than one split.
- `ml/training/train.py` trains against the config, writing checkpoints
  plus the exact run config used, so any checkpoint can be traced back to
  the settings that produced it.

## Model Export & Evaluation

- `ml/export/export.py` converts a trained checkpoint to ONNX and writes
  it into `ml/artifacts/<version>/` alongside `metadata.json` (version,
  source checkpoint, class list, preprocessing spec, export date).
- `ml/export/evaluate.py` runs the exported model against the held-out
  test split only, producing accuracy/precision/recall/confusion-matrix
  metrics. A model is only promoted (its version referenced by the
  backend's `MODEL_VERSION` config) if it clears the threshold defined in
  [constraints.md](constraints.md).
- The preprocessing/normalization spec recorded in `metadata.json` is the
  single source of truth used both by the evaluation script and by the
  backend's inference service — it is defined once and referenced, never
  redefined in two places.

## Backend Architecture

Layered, one-way dependency flow:

```
routers/     Request parsing/response shaping only. No inference or DB
             logic inline.
services/    inference_service (loads the ONNX model once at startup,
             runs preprocessing + inference), prediction_service
             (persists/reads PredictionRecord), rate_limit (Redis-backed).
models/      SQLAlchemy ORM models.
schemas/     Pydantic request/response models, separate from ORM models.
core/        config, DB session, Redis client, logging setup.
```

- **Data model** — `PredictionRecord`: id, `image_hash` (sha256 of the
  uploaded image), `predicted_label`, `confidence`, `probabilities` (JSON,
  per-class), `model_version`, `inference_latency_ms`, `created_at`.
- **Inference service** loads the ONNX model and class list once at
  process startup (not per-request) via `onnxruntime.InferenceSession`,
  and is safe to call concurrently.
- **Caching** — Redis key `predict:{model_version}:{image_sha256}` with a
  TTL, caching the prediction for identical repeated uploads. Including
  `model_version` in the key means a new promoted model version
  automatically bypasses stale cache entries without any manual
  invalidation step.
- **Rate limiting** — Redis-backed counter (sliding window/token bucket)
  applied to the prediction endpoint per client IP.

## Frontend Architecture

- `app/upload/` posts the selected image to the backend's `/predict`
  endpoint and renders `ResultCard` (predicted label, confidence) and
  `ProbabilityChart` (per-class probabilities) from the response.
- `app/history/` calls the backend's paginated `/history` endpoint and
  renders `HistoryTable`.
- `lib/api/` is a typed client wrapping both endpoints; the backend base
  URL is read from an environment variable, never hardcoded.
- Class list and any per-class display data come from the API response,
  not from a hardcoded frontend constant — components are prop-driven.

## Docker Compose Topology

Services: `frontend` (Next.js, port 3000), `backend` (FastAPI, port 8000,
depends on `db` and `redis`, mounts the `ml/artifacts/` model registry
read-only), `db` (Postgres, named volume for data), `redis`. Each service
reads its configuration from environment variables (via `.env`, git-ignored,
with an `.env.example` documenting required keys); `backend` and `db`/`redis`
expose healthchecks that `docker compose` waits on before starting
dependents.
