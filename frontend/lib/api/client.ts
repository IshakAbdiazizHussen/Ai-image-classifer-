/**
 * Typed client for the backend API. The base URL is read from an
 * environment variable (constraints.md rule 23) — never hardcoded here or
 * in any component. Types below mirror backend/schemas/{predict,history}.py
 * exactly (Phase 3).
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_BASE_URL && typeof window !== "undefined") {
  // Fail loudly in the browser console rather than silently calling a
  // broken "undefined/predict" URL.
  console.error(
    "NEXT_PUBLIC_API_URL is not set — API calls will fail. Set it in .env.local."
  );
}

export interface PredictResponse {
  predicted_label: string;
  confidence: number;
  probabilities: Record<string, number>;
  model_version: string;
  inference_latency_ms: number;
  cached: boolean;
}

export interface PredictionHistoryItem {
  id: string;
  image_hash: string;
  predicted_label: string;
  confidence: number;
  model_version: string;
  created_at: string;
}

export interface PaginatedHistoryResponse {
  items: PredictionHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    // Backend's standardized error shape (Phase 6): {"error": {"code",
    // "message"}}. `detail` is kept as a fallback for resilience, though
    // every backend error now goes through the standardized shape.
    const body = (await response.json()) as {
      error?: { message?: unknown };
      detail?: unknown;
    };
    if (typeof body.error?.message === "string") return body.error.message;
    if (typeof body.detail === "string") return body.detail;
    return JSON.stringify(body);
  } catch {
    return response.statusText || `Request failed with status ${response.status}`;
  }
}

export async function predictImage(file: File): Promise<PredictResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/predict`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }
  return (await response.json()) as PredictResponse;
}

export async function getHistory(
  page: number = 1,
  pageSize: number = 20
): Promise<PaginatedHistoryResponse> {
  const url = new URL(`${API_BASE_URL}/history`);
  url.searchParams.set("page", String(page));
  url.searchParams.set("page_size", String(pageSize));

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }
  return (await response.json()) as PaginatedHistoryResponse;
}
