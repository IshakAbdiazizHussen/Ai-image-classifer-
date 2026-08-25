"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from "react";
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

function validateFile(selected: File): string | null {
  if (!ALLOWED_TYPES.includes(selected.type)) {
    return `Unsupported file type "${selected.type || "unknown"}". Choose a JPEG, PNG, or WebP image.`;
  }
  if (selected.size > MAX_SIZE_BYTES) {
    return (
      `File is too large (${(selected.size / 1024 / 1024).toFixed(1)} MB). ` +
      `Max ${MAX_SIZE_BYTES / 1024 / 1024} MB.`
    );
  }
  return null;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

export function UploadForm({ onSubmit, onPredicted }: UploadFormProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Thumbnail preview: derived from `file` during render (not via
  // setState-in-an-effect, which reliably triggers an extra render for
  // no benefit here) — the effect below only handles the actual side
  // effect, revoking the previous object URL once it's no longer used.
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function applySelectedFile(selected: File) {
    setServerError(null);
    setClientError(null);
    const error = validateFile(selected);
    if (error) {
      setClientError(error);
      setFile(null);
      return;
    }
    setFile(selected);
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    if (selected) applySelectedFile(selected);
  }

  function handleDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragOver(false);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    // Drag-and-drop bypasses the <input accept> filter entirely, so
    // applySelectedFile's client-side validation is the only thing
    // standing between a dropped .txt file and the request going out —
    // it isn't just for the input's onChange path.
    event.preventDefault();
    setIsDragOver(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) applySelectedFile(dropped);
  }

  function handleRemove() {
    setFile(null);
    setClientError(null);
    setServerError(null);
    // Reset so re-selecting the same file/path still fires onChange.
    if (inputRef.current) inputRef.current.value = "";
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
      {!file ? (
        <label
          className={`dropzone${isDragOver ? " dropzone-active" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <svg
            className="dropzone-icon"
            viewBox="0 0 24 24"
            width="36"
            height="36"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M7 18a4.5 4.5 0 0 1-1-8.9 5.5 5.5 0 0 1 10.8-2A4.5 4.5 0 0 1 17.5 18H7Z" />
            <path d="M12 12v6M9.5 14.5 12 12l2.5 2.5" />
          </svg>
          <p className="dropzone-primary">Drag and drop an image here</p>
          <p className="dropzone-secondary">or click to browse — JPEG, PNG, or WebP</p>
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            aria-label="Choose an image"
            className="upload-input-hidden"
            onChange={handleFileChange}
          />
        </label>
      ) : (
        <div className="upload-preview">
          <button
            type="button"
            className="upload-preview-remove"
            aria-label="Remove selected image"
            onClick={handleRemove}
          >
            ×
          </button>
          {/* A local blob: object URL — next/image can't optimize this. */}
          {previewUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={previewUrl} alt="" className="upload-preview-thumb" />
          )}
          <div className="upload-preview-meta">
            <span className="upload-preview-name">{file.name}</span>
            <span className="upload-preview-size">{formatFileSize(file.size)}</span>
          </div>
        </div>
      )}

      {displayedError && (
        <p role="alert" className="form-error">
          {displayedError}
        </p>
      )}

      <button type="submit" className="upload-submit" disabled={!file || submitting}>
        {submitting ? "Classifying…" : "Classify image"}
      </button>
    </form>
  );
}
