import type { PredictResponse } from "@/lib/api/client";

interface ProbabilityChartProps {
  probabilities: PredictResponse["probabilities"];
}

/** Renders one row per class, entirely derived from props — the class
 * list comes from the API response, never from a hardcoded list
 * (constraints.md rule 25).
 *
 * Reuses the landing page's AccuracyByCategory panel/bar classes
 * (accuracy-panel/accuracy-bars/accuracy-bar-*) instead of its own
 * separate style, so a real prediction's probability breakdown looks
 * like the same design language as the "Accuracy by category" panel,
 * not the old flat-blue-bar look. The predicted (top) class gets the
 * mint "tier-high" treatment; the rest get a neutral tier — unlike
 * AccuracyByCategory's mint/amber/red tiers (which grade class quality,
 * good vs. bad), a low probability on 9 of 10 classes here is the
 * *expected*, correct outcome of a confident prediction, not something
 * gone wrong — so it isn't colored red. */
export function ProbabilityChart({ probabilities }: ProbabilityChartProps) {
  const sorted = Object.entries(probabilities).sort(([, a], [, b]) => b - a);

  return (
    <div className="accuracy-panel">
      <div className="accuracy-panel-header">
        <span>Class probabilities</span>
        <span>highest → lowest</span>
      </div>

      <ul className="accuracy-bars" aria-label="Class probabilities">
        {sorted.map(([label, probability], index) => (
          <li key={label} className="accuracy-bar-row">
            <span className="accuracy-bar-label">{label}</span>
            <span className="accuracy-bar-track">
              <span
                className={`accuracy-bar-fill ${index === 0 ? "tier-high" : "tier-neutral"}`}
                style={{ width: `${(probability * 100).toFixed(1)}%` }}
              />
            </span>
            <span className="accuracy-bar-value">{(probability * 100).toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
