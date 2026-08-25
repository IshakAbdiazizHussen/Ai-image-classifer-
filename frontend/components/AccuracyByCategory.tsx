// Per-class accuracy panel, sitting to the right of HonestStats' text
// column. All numbers are recall_per_class from the real evaluation
// report (ml/artifacts/20260824T143019Z/evaluation_report.json), computed
// programmatically and rounded to whole percent — not copied from the
// reference, whose numbers/ranking don't match this model:
//   - Reference had cat lowest (84%); the real weakest class by accuracy
//     is deer (60%), not cat. Cat is actually mid-pack (73%) by this
//     metric — it only reads as "hardest" under F1 (which factors in
//     precision too, where cat really is worst). Since this chart is
//     specifically labeled "accuracy", it uses accuracy's real ranking.
//   - Reference's closing note claimed cat/dog confusion was the biggest
//     single mix-up at 38% of mistakes. Checked directly against the
//     confusion matrix: the real biggest pair is airplane<->ship (16
//     combined misclassifications, 12.2% of all 131 mistakes) — cat/dog
//     is real but smaller (13 combined, ~10%).
// See HonestStats.tsx for the corresponding text-column correction (that
// component's "cats are the hardest of all" line was dropped so it
// doesn't contradict this chart).
const ACCURACY_BY_CATEGORY = [
  { label: "automobile", pct: 90, tier: "high" },
  { label: "truck", pct: 90, tier: "high" },
  { label: "airplane", pct: 88, tier: "high" },
  { label: "frog", pct: 87, tier: "high" },
  { label: "horse", pct: 78, tier: "mid" },
  { label: "dog", pct: 77, tier: "mid" },
  { label: "cat", pct: 73, tier: "mid" },
  { label: "bird", pct: 72, tier: "mid" },
  { label: "ship", pct: 67, tier: "low" },
  { label: "deer", pct: 60, tier: "low" },
] as const;

export function AccuracyByCategory() {
  return (
    <div className="accuracy-panel">
      <div className="accuracy-panel-header">
        <span>Accuracy by category</span>
        <span>strongest → weakest</span>
      </div>

      <ul className="accuracy-bars">
        {ACCURACY_BY_CATEGORY.map((row) => (
          <li className="accuracy-bar-row" key={row.label}>
            <span className="accuracy-bar-label">{row.label}</span>
            <span className="accuracy-bar-track">
              <span
                className={`accuracy-bar-fill tier-${row.tier}`}
                style={{ width: `${row.pct}%` }}
              />
            </span>
            <span className="accuracy-bar-value">{row.pct}%</span>
          </li>
        ))}
      </ul>

      <p className="accuracy-panel-note">
        Airplanes and ships get mixed up with each other more than any
        other pair — together they are 12% of all mistakes.
      </p>
    </div>
  );
}
