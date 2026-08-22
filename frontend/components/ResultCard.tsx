import type { PredictResponse } from "@/lib/api/client";

/** Renders predicted label + confidence entirely from the API response —
 * no hardcoded class name anywhere (constraints.md rule 25). */
export function ResultCard({ result }: { result: PredictResponse }) {
  return (
    <div className="result-card">
      <h2>{result.predicted_label}</h2>
      <p>Confidence: {(result.confidence * 100).toFixed(1)}%</p>
      <p className="meta">
        Model {result.model_version} ·{" "}
        {result.cached ? "served from cache" : `${result.inference_latency_ms.toFixed(0)} ms`}
      </p>
    </div>
  );
}
