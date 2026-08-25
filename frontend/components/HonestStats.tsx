import { AccuracyByCategory } from "@/components/AccuracyByCategory";

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
//   - "cats are the hardest of all" is DROPPED (was here in an earlier
//     pass, justified via per-class F1 where cat is lowest). Now that
//     AccuracyByCategory shows the real per-class *accuracy* breakdown,
//     deer is actually the weakest class by that metric (60%, vs cat's
//     73%) — keeping the cat claim here would visibly contradict the
//     chart right next to it. "Vehicles are easier than animals on
//     average" still checks out (83.8% vs 74.4% mean recall) and is kept.
//
// "in ten" below uses a non-breaking space — the title's clamp() is
// tuned so the whole first sentence fits on one line from 320px up, but
// this guarantees "in ten" specifically can never get split across a
// wrap on its own, regardless of device/font differences the tuning
// didn't cover.
export function HonestStats() {
  return (
    <section id="honest-stats" className="honest-stats-section">
      <div className="honest-stats-inner">
        <div className="honest-stats-grid">
          <div className="honest-stats-left">
            <p className="section-eyebrow">Honest stats</p>
            <h2 className="honest-stats-title">
              It is right about eight times in ten. Here&apos;s one of the
              misses.
            </h2>
            <p className="honest-stats-subtitle">
              Measured on 600 images the model never saw during training.
              Vehicles are easier than animals on average — they have hard
              edges and consistent shapes.
            </p>

            <div className="stats-cards">
              <div className="stat-card">
                <div className="stat-value stat-value-accent">78.2%</div>
                <div className="stat-label">overall accuracy</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">0.782</div>
                <div className="stat-label">macro F1</div>
              </div>
            </div>

            <div className="warning-callout">
              <h3 className="warning-callout-title">Where it will let you down</h3>
              <p className="warning-callout-body">
                Show it something outside the ten categories — a pizza, a
                screenshot, your face — and it will still answer with one of
                the ten. Low confidence is the signal that it does not
                really know.
              </p>
            </div>
          </div>

          <AccuracyByCategory />
        </div>
      </div>
    </section>
  );
}
