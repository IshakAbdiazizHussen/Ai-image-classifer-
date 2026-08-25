// Landing-page "example predictions" strip, placed under Hero. Matches the
// supplied reference exactly, including its own "placeholder" caption —
// these are mockup numbers/captions from the reference, not real inference
// output. Swap in real predictions (and drop the caption below) when real
// example images are wired in.
const EXAMPLES = [
  {
    label: "ship",
    confidence: "98.1%",
    tier: "high",
    caption: "Confident. Runner-up was airplane at 1.2%.",
  },
  {
    label: "cat",
    confidence: "54.3%",
    tier: "mid",
    caption: "Not sure — dog was close behind at 41.8%.",
  },
  {
    label: "frog",
    confidence: "31.0%",
    tier: "low",
    caption: "A guess. This image is outside the ten categories.",
  },
] as const;

export function ExampleCards() {
  return (
    <section className="examples-section">
      <div className="examples-inner">
        <div className="examples-grid">
          {EXAMPLES.map((example) => (
            <div className="example-card" key={example.label}>
              <div className="example-card-image" aria-hidden="true" />
              <div className="example-card-row">
                <span className="example-card-label">{example.label}</span>
                <span className={`example-card-confidence tier-${example.tier}`}>
                  {example.confidence}
                </span>
              </div>
              <p className="example-card-caption">{example.caption}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
