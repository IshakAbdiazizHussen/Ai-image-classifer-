"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import type { PredictResponse } from "@/lib/api/client";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
// Mirrors the backend's default MAX_UPLOAD_BYTES. This is a UX
// convenience only — the server always re-validates independently and is
// the source of truth (constraints.md rule 24).
const MAX_SIZE_BYTES = 5 * 1024 * 1024;

interface UploadFormProps {
  onSubmit: (file: File) => Promise<PredictResponse>;
  onPredicted: (result: PredictResponse) => void;
}

export function UploadForm({ onSubmit, onPredicted }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setServerError(null);
    setClientError(null);
    setFile(null);

    if (!selected) return;

    if (!ALLOWED_TYPES.includes(selected.type)) {
      setClientError(
        `Unsupported file type "${selected.type || "unknown"}". Choose a JPEG, PNG, or WebP image.`
      );
      return;
    }
    if (selected.size > MAX_SIZE_BYTES) {
      setClientError(
        `File is too large (${(selected.size / 1024 / 1024).toFixed(1)} MB). ` +
          `Max ${MAX_SIZE_BYTES / 1024 / 1024} MB.`
      );
      return;
    }
    setFile(selected);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;

    setSubmitting(true);
    setServerError(null);
    try {
      const result = await onSubmit(file);
      onPredicted(result);
    } catch (error) {
      // Always surface the server's actual validation error — never
      // swallow it (Phase 4 QA requirement).
      setServerError(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  const displayedError = clientError ?? serverError;

  return (
    <form onSubmit={handleSubmit} className="upload-form">
      <label className="upload-field">
        <span>Choose an image</span>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          aria-label="Choose an image"
          onChange={handleFileChange}
        />
      </label>

      {displayedError && (
        <p role="alert" className="form-error">
          {displayedError}
        </p>
      )}

      <button type="submit" disabled={!file || submitting}>
        {submitting ? "Classifying…" : "Classify image"}
      </button>
    </form>
  );
}
