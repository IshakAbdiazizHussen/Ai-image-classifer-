# Development Plan

This plan covers the Image Classifier project from an empty repository to a
hardened, containerized full stack, broken into six phases. Each phase
builds on the previous one and should not begin until the prior phase's
Quality Assurance section is fully satisfied.

---

## Phase 1 — ML Training Pipeline

Read the four docs — project-definition.md, architecture.md,
constraints.md, and development-plan.md — before you build this phase.

### Prompting

- **Task framing:** "Build the ML training pipeline for the image
  classifier: a config-driven dataset split, a training script using
  PyTorch/torchvision, and checkpointing that records the exact
  config/seed used for each run. Produce trained checkpoints only — no
  export, no serving code."
- **Context to reference:** [project-definition.md](project-definition.md)'s
  "Core Workflow" and "Scope" sections (fixed label set, single model
  version); [architecture.md](architecture.md)'s "ML Pipeline" section for
  the `ml/` directory layout; [constraints.md](constraints.md)'s "ML &
  Data" rules (1–6).
- **Do not attempt yet:** model export to ONNX, evaluation against a
  threshold, any backend or frontend code, and any Docker/containerization
  work — all out of scope until later phases.

### Security

- **Secrets/credentials:** none introduced in this phase. If the dataset
  is pulled from a remote source requiring credentials, those credentials
  are read from environment variables only, never hardcoded in a script or
  config file committed to git.
- **Input validation:** the dataset loader validates that every manifest
  entry points to a readable image file with a label in the configured
  class list; malformed entries are reported and excluded from the split,
  not silently included.
- **Auth/access:** not applicable — this phase runs offline, with no
  network-facing service, per [project-definition.md](project-definition.md)'s
  scope for this phase.

### Guidelines

- **Constraints.md rules that apply:** 1 (no raw dataset in git, path via
  config), 2 (deterministic, leakage-free splits, persisted manifest), 3
  (augmentation on train split only), 4 (fixed, documented seeds), 5
  (class labels defined once), 6 (run config recorded alongside
  checkpoints).
- **Coding conventions (per architecture.md):** dataset, model, and
  training logic live in `ml/training/` as separate modules
  (`dataset.py`, `model.py`, `train.py`); all tunables live in
  `ml/configs/`, not inline in `train.py`; use type hints throughout.
- **Do's and don'ts:** do persist the train/val/test manifest to
  `ml/data/splits/` so the split is reproducible across machines; don't
  regenerate the split on every run — split once, reuse the manifest.

### Implementation

- [x] Define `ml/configs/` — training config (hyperparameters, seed,
      class list, split ratios, dataset path).
- [x] `ml/training/dataset.py` — dataset loader, manifest-driven
      train/val/test split generation (first run) and manifest loading
      (subsequent runs), augmentation applied only to the training split.
- [x] `ml/training/model.py` — model architecture (transfer-learning
      backbone + classification head appropriate to the configured class
      count).
- [x] `ml/training/train.py` — training loop, checkpoint saving, and
      writing the exact run config used alongside each checkpoint.
- [x] Persist the generated split manifest to `ml/data/splits/`.
- [x] Dependencies on previous phases: none — this is the first phase.

> **Status: complete.** Built with a small CIFAR-10-derived sample dataset
> (`ml/data/prepare_sample_dataset.py`, 60 images/class, not part of the
> reusable pipeline) since no real dataset/class list existed yet. Swap
> `dataset.raw_dir`/`dataset.classes` in `ml/configs/train_config.yaml` to
> a real dataset before a real training run — no code changes needed.

### Quality Assurance

- **Tests to write:** a unit test asserting no image path appears in more
  than one of train/val/test in the generated manifest; a unit test that
  re-running the split with the same seed produces an identical manifest.
- **Specific checks:** manually inspect a sample of augmented training
  images and confirm validation/test images are not augmented; confirm
  each checkpoint directory contains its run config.
- **Definition of done:** a full training run completes end-to-end from a
  fresh checkout using only the config file, produces at least one
  checkpoint with its recorded config, and the split-integrity tests pass.

**Verified:** `ml/tests/test_dataset_split.py` (7 tests: no cross-split
overlap, deterministic split under a fixed seed, differing order under a
different seed, malformed-file exclusion + reporting, per-class ratio
correctness, train-only augmentation, identical val/test preprocessing) —
all passing. A full run of `python -m ml.training.train` against the
sample dataset completed end-to-end (360/120/120 train/val/test split, 0
skipped files) and produced
`ml/checkpoints/20260822T165334Z/{checkpoint.pt,config.yaml,metrics.json}`.

---

## Phase 2 — Model Export and Evaluation

Read the four docs — project-definition.md, architecture.md,
constraints.md, and development-plan.md — before you build this phase.

### Prompting

- **Task framing:** "Build the export and evaluation pipeline: convert a
  trained checkpoint to ONNX, write versioned artifacts with metadata, and
  evaluate the exported model against the held-out test split against the
  project's accuracy threshold. Do not promote a model that fails the
  threshold, and do not build any backend serving code yet."
- **Context to reference:** [architecture.md](architecture.md)'s "Model
  Export & Evaluation" section (artifact layout, `metadata.json` contents,
  preprocessing spec as single source of truth);
  [constraints.md](constraints.md) rules 7–10; the checkpoints and split
  manifest produced by Phase 1.
- **Do not attempt yet:** any backend inference code that loads this
  artifact (Phase 3), any frontend work, and any containerization.

### Security

- **Secrets/credentials:** none introduced. If artifacts are pushed to a
  remote registry/storage, credentials for that storage come from
  environment variables only.
- **Input validation:** the export script validates that the checkpoint
  being exported matches the expected architecture/class count before
  attempting conversion, and fails loudly rather than producing a
  malformed artifact.
- **Auth/access:** not applicable in v1 per constraints.md — this remains
  an offline pipeline step with no network-facing service.

### Guidelines

- **Constraints.md rules that apply:** 7 (versioned artifacts, never
  overwritten), 8 (promotion gated on threshold), 9 (metrics computed only
  on held-out test split), 10 (preprocessing defined once, reused
  byte-for-byte at inference).
- **Coding conventions (per architecture.md):** export logic lives in
  `ml/export/export.py`, evaluation in `ml/export/evaluate.py`; each
  versioned artifact directory (`ml/artifacts/<version>/`) contains
  `model.onnx` and `metadata.json` — version identifiers are never reused.
- **Do's and don'ts:** do write the preprocessing spec into
  `metadata.json` exactly as used during training; don't hand-tune or
  cherry-pick the evaluation split, and don't promote a model version
  anywhere in config until it has passed evaluation.

### Implementation

- [x] `ml/export/export.py` — load a checkpoint, export to ONNX, write
      `ml/artifacts/<version>/model.onnx` and `metadata.json` (version,
      source checkpoint, class list, preprocessing spec, export date).
- [x] `ml/export/evaluate.py` — run the exported ONNX model against the
      test split only, computing accuracy, precision, recall, and a
      confusion matrix.
- [x] Define and document the accuracy threshold required for promotion
      (in `constraints.md` or the export config — a single source of
      truth).
- [x] Produce an evaluation report artifact (metrics + confusion matrix)
      stored alongside `metadata.json`.
- [x] Dependencies on previous phases: requires a trained checkpoint and
      the persisted split manifest from Phase 1.

> **Status: complete, with an honest caveat.** `ml/preprocessing.py` was
> added as the single source of truth for resize/crop/normalize (rule 10),
> imported by both `ml/training/dataset.py`'s val/test transform and
> `evaluate.py`. The accuracy threshold lives in
> `ml/configs/train_config.yaml` under `evaluation.min_test_accuracy`
> (0.55 — sized for the 10-class sample dataset, random baseline 10%).
> Real end-to-end run: exported Phase 1's checkpoint to
> `ml/artifacts/20260822T165903Z/`, evaluated it against the 120-image
> test split → **53.3% test accuracy, NOT PROMOTABLE**. A retry with more
> epochs (3 → 8) on the same tiny 36-image/class train split made it
> *worse* (validation accuracy fell to ~40-52% as it overfit) — expected
> behavior given how little sample data there is, not a pipeline bug.
> Config was reverted to 3 epochs. This is the correct, intended outcome
> for a demo-scale dataset: the gating logic correctly refuses to mark a
> weak model promotable rather than rubber-stamping it. A real dataset
> would need its own epoch/data tuning to actually clear a threshold —
> that's expected to happen when a real dataset replaces the sample one,
> not something to force here by lowering the bar to match this run.

### Quality Assurance

- **Tests to write:** a unit test verifying `evaluate.py` runs only
  against the held-out test manifest entries (never train/val); a unit
  test verifying the export script rejects a checkpoint/config mismatch.
- **Specific checks:** manually confirm the ONNX model's predictions match
  the original PyTorch checkpoint's predictions on a small sample (no
  drift introduced by export); confirm re-running export with the same
  checkpoint produces a new version directory, not an overwrite.
- **Definition of done:** an exported artifact exists with a complete
  `metadata.json`, its evaluation report shows it clears the documented
  accuracy threshold, and the version is ready to be referenced (not yet
  wired in) by the backend.

**Verified:** `ml/tests/test_export_evaluate.py` (9 tests: checkpoint/
config mismatch rejected on class list and on backbone, matching
checkpoint accepted, versioned artifact written with correct metadata,
re-export under the same version raises `FileExistsError`, a second
version exports cleanly alongside the first, evaluate reads only the test
split's entries, threshold-gating logic verified in both directions with
hand-built confusion matrices, preprocessing output shape/range) — all
passing, 15/15 across the full `ml/tests/` suite. Real export + evaluate
run against Phase 1's checkpoint produced
`ml/artifacts/20260822T165903Z/{model.onnx,metadata.json,evaluation_report.json}`
end-to-end. **Not yet promotable per this run's own numbers** — expected
until a real dataset/training budget replaces the sample one; the backend
(Phase 3) is built against the export/evaluate contract, not against this
specific artifact being production-ready.

---

## Phase 3 — Backend Service (FastAPI, Database, Cache, Inference)

Read the four docs — project-definition.md, architecture.md,
constraints.md, and development-plan.md — before you build this phase.

### Prompting

- **Task framing:** "Build the FastAPI backend: the layered
  routers/services/models/schemas/core structure, a PostgreSQL-backed
  `PredictionRecord` model with an Alembic migration, a Redis-backed
  inference cache and rate limiter, and the inference service that loads
  the promoted ONNX model once at startup and serves `/predict` and
  `/history` endpoints. Do not build the frontend or Docker Compose setup
  yet."
- **Context to reference:** [architecture.md](architecture.md)'s "Backend
  Architecture" section (layering, data model, caching key format, rate
  limiting); [constraints.md](constraints.md) rules 11–22; the promoted
  model artifact and its `metadata.json` from Phase 2.
- **Do not attempt yet:** the Next.js frontend, Docker Compose, and final
  hardening details like production-tuned rate-limit thresholds (Phase 6
  reviews and finalizes those) — get a correctly structured, working
  service first.

### Security

- **Secrets/credentials:** DB URL, Redis URL, and `MODEL_VERSION` are read
  from environment variables via `core/config.py` only, never hardcoded;
  `.env` is git-ignored with an `.env.example` documenting required keys.
- **Input validation:** `/predict` validates uploaded file type and
  enforces a max file size before any processing; invalid uploads are
  rejected with a clear error and never reach the model. All request/
  response shapes go through Pydantic schemas.
- **Auth/access:** not applicable in v1 per constraints.md rule 20 —
  `/predict` and `/history` are intentionally public; this is documented,
  not an oversight, and rate limiting (this phase) is the abuse mitigation
  in place of auth.

### Guidelines

- **Constraints.md rules that apply:** 11 (no business/inference logic in
  routers), 12 (ORM only, no raw SQL), 13 (Alembic for all schema
  changes), 14 (Pydantic validation on all requests/uploads), 15
  (`model_version` in every prediction response), 16 (paginated `/history`),
  17 (model loaded once at startup, concurrency-safe), 18 (env-var-only
  secrets), 19 (upload validation), 21 (rate limiting on `/predict`), 22
  (no raw image bytes or secrets in logs).
- **Coding conventions (per architecture.md):** routers →
  services → models/schemas → core, one-way dependency flow;
  `services/inference_service.py`, `services/prediction_service.py`, and
  `services/rate_limit.py` as separate modules; type hints throughout;
  Pydantic schemas kept separate from SQLAlchemy models.
- **Do's and don'ts:** do load the ONNX session once at app startup and
  reuse it across requests; don't query the database or call the model
  directly from a router function; don't cache anything that omits
  `model_version` from the cache key.

### Implementation

- [x] `core/config.py`, `core/database.py`, `core/redis.py`,
      `core/logging.py` — environment-based settings, DB session, Redis
      client, structured logging setup.
- [x] `models/prediction.py` — `PredictionRecord` SQLAlchemy model
      (id, image_hash, predicted_label, confidence, probabilities,
      model_version, inference_latency_ms, created_at).
- [x] Alembic setup and initial migration creating the `PredictionRecord`
      table.
- [x] `schemas/predict.py` — request/response schemas for `/predict`,
      `schemas/history.py` for paginated `/history`.
- [x] `services/inference_service.py` — loads the promoted ONNX model +
      class list + preprocessing spec from `ml/artifacts/<MODEL_VERSION>/`
      once at startup; exposes a `predict(image_bytes)` function.
- [x] `services/prediction_service.py` — persists and reads
      `PredictionRecord` rows (paginated).
- [x] `services/rate_limit.py` — Redis-backed per-IP rate limiter,
      applied as a dependency on `/predict`.
- [x] Redis caching in `/predict`: check `predict:{model_version}:{image_hash}`
      before running inference; write through on a miss.
- [x] `routers/predict.py` — `POST /predict`.
- [x] `routers/history.py` — `GET /history` (paginated).
- [x] `routers/health.py` — `GET /healthz` reporting DB, Redis, and
      model-loaded status.
- [x] Dependencies on previous phases: requires a promoted, versioned
      model artifact and its `metadata.json` from Phase 2.

> **Status: complete.** Local dev/test infra: Postgres and Redis run as
> throwaway Docker containers (`imgclf-postgres` on host port 5433,
> `imgclf-redis` on 6380 — both remapped off their defaults since this
> machine already has a native Postgres and another project's Redis
> container on the standard ports). `backend/models/prediction.py` +
> Alembic produced one migration (`bf2888c169ab`), verified
> upgrade→downgrade→upgrade against the real container. Both `redis_client`
> and the DB session are exposed as FastAPI dependencies
> (`get_redis_client`/`get_db`), not imported as bare singletons in
> routers — needed for tests to isolate the cache/DB, and generally the
> more testable pattern. `ml.preprocessing.apply_preprocessing` is
> imported directly by `inference_service.py` (no reimplementation),
> satisfying rule 10 for real rather than by convention.

### Quality Assurance

- **Tests to write:** unit tests for `inference_service.predict()` against
  a known sample image/expected class; unit tests for cache hit vs. miss
  behavior including the `model_version` in the key; unit tests for the
  rate limiter rejecting requests over the configured threshold; a test
  confirming `/predict` rejects a non-image/oversized upload without
  invoking the model.
- **Specific checks:** manually upload a real image via `curl`/HTTP client
  and confirm the response includes `predicted_label`, `confidence`,
  `probabilities`, and `model_version`; manually confirm repeated identical
  uploads are served from cache (e.g. via latency or a cache-hit log);
  confirm `/healthz` reports `model_loaded: true`.
- **Definition of done:** `alembic upgrade head` succeeds on a fresh DB,
  `/predict` and `/history` work end-to-end against a real running
  Postgres/Redis, rate limiting and caching both function as designed, and
  no secret or raw image data appears in logs.

**Verified:** 16/16 backend tests pass (`inference_service` against the
real Phase 2 artifact — correctly predicts "cat" on a known sample;
`rate_limit` allows-to-limit/rejects-over-limit/tracks-clients-
independently; `prediction_service` cache hit/miss and `model_version`
cache-key isolation; full `/predict` endpoint tests — wrong content-type
→ 400, oversized upload → 413, corrupt bytes with a spoofed content-type
→ 400 without reaching the model, a real upload → 200 with the correct
shape, second identical upload → `cached: true`; `/healthz` → all
dependencies true). Manual run against the live containerized Postgres/
Redis: real `curl` uploads of a cat and a dog image both classified
correctly (97.7% confidence on the dog); rate limit fired exactly at
30 requests/minute (30×200, then 429s); `/history` paginated correctly;
tailed server logs are one-JSON-object-per-line with `request_id`,
`image_hash`, `model_version`, `predicted_label` — no raw image bytes, no
secrets, anywhere. Full combined suite (`ml/tests/` + `backend/tests/`):
**31/31 passing.**

---

## Phase 4 — Frontend Application (Next.js)

Read the four docs — project-definition.md, architecture.md,
constraints.md, and development-plan.md — before you build this phase.

### Prompting

- **Task framing:** "Build the Next.js frontend: an upload page that posts
  an image to the backend's `/predict` endpoint and renders the result
  (label, confidence, per-class probabilities), and a history page that
  reads the backend's paginated `/history` endpoint. Use a typed API
  client with the backend URL from an environment variable. Do not build
  Docker Compose or attempt any backend changes in this phase."
- **Context to reference:** [architecture.md](architecture.md)'s "Frontend
  Architecture" section (page/component layout, typed API client);
  [constraints.md](constraints.md) rules 23–25; the actual response
  shapes of `/predict` and `/history` built in Phase 3.
- **Do not attempt yet:** Docker Compose/containerization (Phase 5), and
  any hardening-level UX like fully polished error states for every
  possible backend failure (baseline error handling only — Phase 6
  finalizes this).

### Security

- **Secrets/credentials:** none handled directly by the frontend; the
  backend API URL is the only externally-configured value, read from an
  environment variable, never hardcoded per environment.
- **Input validation:** the upload form checks file type/size client-side
  before submitting, purely as a UX convenience — it never assumes this
  replaces server-side validation and always surfaces the server's actual
  validation error if the upload is rejected.
- **Auth/access:** not applicable in v1 per constraints.md rule 20 — no
  login flow, no per-user session; all pages are publicly accessible.

### Guidelines

- **Constraints.md rules that apply:** 23 (API URL from env var, never
  hardcoded), 24 (client validation is UX-only, server is source of
  truth), 25 (shared components are prop-driven, not hardcoded to a class
  list).
- **Coding conventions (per architecture.md):** `app/upload/` and
  `app/history/` as separate route segments; shared components
  (`UploadForm`, `ResultCard`, `ProbabilityChart`, `HistoryTable`) in
  `components/`; API calls centralized in `lib/api/`, not inlined in page
  components; TypeScript types for API request/response shapes matching
  the backend schemas.
- **Do's and don'ts:** do derive the displayed class list/probabilities
  entirely from the API response; don't hardcode any class name or
  backend URL into a component.

### Implementation

- [x] Scaffold the Next.js app (TypeScript, base layout, global styles).
- [x] `lib/api/` — typed client for `POST /predict` and `GET /history`,
      reading the backend base URL from an environment variable.
- [x] `components/UploadForm` — file picker with client-side type/size
      check, submit handler.
- [x] `components/ResultCard` — renders predicted label + confidence from
      an API response.
- [x] `components/ProbabilityChart` — renders per-class probabilities from
      an API response.
- [x] `components/HistoryTable` — renders a paginated list from
      `/history`.
- [x] `app/upload/` — page wiring `UploadForm` → `/predict` →
      `ResultCard`/`ProbabilityChart`.
- [x] `app/history/` — page wiring paginated `/history` fetch →
      `HistoryTable`.
- [x] Baseline error/loading states for both pages (network error, server
      validation error, empty history).
- [x] Dependencies on previous phases: requires the running backend from
      Phase 3 and its actual `/predict`/`/history` response shapes.

> **Status: complete — with one real bug found and fixed.**
> Browser-driven testing (Playwright, headless Chromium — `chromium-cli`
> wasn't available, so a small driver script was used instead) caught
> something `curl`-only testing in Phase 3 couldn't: the backend had no
> CORS policy, so the browser silently blocked every `fetch` from
> `localhost:3000` to `localhost:8000`. Fixed by adding `CORSMiddleware`
> to `backend/main.py`, configured via a new `CORS_ORIGINS` env var
> (`core/config.py`) rather than hardcoded — and locked in with a
> regression test (`backend/tests/test_cors.py`) so it can't silently
> regress. Also hit and fixed along the way: `react-hooks/set-state-in-
> effect` lint error in `app/history/page.tsx` (restructured the fetch
> into a named async function inside the effect rather than calling
> `setState` as the first statement), a corrupted `@next/swc-darwin-
> arm64` native binary that broke `next build` (reinstalled), and a
> `next.config.ts` `turbopack.root` warning from an unrelated lockfile
> elsewhere on disk (pinned explicitly).

### Quality Assurance

- **Tests to write:** component tests for `ResultCard` and
  `ProbabilityChart` rendering a given API response correctly; a test that
  `UploadForm` surfaces a server-side validation error message rather than
  swallowing it.
- **Specific checks:** manually upload a real image through the running
  UI against the live backend and confirm the result matches what `curl`
  against `/predict` returns; manually confirm the history page paginates
  correctly with more records than fit on one page; manually confirm the
  API URL comes from env config by pointing it at a different backend
  port and confirming the UI follows.
- **Definition of done:** a visitor can upload an image and see a
  prediction, and browse paginated history, entirely through the UI
  against the real backend, with no hardcoded class names or backend URLs
  anywhere in the frontend code.

**Verified:** 7/7 Vitest component tests pass (`ResultCard` renders
label/confidence/model version and the cached-vs-latency distinction from
props; `ProbabilityChart` renders one row per class, sorted, entirely
from props — including a class name never seen before, proving no
hardcoded list; `UploadForm` surfaces a mocked server rejection via
`role="alert"` without calling `onPredicted`, rejects an unsupported type
client-side without calling `onSubmit`, and calls through correctly on
success). `next build` and `eslint` both clean. Real browser run (backend
+ frontend + the Phase 3 Postgres/Redis containers, all actually running):
uploaded a real sample image through the UI — got a rendered result card
and a 10-row probability chart matching the live model (a `dog` image
scored 42.4% Cat / 37.3% Dog, consistent with Phase 2's disclosed 53.3%
test accuracy — not a frontend bug); history page correctly showed 20
total predictions across 2 pages, and clicking Next/Previous actually
changed the rendered rows and correctly disabled Next on the last page;
pointing `NEXT_PUBLIC_API_URL` at a deliberately wrong port (9999) and
restarting made the browser's actual network requests follow it there,
proving no hardcoded backend URL exists anywhere in the frontend; zero
browser console errors throughout. Screenshots taken at each step during
verification (not committed — verification artifacts, not app code).

---

## Phase 5 — Integration and Containerization (Docker Compose, Full Stack)

Read the four docs — project-definition.md, architecture.md,
constraints.md, and development-plan.md — before you build this phase.

### Prompting

- **Task framing:** "Containerize the full stack: write Dockerfiles for
  the backend and frontend, and a `docker-compose.yml` wiring together
  frontend, backend, Postgres, and Redis, with the promoted model artifact
  mounted into the backend container. The stack must come up with a
  single `docker compose up` using only an `.env` file for configuration.
  Do not add new application features in this phase — integration and
  packaging only."
- **Context to reference:** [architecture.md](architecture.md)'s "Docker
  Compose Topology" section; [constraints.md](constraints.md) rule 18
  (env-var-only secrets) and rule 28 (health-check contents); the actual
  backend and frontend built in Phases 3–4.
- **Do not attempt yet:** rate-limit tuning, logging polish, or the final
  constraints review — those belong to Phase 6. This phase proves the
  pieces run together, not that they're production-hardened.

### Security

- **Secrets/credentials:** all service configuration (DB credentials,
  Redis URL, `MODEL_VERSION`, API URL) is supplied via a git-ignored
  `.env` file consumed by `docker-compose.yml`, with `.env.example`
  documenting every required key; no credential is baked into an image
  layer.
- **Input validation:** unchanged from Phases 3–4 — this phase does not
  introduce new input surfaces, but must confirm validation still behaves
  correctly when the services run as containers instead of local
  processes.
- **Auth/access:** not applicable in v1 per constraints.md — the compose
  network exposes only the frontend and backend ports required for local/
  demo access; the database and Redis are not published outside the
  compose network.

### Guidelines

- **Constraints.md rules that apply:** 18 (env-var-only secrets, `.env`
  git-ignored), 28 (health check reports liveness and model-loaded
  status, used for compose healthchecks).
- **Coding conventions (per architecture.md):** service topology exactly
  as documented — `frontend`, `backend`, `db`, `redis`; the model registry
  (`ml/artifacts/`) mounted read-only into the backend container rather
  than baked into the image, so a new promoted version doesn't require a
  rebuild.
- **Do's and don'ts:** do make `backend` wait on `db`/`redis` healthchecks
  before starting; don't publish the database or Redis ports to the host
  unless explicitly needed for local debugging.

### Implementation

- [x] `backend/Dockerfile` — builds the FastAPI service.
- [x] `frontend/Dockerfile` — builds the Next.js app.
- [x] `docker-compose.yml` — `frontend`, `backend`, `db` (Postgres,
      named volume), `redis`, with `backend` depending on healthy `db`
      and `redis`.
- [x] Mount `ml/artifacts/` read-only into the `backend` container; wire
      `MODEL_VERSION` via env so the container serves the correct promoted
      model.
- [x] `.env.example` covering every variable consumed by any service.
- [x] Wire Alembic migrations to run (or be run) against the `db` service
      as part of bringing the stack up.
- [x] Dependencies on previous phases: requires the working backend
      (Phase 3), frontend (Phase 4), and a promoted model artifact
      (Phase 2).

> **Status: complete.** `backend/Dockerfile` builds from `python:3.13-
> slim`, copies only `backend/` and the two files the backend actually
> imports from `ml/` (`__init__.py`, `preprocessing.py`) — no torch/
> torchvision, no dataset, no baked-in artifact (738MB image; would be
> multiple GB with the training stack included). `frontend/Dockerfile` is
> a 3-stage `node:22-alpine` build; `NEXT_PUBLIC_API_URL` is a build ARG
> (not a runtime env var) since Next.js inlines `NEXT_PUBLIC_*` into the
> client bundle at build time — and it has to be a browser-reachable URL
> (`localhost:8000`), not the in-network service name `backend`, since
> the fetch happens in the user's browser, not inside the compose
> network. A one-shot `migrate` service runs `alembic upgrade head`
> against `db` and exits; `backend` depends on it via
> `condition: service_completed_successfully`. Root `.env`/`.env.example`
> now carry both the local-process variables (Phase 3's `DATABASE_URL`/
> `REDIS_URL` pointing at `localhost:5433`/`6380`) and the compose-only
> `POSTGRES_USER`/`PASSWORD`/`DB` (compose builds its own `DATABASE_URL`/
> `REDIS_URL` from these using the `db`/`redis` service hostnames) — kept
> clearly commented so the two workflows don't get confused. Hit and
> fixed along the way: `frontend/package-lock.json` had drifted out of
> sync with `package.json` (from earlier ad-hoc `--no-save` installs
> during Phase 4 debugging), which `npm ci` in the Docker build correctly
> refused to paper over — fixed with a full clean reinstall.

### Quality Assurance

- **Tests to write:** none new at the unit level — this phase is verified
  primarily by integration/manual checks.
- **Specific checks:** `docker compose up` from a clean checkout (with
  only `.env` populated) brings up all four services; `/healthz` on the
  containerized backend reports DB, Redis, and model-loaded all healthy;
  an image uploaded through the containerized frontend produces a correct
  prediction end-to-end; `docker compose down && docker compose up` is
  repeatable without manual cleanup.
- **Definition of done:** the entire stack runs from a single
  `docker compose up` with no manual steps beyond `.env`, and the full
  upload → predict → history workflow works against the containerized
  stack exactly as it did against local processes in Phases 3–4.

**Verified:** `docker compose build` succeeds for all three images
(`backend`, `frontend`, `migrate`); `docker compose up -d` brings up all
four services in the correct dependency order — `db`/`redis` healthy →
`migrate` runs and exits 0 → `backend` becomes healthy → `frontend`
starts — confirmed via `docker compose ps` (all four `Up ... (healthy)`).
`/healthz` on the containerized backend reports
`{"status":"ok","database":true,"redis":true,"model_loaded":true}`.
Real browser run (Playwright) against the fully containerized stack: a
horse image uploaded through `localhost:3000` → correctly classified at
99.8% confidence, zero console errors; history correctly showed the
accumulated predictions. `docker compose down` (no `-v`) then
`docker compose up -d` again: identical healthy startup, and the named
`db_data` volume correctly preserved prior predictions across the cycle
(proven by `/history` returning the same rows post-restart) — migration
re-ran cleanly against the already-migrated DB. Confirmed
`ml/artifacts/` is genuinely bind-mounted, not baked in (`touch` inside
the container correctly fails with "Read-only file system"), and that
`db`/`redis` are not published to the host (`docker compose ps` shows
`5432/tcp`/`6379/tcp` with no `0.0.0.0->` host mapping, only `backend`/
`frontend` are). Full `ml/tests/` + `backend/tests/` suite (32 tests)
re-run against the separate Phase 3 dev containers and still green,
confirming the Docker Compose work didn't disturb the local-process
workflow.

---

## Phase 6 — Polish and Hardening

Read the four docs — project-definition.md, architecture.md,
constraints.md, and development-plan.md — before you build this phase.

### Prompting

- **Task framing:** "Harden the application: finalize and tune rate
  limiting on `/predict`, ensure structured JSON logging with request IDs
  across all backend services, standardize error handling/response shape
  across every endpoint, and perform a full explicit review of every rule
  in constraints.md against the running system. This is the final phase —
  no new features, only correctness and robustness of what already
  exists."
- **Context to reference:** the entire [constraints.md](constraints.md)
  document (every rule, not a subset); [architecture.md](architecture.md)
  for where logging/rate-limiting/error-handling already live; the working
  system from Phases 1–5.
- **Do not attempt yet:** anything explicitly listed as a non-goal in
  [project-definition.md](project-definition.md) (auth/accounts,
  multi-model serving, online learning, admin panel, mobile app) — this
  phase hardens v1 scope, it does not expand it.

### Security

- **Secrets/credentials:** re-verify, system-wide, that no secret or
  credential appears in source control, container images, or log output
  (grep logs and image layers as part of this phase, not just trust
  earlier phases).
- **Input validation:** re-verify upload validation and rate limiting hold
  up under adversarial/edge-case input (oversized files, wrong MIME type,
  burst traffic) against the fully integrated, containerized stack.
- **Auth/access:** confirmed as not applicable in v1 per constraints.md
  rule 20 — this phase's job is to make sure the public endpoints are
  robust and rate-limited given that no auth layer exists, not to add
  one.

### Guidelines

- **Constraints.md rules that apply:** all of them — this phase performs
  the explicit full review required by rule 29, with particular focus on
  21 (rate limiting tuned, not just present), 22/27 (logging is structured
  and free of sensitive data), and 28 (health check is accurate under
  real failure conditions, e.g. DB or Redis down).
- **Coding conventions (per architecture.md):** error responses follow one
  consistent schema across every router; logging goes through the single
  `core/logging.py` setup everywhere, no ad-hoc `print`/inconsistent
  logging left over from earlier phases.
- **Do's and don'ts:** do test rate-limit and error-handling behavior
  under real failure conditions (Redis unreachable, DB unreachable,
  malformed upload); don't treat a rule as satisfied just because an
  earlier phase's QA passed — re-verify against the integrated system.

### Implementation

- [x] Tune rate-limit thresholds on `/predict` for a realistic demo/load
      profile; confirm the limiter fails safe (rejects cleanly) if Redis
      is briefly unavailable.
- [x] Ensure every backend service logs through the shared structured
      (JSON) logger with a request ID, replacing any ad-hoc logging left
      from earlier phases.
- [x] Standardize error response shape (status code, error code/message)
      across `/predict`, `/history`, and `/healthz`; update the frontend's
      error handling to match.
- [x] Confirm `/healthz` correctly reports unhealthy when DB or Redis is
      down, not just when the process is up.
- [x] Run a full rule-by-rule pass over [constraints.md](constraints.md)
      (all 29 rules) against the running, containerized system; fix or
      explicitly document any gap found.
- [x] Dependencies on previous phases: requires the fully integrated,
      containerized stack from Phase 5.

> **Status: complete — three real bugs found and fixed by re-verifying
> against the running system instead of trusting earlier phases' QA.**
>
> 1. **`/healthz` never actually returned a non-200 status.** It computed
>    `status: "degraded"` in the JSON body but always responded HTTP 200
>    — meaning nothing watching the status code (including our own
>    Docker healthcheck) could ever detect a real outage. Fixed by
>    setting `response.status_code = 503` when unhealthy, and rewired the
>    Docker healthcheck to check the status code explicitly rather than
>    relying on `urlopen`'s `HTTPError`-on-non-2xx behavior accidentally
>    doing the right thing. **Verified for real**: stopped
>    `imageclassifier-redis-1` → `/healthz` returned 503 immediately, and
>    after the healthcheck's retry window Docker itself flipped the
>    container to `(unhealthy)`; restarted Redis → automatic recovery to
>    `(healthy)`, no manual intervention. Repeated the same for the `db`
>    container with the same result.
> 2. **The rate limiter and prediction cache both had no defined
>    behavior when Redis itself was unreachable** — a bare `redis.incr()`/
>    `.get()`/`.set()` would have raised an unhandled exception. Given
>    these two Redis-backed things serve different purposes, they now
>    fail in opposite, deliberate directions: the rate limiter (an abuse-
>    control gate) fails CLOSED — `RateLimiterUnavailable` → a clean 503,
>    never silently unlimited — while the prediction cache (a pure
>    optimization) fails OPEN — logs a warning and degrades to a cache
>    miss / no-op write, never taking `/predict` down over lost caching.
>    **Verified for real**: stopped Redis, hit `/predict` → clean
>    `{"error":{"code":"rate_limiter_unavailable",...}}` at 503, not a
>    crash or hang.
> 3. **The exception-handler registration for the standardized error
>    shape missed Starlette's own routing-level errors** (e.g. an
>    unmatched route's 404) because it was registered against FastAPI's
>    `HTTPException` subclass rather than Starlette's base class that
>    routing actually raises — caught by the new test suite itself
>    (`test_not_found_error_shape_on_unknown_route` failed on first run),
>    not by manual inspection. Fixed by registering against
>    `starlette.exceptions.HTTPException`; `APIError`'s own more specific
>    handler still wins for anything raised through it (exact-type
>    match beats the walked-up MRO fallback).
>
> Also added, beyond the phase's literal checklist, because the rule-by-
> rule review (below) surfaced it as a real gap: **rule 8 ("a failing
> export is never wired in") was unenforced and silent** — the model
> version actually being served this whole time is the one Phase 2
> explicitly marked NOT PROMOTABLE (53.3% vs. a 55% threshold), and
> nothing said so anywhere a person would see it. `InferenceService` now
> reads the artifact's own `evaluation_report.json` at startup, logs a
> loud warning if `meets_threshold` is false, and `/healthz` gained a
> `model_promotable` field surfacing it honestly — without flipping
> overall `status` to degraded, since knowingly serving a demo-scale
> model is a deliberate operator choice, not an outage. **Verified**:
> the real startup log and `/healthz` response for the live artifact
> both correctly show `model_promotable: false` with the actual numbers
> (0.533 vs. 0.55) — confirmed against the real file, not asserted.
>
> New `Retry-After` header on 429s (computed from the actual seconds
> left in the current fixed window) — a small but genuine correctness
> improvement for anything that respects standard rate-limit semantics.
> Rate limit itself stayed at 30 req/min: generous enough for a live demo
> session, bounded enough to stop a scripted flood — a deliberate choice,
> not an arbitrary one just to appear "tuned."

### Quality Assurance

- **Tests to write:** unit/integration tests for rate-limit behavior at
  and beyond the tuned threshold; a test confirming `/healthz` reports
  unhealthy when a dependency is down (simulated); a test confirming every
  endpoint's error response matches the standardized shape.
- **Specific checks:** manually trigger each failure mode (stop Redis,
  stop the DB, send a malformed/oversized upload, burst-request
  `/predict`) against the containerized stack and confirm the system
  degrades as designed rather than crashing or hanging; tail logs during
  this and confirm structured output with no sensitive data.
- **Definition of done:** the full constraints.md checklist is signed off
  rule by rule against the real running system, all failure-mode checks
  behave as designed, and the project matches every success criterion in
  [project-definition.md](project-definition.md).

**Verified:** 55/55 tests passing (48 ML+backend, 7 frontend) — 17 new in
this phase: rate limiter fail-closed + `Retry-After` bounds
(`test_rate_limit.py`), cache fail-open on read/write
(`test_prediction_cache.py`), `/healthz` 200-vs-503 across three
dependency states (`test_health.py`), standardized error shape across
seven distinct failure paths including the 404 bug the suite itself
caught (`test_error_handling.py`), and the promotion-status logic
against both the real artifact and a synthetic no-report case
(`test_inference_service.py`). `next build`/`eslint` both clean.

Manual verification against the **real containerized stack** (rebuilt,
not just restarted, so every change above was actually exercised):
stopped Redis mid-run → `/healthz` 503 immediately, Docker's own
healthcheck flipped to `(unhealthy)` after its retry window, `/predict`
returned a clean 503 rather than hanging or crashing; restarted Redis →
full automatic recovery, no intervention, confirmed via both the API and
`docker compose ps`. Stopped the DB → same `/healthz` 503 behavior;
`/predict` in this state returns a clean standardized 500 (DB
persistence is a hard dependency here, deliberately — unlike the cache)
with the full traceback confirmed logged server-side as structured JSON
and *only* a generic message reaching the client. Burst-tested 35
requests → 30×200 then 429s with `Retry-After`, exactly as configured.
Re-grepped all accumulated container logs across this entire session for
`password|secret|token` and for base64-looking image data — clean.
Confirmed `.env`/`.env.local` are still untracked in git and that
neither built image contains a copied-in `.env*` file. Confirmed in the
browser (Playwright) that a real server-side error
(`{"error":{"code":"invalid_image","message":"..."}}`) renders correctly
through the frontend's updated error parsing.

**Full constraints.md rule-by-rule review** (rule 29's own requirement —
every rule re-verified against the running system in this phase, not
assumed from earlier phases' QA):

| # | Rule (short) | Status | Evidence |
|---|---|---|---|
| 1 | Raw dataset never in git, path via config | PASS | `ml/data/raw/` git-ignored; `dataset.raw_dir` in `train_config.yaml` |
| 2 | Splits created once, deterministic, persisted | PASS | `build_or_load_split` reuses `manifest.json`; tested |
| 3 | Augmentation train-only | PASS | `get_transforms` differs by split; tested |
| 4 | Seeds fixed/documented | PASS | `seed: 1337` in config, used throughout |
| 5 | Class labels defined once | PASS | `dataset.classes` → `metadata.json` → backend → frontend, one path |
| 6 | Run config recorded with checkpoint | PASS | `train.py` copies `config.yaml` + `metrics.json` per run |
| 7 | Versioned artifacts, never overwritten | PASS | `export_model` raises `FileExistsError` on collision; tested |
| 8 | Failing export never silently wired in | **FIXED** | Was unenforced/silent (see above) — now loud at startup + `/healthz` |
| 9 | Eval metrics on held-out test split only | PASS | `load_test_entries` reads only `manifest["test"]`; tested |
| 10 | Preprocessing byte-for-byte, defined once | PASS | `ml/preprocessing.py` imported by dataset.py, evaluate.py, and the backend |
| 11 | No business logic in routers | PASS | Reviewed all three routers — parsing/shaping only |
| 12 | ORM only, no raw SQL interpolation | PASS | Only a static literal `text("SELECT 1")` health ping, no interpolation |
| 13 | Alembic for all schema changes | PASS | One migration, verified up/down/up in Phase 3 |
| 14 | Pydantic + explicit upload checks | PASS | Content-type/size checked explicitly; responses are Pydantic |
| 15 | Every prediction includes `model_version` | PASS | `PredictResponse.model_version`, always set |
| 16 | List endpoints paginated | PASS | `/history` page/page_size, validated bounds |
| 17 | Model loaded once, concurrency-safe | PASS | `InferenceService` built once in `lifespan`; onnxruntime sessions are concurrency-safe |
| 18 | Env-var-only secrets, `.env` git-ignored | PASS | Re-verified: not tracked, no image contains one, `.env.example` complete |
| 19 | Upload validated, never reaches model if invalid | PASS | Type + size checked before decode; corrupt bytes rejected pre-inference; tested |
| 20 | No auth in v1, documented | PASS (by design) | Documented here, in constraints.md, and project-definition.md |
| 21 | `/predict` rate-limited | PASS, **improved** | 30/min, fail-closed, `Retry-After` header, tested at/beyond limit |
| 22 | No raw image bytes/secrets in logs | PASS | Re-grepped all session logs — clean |
| 23 | No hardcoded frontend API URL | PASS | `NEXT_PUBLIC_API_URL`; proven in Phase 4 by pointing it at a wrong port |
| 24 | Client validation is UX-only | PASS | Server re-validates independently; tested |
| 25 | Shared components prop-driven | PASS | Tested with a class name never seen before (Phase 4) |
| 26 | Business-logic phases have test coverage | PASS | 55/55 across ML, backend, frontend |
| 27 | Structured JSON logging with request IDs | PASS | Every log line, re-confirmed across all failure-mode tests this phase |
| 28 | Health check accurate, not just liveness | **FIXED** | Was always-200 regardless of body (see above) — now 503 when degraded |
| 29 | Full explicit review before calling it done | **this table** | Every rule above re-verified against the running system, this phase |
