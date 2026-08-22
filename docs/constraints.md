# Constraints

Rules the implementation must follow. Grouped by category; every phase of
the development plan should only pull the subset relevant to what it
touches.

## ML & Data

1. Raw datasets are never committed to git; the dataset location is
   configured via env var/config path, not hardcoded in a script.
2. Train/validation/test splits are created once, deterministically (fixed
   seed), and persisted as a manifest file — the same image never appears
   in more than one split.
3. Data augmentation is applied only to the training split; validation and
   test data receive identical normalization to training but no
   augmentation.
4. Random seeds for shuffling, splitting, and model initialization are
   fixed and documented for reproducibility.
5. Class labels are defined once, in a single config/manifest, and
   referenced everywhere (training, export, backend, frontend) — never
   redefined ad hoc in more than one place.
6. Each training run's configuration (hyperparameters, dataset/split
   version, seed) is recorded alongside its checkpoint, not just the
   final metric.

## Model Export & Evaluation

7. Exported model artifacts are versioned (directory or filename includes
   a version/hash) and never silently overwritten — a new export is a new
   version.
8. A model is promoted for serving (referenced by the backend's
   `MODEL_VERSION`) only after it clears the project's accuracy threshold
   on the held-out test split; a failing export is never wired in.
9. Evaluation metrics are computed only on the held-out test split, never
   on data used in training or validation.
10. The exact preprocessing/normalization used at training time is reused
    byte-for-byte at inference time — defined once in export metadata,
    referenced by both the evaluation script and the backend.

## Backend / API

11. Routers contain no business or inference logic — request
    parsing/response shaping only; inference and persistence logic live in
    `services/`.
12. All DB access goes through the ORM/parameterized queries — no raw SQL
    string interpolation.
13. All schema changes go through Alembic migrations — no manual DB
    edits.
14. All request bodies/uploads are validated via Pydantic schemas and
    explicit file checks before being processed.
15. Every prediction response includes the `model_version` used, so a
    served prediction can always be traced back to the exact model
    artifact that produced it.
16. List/history endpoints are paginated.
17. The inference service loads the model once at process startup, not
    per request, and must be safe under concurrent requests.

## Security

18. Secrets (DB URL, Redis URL, any API keys) are read from environment
    variables only — never hard-coded or committed. `.env` is git-ignored;
    an `.env.example` documents required variables without real values.
19. Uploaded images are validated for file type and size before
    processing; oversized or non-image files are rejected with a clear
    error and never reach the model.
20. There is no user authentication or accounts in v1 — the prediction and
    history endpoints are intentionally public. This is a deliberate,
    documented v1 limitation, to be revisited before the app handles
    sensitive data or multi-tenant use — not an oversight to silently work
    around in any single phase.
21. The prediction endpoint is rate-limited (per client IP) to prevent
    abuse of the inference path.
22. Logs never contain raw image bytes/base64 payloads or secrets — only
    metadata (size, hash, predicted label, latency).

## Frontend

23. The frontend never hardcodes the backend API URL — it is configured
    via an environment variable, distinct per environment.
24. Client-side file-type/size validation is a UX convenience only; the
    server always re-validates independently and is the source of truth.
25. Shared UI components (upload widget, result card, chart) are
    generic/prop-driven — the class list and any per-class data come from
    the API/config, never hardcoded into a component.

## Testing

26. Every phase that introduces business/inference logic has unit test
    coverage before it is considered done: data split integrity, export/
    evaluation thresholds, the inference service, and rate limiting all
    require explicit tests.

## Observability & Ops

27. All backend services use structured (JSON) logging with request IDs.
28. The health-check endpoint reports both API liveness and whether the
    model is loaded, not just process uptime.
29. A full, explicit review against every rule in this document is a
    required step before the project is considered hardened/done — it is
    not assumed to follow automatically from earlier phases passing their
    own QA.
