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

Services: `frontend` (Next.js, port 3001), `backend` (FastAPI, port 8000,
depends on `db` and `redis`, mounts the `ml/artifacts/` model registry
read-only), `db` (Postgres, named volume for data), `redis`. Each service
reads its configuration from environment variables (via `.env`, git-ignored,
with an `.env.example` documenting required keys); `backend` and `db`/`redis`
expose healthchecks that `docker compose` waits on before starting
dependents.

The frontend runs on **3001, not Next.js's default 3000** — on this
machine, 3000 is where the compose stack's own frontend container itself
binds (a `docker compose up` frontend occupies host port 3000 as
configured before this doc was updated), so a local `npm run dev` run
outside the stack would silently fall back to whatever port Next.js
picked next rather than fail loudly. 3001 is now the single explicit,
documented port for both the containerized frontend (`docker-compose.yml`)
and local dev (`next dev -p 3001` / `next start -p 3001` in
`frontend/package.json`) — deliberate and pinned, not a fallback.
`CORS_ORIGINS` (`.env`/`.env.example`) and the frontend healthcheck are
both kept in sync with this port.

## Local Development: Two Postgres Instances

Development on this project has actually run **two independent Postgres
containers**, not one — worth being explicit about, since they hold
different data and nothing about their names makes that obvious:

- **`imgclf-postgres` (host port 5433)** — a throwaway container created
  during Phase 3 as local dev/test infrastructure, used when running the
  backend as a local process (`.venv`, `uvicorn` directly) and by
  `pytest` (`backend/tests/`) via the root `.env`'s `DATABASE_URL`. This
  is what the automated test suite talks to.
- **The `db` service in `docker-compose.yml`** (container name
  `imageclassifier-db-1` when running, no host-published port) — the
  real database backing the actual running application at
  `localhost:8000` / `localhost:3001` when the stack is brought up via
  `docker compose up`.

**These are not synchronized and will diverge** — a prediction made
through the containerized app (`localhost:3001`) does not appear in
`imgclf-postgres`, and a `pytest` run does not affect the compose stack's
data. Confirmed by direct query during a database audit: at one point
these held 22 and 26 rows respectively, despite both being labeled
`image-classifier` internally.

**The `db` service (`imageclassifier-db-1`) is authoritative** — it's
what a real user or reviewer interacting with the running app actually
sees. `imgclf-postgres` exists only to let the backend and its test
suite run as local processes without needing the full container stack up
— genuinely convenient for fast local iteration during backend
development (`pytest`, or `uvicorn --reload` for quick manual checks),
and still fine to keep for that purpose. If local-process development on
the backend is no longer part of your workflow, it's safe to remove:

```bash
docker stop imgclf-postgres imgclf-redis
docker rm imgclf-postgres imgclf-redis
```

Removing it does not affect the `docker compose` stack or its data in
any way — the two have never shared anything beyond a coincidentally
identical database name.

## Backup and Data Durability

**No automated backup strategy exists for the `db_data` volume.** This is
a dev-scale reference project (see project-definition.md's Scope) — no
SLA, no retention policy, no tested disaster-recovery process. Prediction
history is a log of past demo predictions, not data anyone depends on
being durable; losing it means re-uploading a few images, not a real
incident. `docker compose down -v` (see `docker-compose.yml`'s comment
on `db_data`) will destroy it permanently, with no way to recover it
after the fact.

If you want to manually snapshot data before a risky operation (e.g.
before running `down -v`, or before a schema experiment), a plain
`pg_dump`/`pg_restore` is all this needs — there's nothing project-
specific about it:

```bash
# Snapshot, while the stack is running:
docker compose exec db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > backup.sql

# Restore into a (fresh or existing) database:
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backup.sql
```

`$POSTGRES_USER`/`$POSTGRES_DB` are the same values already in your
`.env` (see `.env.example`).
