// "Honest stats" section, placed under HowItWorks — fills in the
// #honest-stats anchor that LandingNav and the Hero's "See how it
// performs" link have pointed at since they were built.
//
// Numbers corrected against the actual promoted model
// (ml/artifacts/20260824T143019Z/evaluation_report.json, MODEL_VERSION in
// .env), not copied verbatim from the reference:
//   - "nine times in ten" (90%) -> real test_accuracy is 0.7817 (~78%).
//     Rounded to "eight times in ten", which is what 78% actually is.
//   - "10,000 images" -> num_test_samples is 600, not 10,000.
//   - "Here is the tenth" was a pun on the 90% framing; doesn't hold once
//     the number is corrected, so it's rephrased rather than left
//     inconsistent with the corrected headline.
// The qualitative claim checked out and is kept as-is: per-class F1 shows
// automobile (0.90) and truck (0.92) well ahead of cat (0.65, the lowest
// of all ten classes) and deer (0.71) — vehicles genuinely score higher
// than animals here, and cat genuinely is the hardest class.
export function HonestStats() {
  return (
    <section id="honest-stats" className="honest-stats-section">
      <div className="honest-stats-inner">
        <p className="section-eyebrow">Honest stats</p>
        <h2 className="honest-stats-title">
          It is right about eight times in ten.
          <br />
          Here&apos;s one of the misses.
        </h2>
        <p className="honest-stats-subtitle">
          Measured on 600 images the model never saw during training.
          Vehicles are easy — they have hard edges and consistent shapes.
          Animals are harder, and cats are the hardest of all.
        </p>
      </div>
    </section>
  );
}
