# Project Definition — Image Classifier

## Overview

A full-stack reference application that trains a custom image
classification model and serves it through a real web app: a reproducible
ML training pipeline produces a versioned model, a FastAPI backend serves
predictions from that model, and a Next.js frontend lets a user upload an
image and see the result — the whole stack runnable with one command via
Docker Compose.

## Problem Statement

Building a classifier notebook is easy; wiring it into something that
actually runs as a deployable service is where most reference projects
stop short. This project needs to go all the way: raw dataset → trained
model → exported/evaluated artifact → backend inference API → frontend UI
→ containerized full stack → hardened for basic production concerns (rate
limiting, structured logging, consistent error handling).

## Users

There is a single user type in v1: a **visitor** who uploads an image and
receives a predicted class with a confidence score, and can browse a
shared history of recent predictions. There are no accounts, roles, or
per-user data in v1 — see [constraints.md](constraints.md) for the explicit
no-auth-in-v1 decision.

## Scope

- A single, fixed label set defined once by the training dataset/config —
  not user-configurable at runtime.
- A single model version served at a time; new training runs produce new
  versioned artifacts, and the backend serves whichever version is
  promoted.
- Image classification only — no object detection, segmentation, or
  multi-model ensembles in v1.

## Core Workflow

1. **Train** — prepare the dataset (train/val/test split), train a model
   against a documented config (hyperparameters, seed), and produce
   checkpoints.
2. **Export & evaluate** — export the trained model to a serving format,
   evaluate it against the held-out test split, and only promote it for
   serving if it clears the accuracy threshold.
3. **Serve** — the backend loads the promoted model once at startup and
   exposes a prediction endpoint plus a paginated history of past
   predictions, backed by a database and a Redis cache.
4. **Use** — the frontend lets a visitor upload an image, view the
   predicted class/confidence (and per-class probabilities), and browse
   prediction history.
5. **Ship** — the full stack (frontend, backend, database, cache) runs
   together via Docker Compose.
6. **Harden** — rate limiting, structured logging, consistent error
   handling, and a full constraints review are applied before the project
   is considered done.

## Non-Goals (Out of Scope for v1)

- User accounts, authentication, or per-user history.
- Online/continual learning or retraining triggered from the app.
- Serving multiple models simultaneously or letting a user pick a model.
- A mobile app or an admin panel.

## Success Criteria

- The exported model meets the accuracy threshold defined in
  [constraints.md](constraints.md), measured only on the held-out test
  split.
- A visitor can upload an image through the UI and see a prediction
  end-to-end.
- `docker compose up` brings up the entire stack (frontend, backend, db,
  cache) with no manual steps beyond providing env values.
- The prediction endpoint is rate-limited, all backend services log in a
  structured format, and every rule in constraints.md has been explicitly
  reviewed against the running system before the project is called done.
