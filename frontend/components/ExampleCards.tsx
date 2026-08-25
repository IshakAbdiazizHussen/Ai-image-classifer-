import Image from "next/image";

// Landing-page "example predictions" strip, placed under Hero. Copy/numbers
// still match the reference's own mockup values (not real inference
// output — see the earlier note this section shipped with). Images are
// real photos now (public/Ship.jpeg, Cat.jpeg, Frog.jpeg), replacing the
// diagonal-stripe placeholder swatch.
const EXAMPLES = [
  {
    label: "ship",
    image: "/Ship.jpeg",
    confidence: "98.1%",
    tier: "high",
    caption: "Confident. Runner-up was airplane at 1.2%.",
  },
  {
    label: "cat",
    image: "/Cat.jpeg",
    // Cat.jpeg is a tall portrait crop (480x720) — object-fit:cover's
    // default center position cropped the face out entirely, leaving
    // just the body. Tried a few values against the live render; "top"
    // is the one that keeps ears/eyes/whiskers fully in frame.
    imagePosition: "top",
    confidence: "54.3%",
    tier: "mid",
    caption: "Not sure — dog was close behind at 41.8%.",
  },
  {
    label: "frog",
    image: "/Frog.jpeg",
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
              <div className="example-card-image">
                <Image
                  src={example.image}
                  alt={`Example ${example.label} photo`}
                  fill
                  sizes="(max-width: 800px) 100vw, 33vw"
                  style={{
                    objectFit: "cover",
                    objectPosition: "imagePosition" in example ? example.imagePosition : "center",
                  }}
                />
              </div>
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
