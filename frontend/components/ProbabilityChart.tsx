import type { PredictResponse } from "@/lib/api/client";

interface ProbabilityChartProps {
  probabilities: PredictResponse["probabilities"];
}

/** Renders one row per class, entirely derived from props — the class
 * list comes from the API response, never from a hardcoded list
 * (constraints.md rule 25). */
export function ProbabilityChart({ probabilities }: ProbabilityChartProps) {
  const sorted = Object.entries(probabilities).sort(([, a], [, b]) => b - a);

  return (
    <ul className="probability-chart" aria-label="Class probabilities">
      {sorted.map(([label, probability]) => (
        <li key={label} className="probability-row">
          <span className="probability-label">{label}</span>
          <div className="probability-bar-track">
            <div
              className="probability-bar-fill"
              style={{ width: `${(probability * 100).toFixed(1)}%` }}
            />
          </div>
          <span className="probability-value">{(probability * 100).toFixed(1)}%</span>
        </li>
      ))}
    </ul>
  );
}
