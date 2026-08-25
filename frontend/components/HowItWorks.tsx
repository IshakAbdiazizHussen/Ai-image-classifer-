// "How it works" section band, placed under ExampleCards — fills in the
// LandingNav / Hero anchor that's pointed at #how-it-works since the start.
//
// Step 2's copy is corrected from the reference: it said images are
// resized to "32×32" — checked against ml/configs/train_config.yaml
// (image_size: 224, "matches the pretrained backbone") and
// ml/preprocessing.py, and that's just wrong for this project. 224×224 is
// what actually happens; CIFAR-10's own images are natively 32×32, which
// is probably where the reference mixed it up. Every other step checked
// out (image bytes really aren't persisted — PredictionRecord only stores
// a sha256 hash; there really are 10 classes with softmax probabilities
// summing to 100%).
const STEPS = [
  {
    title: "You upload",
    description:
      "Pick any photo from your phone or laptop. It goes straight to the model and is never saved.",
  },
  {
    title: "It gets shrunk",
    description:
      "Your image is resized to 224×224 — the same size the model learned from.",
  },
  {
    title: "The model scores it",
    description:
      "It hands out a score to each of the ten categories, then turns those scores into percentages that add up to 100.",
  },
  {
    title: "You see everything",
    description:
      "The winning label, its confidence, and the other nine — so a close call looks like a close call.",
  },
] as const;

export function HowItWorks() {
  return (
    <section id="how-it-works" className="section-band">
      <div className="section-band-inner">
        <h2 className="section-band-title">Four steps, start to finish</h2>
        <p className="section-band-subtitle">
          No machine learning knowledge needed to follow along.
        </p>

        <div className="steps-grid">
          {STEPS.map((step, index) => (
            <div className="step-card" key={step.title}>
              <span className="step-number">{index + 1}</span>
              <h3 className="step-title">{step.title}</h3>
              <p className="step-description">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
