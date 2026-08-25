// "How it works" section band, placed under ExampleCards — fills in the
// LandingNav / Hero anchor that's pointed at #how-it-works since the start.
// Reference only shows the section header (title + subtitle) on an
// elevated background band, not the four steps themselves, so that's all
// that's built here — the actual step content is a follow-up.
export function HowItWorks() {
  return (
    <section id="how-it-works" className="section-band">
      <div className="section-band-inner">
        <h2 className="section-band-title">Four steps, start to finish</h2>
        <p className="section-band-subtitle">
          No machine learning knowledge needed to follow along.
        </p>
      </div>
    </section>
  );
}
